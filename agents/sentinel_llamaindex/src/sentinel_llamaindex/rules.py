"""The binding half of Sentinel: policy evaluated as code, not as prose.

Every clause in ``data/seed/policies.json`` carries two things. The ``text`` is
what a person reads, and it is what the retrieval index in ``agent.py`` is
built from. The ``rule`` is a small structured description of the same clause,
and it is what gets evaluated here.

The split matters. Retrieval decides which clauses are *worth explaining*; this
module decides which clauses are *broken*. A ruling that stops a booking should
not depend on a model reading a paragraph correctly.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from atlastrip_core import documents
from atlastrip_core.models import (
    ComplianceVerdict,
    PolicyFinding,
    ScreeningRequest,
    VisaRequirement,
)


def load_clauses() -> list[dict[str, Any]]:
    """Every policy clause, as stored in TinyDB."""
    return documents.all_documents(documents.POLICIES)


def evaluate(request: ScreeningRequest, destination_country: str) -> ComplianceVerdict:
    """Rule on one trip against the whole policy book.

    Args:
        request: The assembled trip, as the Concierge put it together.
        destination_country: Resolved from the destination airport by the
            caller, because the entry rules are keyed on country, not airport.
    """
    as_of = request.as_of or date.today()
    findings: list[PolicyFinding] = []

    for clause in load_clauses():
        rule = clause.get("rule") or {}
        handler = _HANDLERS.get(rule.get("type"))
        if handler is None:
            continue
        findings.extend(handler(clause, rule, request, as_of))

    visa = lookup_visa(request.traveller.passport_country, destination_country)
    findings.extend(_entry_findings(visa, request, as_of, destination_country))

    violations = [f for f in findings if f.severity == "violation"]
    return ComplianceVerdict(
        trip_ref=request.trip_ref,
        compliant=not violations,
        findings=findings,
        visa=visa,
        requires_manager_approval=any(f.requires_approval for f in findings),
        summary=summarise(findings, visa),
    )


# --------------------------------------------------------------------------
# One handler per rule type. Each returns zero or more findings.
# --------------------------------------------------------------------------


def _cabin_entitlement(
    clause: dict[str, Any], rule: dict[str, Any], request: ScreeningRequest, _: date
) -> list[PolicyFinding]:
    if request.flights is None:
        return []
    ranks: dict[str, int] = rule["cabin_rank"]
    grade = request.traveller.grade
    findings: list[PolicyFinding] = []

    for leg in (request.flights.outbound, request.flights.inbound):
        entitled = rule["default_cabin"]
        if leg.duration_minutes >= rule["long_haul_minutes"]:
            entitled = rule["long_haul_entitlement"].get(grade, entitled)

        booked_rank = ranks.get(leg.cabin, 0)
        entitled_rank = ranks.get(entitled, 0)
        if booked_rank > entitled_rank:
            findings.append(
                PolicyFinding(
                    clause_id=clause["clause_id"],
                    title=clause["title"],
                    severity="violation",
                    detail=(
                        f"{leg.flight_no} is booked in "
                        f"{leg.cabin.replace('_', ' ')}, but grade {grade} is "
                        f"entitled to {entitled.replace('_', ' ')} on a "
                        f"{leg.duration_minutes} minute flight."
                    ),
                    requires_approval=True,
                )
            )
        elif booked_rank < entitled_rank:
            findings.append(
                PolicyFinding(
                    clause_id=clause["clause_id"],
                    title=clause["title"],
                    severity="info",
                    detail=(
                        f"{leg.flight_no} is booked below entitlement: grade "
                        f"{grade} could travel {entitled.replace('_', ' ')} on "
                        f"this sector."
                    ),
                )
            )
    return findings


def _preferred_carrier(
    clause: dict[str, Any], rule: dict[str, Any], request: ScreeningRequest, _: date
) -> list[PolicyFinding]:
    if request.flights is None:
        return []
    preferred = set(rule["carriers"])
    offending = {
        leg.carrier
        for leg in (request.flights.outbound, request.flights.inbound)
        if leg.carrier not in preferred
    }
    if not offending:
        return []
    return [
        PolicyFinding(
            clause_id=clause["clause_id"],
            title=clause["title"],
            severity="warning",
            detail=(
                f"{', '.join(sorted(offending))} is outside the corporate "
                f"carrier agreements. Permitted, but a justification is "
                f"recorded for the cost centre review."
            ),
        )
    ]


def _lodging_cap(
    clause: dict[str, Any], rule: dict[str, Any], request: ScreeningRequest, _: date
) -> list[PolicyFinding]:
    if request.stay is None:
        return []
    hotel = request.stay.recommended
    cap = float(rule["caps"].get(hotel.city, rule["default_cap"]))
    if hotel.nightly_rate_usd <= cap:
        return []

    overage = hotel.nightly_rate_usd - cap
    return [
        PolicyFinding(
            clause_id=clause["clause_id"],
            title=clause["title"],
            severity="violation",
            detail=(
                f"{hotel.name} is ${hotel.nightly_rate_usd:,.2f} a night "
                f"against a {hotel.city} cap of ${cap:,.2f}, an overage of "
                f"${overage:,.2f} a night "
                f"(${overage * hotel.nights:,.2f} across {hotel.nights} nights)."
            ),
            requires_approval=True,
        )
    ]


def _advance_purchase(
    clause: dict[str, Any],
    rule: dict[str, Any],
    request: ScreeningRequest,
    as_of: date,
) -> list[PolicyFinding]:
    days = (request.request.depart_date - as_of).days
    if days >= rule["minimum_days"]:
        return []
    return [
        PolicyFinding(
            clause_id=clause["clause_id"],
            title=clause["title"],
            severity="violation",
            detail=(
                f"Departure is {days} days away, inside the "
                f"{rule['minimum_days']} day advance purchase window."
            ),
            requires_approval=True,
        )
    ]


def _spend_threshold(
    clause: dict[str, Any], rule: dict[str, Any], request: ScreeningRequest, _: date
) -> list[PolicyFinding]:
    total = _trip_total(request)
    threshold = float(rule["auto_approve_below_usd"])
    if total < threshold:
        return []
    return [
        PolicyFinding(
            clause_id=clause["clause_id"],
            title=clause["title"],
            severity="warning",
            detail=(
                f"Trip total ${total:,.2f} is at or above the ${threshold:,.2f} "
                f"auto-approval threshold, so the cost centre owner has to sign "
                f"it off before anything is ticketed."
            ),
            requires_approval=True,
        )
    ]


def _refundable_window(
    clause: dict[str, Any],
    rule: dict[str, Any],
    request: ScreeningRequest,
    as_of: date,
) -> list[PolicyFinding]:
    if request.flights is None:
        return []
    days = (request.request.depart_date - as_of).days
    if days > rule["days_before_departure"]:
        return []
    non_refundable = [
        leg.flight_no
        for leg in (request.flights.outbound, request.flights.inbound)
        if not leg.refundable
    ]
    if not non_refundable:
        return []
    return [
        PolicyFinding(
            clause_id=clause["clause_id"],
            title=clause["title"],
            severity="warning",
            detail=(
                f"{', '.join(non_refundable)} is non-refundable and departure "
                f"is {days} days away. A changeable fare is preferred this "
                f"close in."
            ),
        )
    ]


def _ground_cap(
    clause: dict[str, Any], rule: dict[str, Any], request: ScreeningRequest, _: date
) -> list[PolicyFinding]:
    cap = float(rule["cap_usd"])
    if request.ground_usd <= cap:
        return []
    return [
        PolicyFinding(
            clause_id=clause["clause_id"],
            title=clause["title"],
            severity="violation",
            detail=(
                f"Ground transport of ${request.ground_usd:,.2f} exceeds the "
                f"${cap:,.2f} cap."
            ),
            requires_approval=True,
        )
    ]


def _carbon_ceiling(
    clause: dict[str, Any], rule: dict[str, Any], request: ScreeningRequest, _: date
) -> list[PolicyFinding]:
    if request.flights is None:
        return []
    total = request.flights.outbound.co2_kg + request.flights.inbound.co2_kg
    ceiling = float(rule["round_trip_kg"])
    if total <= ceiling:
        return [
            PolicyFinding(
                clause_id=clause["clause_id"],
                title=clause["title"],
                severity="info",
                detail=(
                    f"Modelled emissions {total:,.0f} kg CO2e, within the "
                    f"{ceiling:,.0f} kg reporting ceiling."
                ),
            )
        ]
    return [
        PolicyFinding(
            clause_id=clause["clause_id"],
            title=clause["title"],
            severity="warning",
            detail=(
                f"Modelled emissions {total:,.0f} kg CO2e exceed the "
                f"{ceiling:,.0f} kg ceiling. The traveller is asked to record "
                f"why a lower emission routing was not viable."
            ),
        )
    ]


_HANDLERS = {
    "cabin_entitlement": _cabin_entitlement,
    "preferred_carrier": _preferred_carrier,
    "lodging_cap": _lodging_cap,
    "advance_purchase": _advance_purchase,
    "spend_threshold": _spend_threshold,
    "refundable_window": _refundable_window,
    "ground_cap": _ground_cap,
    "carbon_ceiling": _carbon_ceiling,
}


# --------------------------------------------------------------------------
# Entry rules
# --------------------------------------------------------------------------


def lookup_visa(passport_country: str, destination_country: str) -> VisaRequirement | None:
    matches = documents.find(
        documents.VISA_RULES,
        passport_country=passport_country,
        destination_country=destination_country,
    )
    if not matches:
        return None
    rule = matches[0]
    return VisaRequirement(
        passport_country=rule["passport_country"],
        destination_country=rule["destination_country"],
        requirement=rule["requirement"],
        processing_days=int(rule["processing_days"]),
        notes=rule.get("notes", ""),
    )


def _entry_findings(
    visa: VisaRequirement | None,
    request: ScreeningRequest,
    as_of: date,
    destination: str,
) -> list[PolicyFinding]:
    if visa is None:
        return [
            PolicyFinding(
                clause_id="TRV-010",
                title="Entry documentation",
                severity="warning",
                detail=(
                    f"No entry rule on file for a "
                    f"{request.traveller.passport_country} passport entering "
                    f"{destination}. Travel Operations must confirm manually."
                ),
                requires_approval=True,
            )
        ]

    days_available = (request.request.depart_date - as_of).days
    if visa.processing_days > days_available:
        return [
            PolicyFinding(
                clause_id="TRV-010",
                title="Entry documentation",
                severity="violation",
                detail=(
                    f"{visa.requirement.replace('_', ' ')} takes about "
                    f"{visa.processing_days} days to obtain and departure is "
                    f"{days_available} days away."
                ),
                requires_approval=True,
            )
        ]

    if visa.processing_days == 0:
        detail = f"No visa required: {visa.notes}"
    else:
        detail = (
            f"{visa.requirement.replace('_', ' ')} required, about "
            f"{visa.processing_days} days to obtain, {days_available} days "
            f"available. {visa.notes}"
        )
    return [
        PolicyFinding(
            clause_id="TRV-010",
            title="Entry documentation",
            severity="info",
            detail=detail,
        )
    ]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _trip_total(request: ScreeningRequest) -> float:
    total = request.ground_usd
    if request.flights:
        total += request.flights.total_usd
    if request.stay:
        total += request.stay.total_usd
    return round(total, 2)


def summarise(
    findings: list[PolicyFinding], visa: VisaRequirement | None
) -> str:
    """One line a human can act on."""
    violations = [f for f in findings if f.severity == "violation"]
    warnings = [f for f in findings if f.severity == "warning"]
    if violations:
        return (
            f"{len(violations)} policy violation"
            f"{'s' if len(violations) > 1 else ''}: "
            + "; ".join(f"{f.clause_id} {f.title}" for f in violations)
            + "."
        )
    if warnings:
        return (
            f"Within policy, with {len(warnings)} item"
            f"{'s' if len(warnings) > 1 else ''} to note: "
            + "; ".join(f"{f.clause_id} {f.title}" for f in warnings)
            + "."
        )
    return "Fully within policy."
