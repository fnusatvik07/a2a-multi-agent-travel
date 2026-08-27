"""Ledger's budget logic, without the model.

Ledger is the only agent on the network that changes anything. Everyone else
reads inventory and forms opinions; Ledger writes a commitment against a cost
centre, and once it has, that money is gone. So the authority to say yes lives
here, in plain code, and the model in ``agent.py`` gets to explain the decision
rather than make it.

Three outcomes are possible:

    rejected        the cost centre cannot cover it, at any level of approval
    needs_approval  it fits, but a human has to sign it off first
    approved        committed, with an authorisation code
"""

from __future__ import annotations

import hashlib

from atlastrip_core.console import get_logger
from atlastrip_core.mcp_http import MCPClient
from atlastrip_core.models import BudgetVerdict, SpendRequest

log = get_logger("ledger")


async def budget_position(cost_center_id: str) -> dict[str, float]:
    """What the cost centre has, and what is left of it."""
    async with MCPClient() as mcp:
        position = await mcp.call_one(
            "get_cost_center_budget", cost_center_id=cost_center_id
        )
    if position is None:
        raise LookupError(f"No cost centre {cost_center_id}.")
    return position


def authorization_code(request: SpendRequest) -> str:
    """A short, stable code derived from the trip and the amount.

    Stable so that replaying the same authorisation cannot mint a new code,
    and derived rather than random so a test can assert on it.
    """
    digest = hashlib.sha256(
        f"{request.trip_ref}|{request.cost_center_id}|{request.total_usd:.2f}".encode()
    ).hexdigest()
    return f"AUTH-{digest[:10].upper()}"


async def assess(request: SpendRequest) -> BudgetVerdict:
    """Decide, and commit the money when the answer is yes.

    This is the whole job in deterministic mode, and the binding decision in
    LLM mode.
    """
    position = await budget_position(request.cost_center_id)
    remaining_before = float(position["remaining_usd"])
    total = request.total_usd
    breakdown = {
        "flights_usd": request.flights_usd,
        "lodging_usd": request.lodging_usd,
        "ground_usd": request.ground_usd,
    }

    def verdict(
        decision: str,
        reason: str,
        code: str | None = None,
        pending_token: str | None = None,
    ) -> BudgetVerdict:
        return BudgetVerdict(
            trip_ref=request.trip_ref,
            cost_center_id=request.cost_center_id,
            requested_usd=total,
            remaining_before_usd=round(remaining_before, 2),
            remaining_after_usd=round(
                remaining_before - (total if code else 0.0), 2
            ),
            decision=decision,  # type: ignore[arg-type]
            reason=reason,
            approval_token=pending_token,
            authorization_code=code,
            breakdown=breakdown,
        )

    if total > remaining_before:
        return verdict(
            "rejected",
            f"{request.cost_center_id} has ${remaining_before:,.2f} left this "
            f"quarter and the trip costs ${total:,.2f}. No level of approval "
            f"can spend money the cost centre does not have.",
        )

    expected = authorization_code(request)
    approval_given = request.manager_approval_token == expected

    if request.requires_manager_approval and not approval_given:
        return verdict(
            "needs_approval",
            f"${total:,.2f} against {request.cost_center_id} needs the cost "
            f"centre owner's sign-off before anything is ticketed. "
            f"${remaining_before:,.2f} remains this quarter.",
            pending_token=expected,
        )

    await _commit(request, total)
    log.info(
        "committed $%.2f to %s for %s", total, request.cost_center_id, request.trip_ref
    )
    return verdict(
        "approved",
        f"${total:,.2f} committed against {request.cost_center_id}, leaving "
        f"${remaining_before - total:,.2f} this quarter."
        + (" Approved by the cost centre owner." if approval_given else ""),
        expected,
    )


async def _commit(request: SpendRequest, total: float) -> None:
    async with MCPClient() as mcp:
        await mcp.call(
            "record_commitment",
            cost_center_id=request.cost_center_id,
            trip_ref=request.trip_ref,
            description=f"Travel authorisation for {request.employee_email}",
            amount_usd=total,
        )
