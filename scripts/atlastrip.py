#!/usr/bin/env python
"""The command line front end for the AtlasTrip network.

This is an ordinary A2A client. It knows the Concierge's URL and nothing else:
it does not import a single line of agent code, and it has no idea that four
other agents are involved. That is the point of the protocol.

    atlastrip cards                     read every agent's card
    atlastrip plan "..."                plan a trip, approving interactively
    atlastrip trail [context-id]        replay what crossed the wire
    atlastrip doctor                    check the network is up
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from typing import Any

import httpx

from atlastrip_core import a2a_client, audit
from atlastrip_core.config import settings
from atlastrip_core.models import Itinerary
from atlastrip_core.registry import ALL_AGENTS, CONCIERGE, MCP_PORT


BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"


def style(text: str, code: str) -> str:
    return text if not sys.stdout.isatty() else f"{code}{text}{RESET}"


def rule(title: str = "") -> None:
    line = "─" * 78
    print(f"\n{style(line, DIM)}")
    if title:
        print(style(title, BOLD))


DEFAULT_REQUEST = (
    "Mira Halvorsen needs to be at the Kaisei Robotics quarterly business "
    "review in Tokyo from 14 October 2026 to 17 October 2026. She is running "
    "the integration test on their line while she is there."
)


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


async def cmd_cards(_: argparse.Namespace) -> int:
    """Read every agent's card. This is all A2A discovery amounts to."""
    for endpoint in ALL_AGENTS:
        try:
            card = await a2a_client.fetch_agent_card(endpoint)
        except Exception as error:
            print(f"{style(endpoint.name, BOLD)}  {style('unreachable', RED)}  {error}")
            continue

        rule(f"{card.name}   {style(endpoint.framework, DIM)}")
        print(f"  {card.description}")
        print(f"  {style('card', DIM)}       {endpoint.agent_card_url}")
        for interface in card.supported_interfaces:
            print(
                f"  {style('interface', DIM)}  {interface.protocol_binding} "
                f"v{interface.protocol_version}  {interface.url}"
            )
        print(
            f"  {style('streaming', DIM)}  {card.capabilities.streaming}"
        )
        for skill in card.skills:
            print(f"  {style('skill', DIM)}      {skill.id}: {skill.name}")
            print(f"             {skill.description}")
    print()
    return 0


async def cmd_plan(args: argparse.Namespace) -> int:
    """Plan one trip, answering the approval question if one comes back."""
    utterance = args.request or DEFAULT_REQUEST
    trip_ref = args.trip_ref or f"TRIP-{uuid.uuid4().hex[:8].upper()}"
    context_id = f"ctx-{uuid.uuid4().hex[:12]}"

    rule("Request")
    print(f"  {utterance}")
    print(f"\n  {style('trip', DIM)}    {trip_ref}")
    print(f"  {style('context', DIM)} {context_id}")

    rule("The network at work")
    reply = await a2a_client.ask(
        CONCIERGE,
        instruction=utterance,
        payload={"trip_ref": trip_ref},
        context_id=context_id,
        caller="traveller",
        trip_ref=trip_ref,
    )
    for line in reply.progress:
        print(f"  {style('·', DIM)} {line}")

    if reply.needs_input:
        rule("Approval required")
        print(f"  {reply.question}\n")
        approved = args.approve if args.approve is not None else _ask_human()

        reply = await a2a_client.ask(
            CONCIERGE,
            instruction="approve" if approved else "decline",
            payload={"approved": approved},
            context_id=context_id,
            task_id=reply.task_id,
            caller="manager",
            trip_ref=trip_ref,
        )
        rule("Resumed")
        for line in reply.progress:
            print(f"  {style('·', DIM)} {line}")

    if not reply.completed:
        rule("Outcome")
        print(f"  {style(reply.state, RED)}")
        print(f"  {reply.question}")
        return 1

    itinerary = Itinerary.model_validate(reply.data)
    _print_itinerary(itinerary)
    print(f"\n  {style('Replay it with', DIM)}  make trail CONTEXT={context_id}")
    return 0


async def cmd_trail(args: argparse.Namespace) -> int:
    """Replay what crossed the wire, in order, across all six processes."""
    entries = audit.trail(args.context_id)
    if not entries:
        print("Nothing in the trail yet. Run 'make demo' first.")
        return 1

    rule(f"A2A trail{f' for {args.context_id}' if args.context_id else ''}")
    print(
        f"  {style('time      agent       direction  event      detail', DIM)}"
    )
    for entry in entries:
        colour = {
            "escalated": YELLOW,
            "failed": RED,
            "completed": GREEN,
        }.get(entry["event"], DIM)
        print(
            f"  {entry['at'][11:19]}  {entry['agent']:<10}  "
            f"{entry['direction']:<9}  {style(f'{entry['event']:<9}', colour)}  "
            f"{(entry['summary'] or '')[:64]}"
        )
    print(f"\n  {len(entries)} exchanges.\n")
    return 0


async def cmd_doctor(_: argparse.Namespace) -> int:
    """Check every moving part before blaming the agents."""
    rule("Checks")
    ok = True

    ok &= _report("Postgres", await _check_postgres())
    ok &= _report(f"MCP server :{MCP_PORT}", await _check_mcp())
    for endpoint in ALL_AGENTS:
        ok &= _report(
            f"{endpoint.name} :{endpoint.port}", await _check_agent(endpoint.base_url)
        )

    print()
    print(f"  reasoning mode : {settings().reasoning_mode}")
    print(f"  model          : {settings().openai_model}")
    print(f"  api key        : {'set' if settings().openai_api_key else 'not set'}")
    print()
    return 0 if ok else 1


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _ask_human() -> bool:
    try:
        answer = input("  Approve this spend? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in {"y", "yes", "approve"}


def _print_itinerary(itinerary: Itinerary) -> None:
    colour = {"confirmed": GREEN, "awaiting_approval": YELLOW, "rejected": RED}[
        itinerary.status
    ]
    rule(f"{itinerary.trip_ref}  {style(itinerary.status.replace('_', ' ').upper(), colour)}")

    if itinerary.flights:
        out, back = itinerary.flights.outbound, itinerary.flights.inbound
        print(
            f"  {style('flights', DIM)}   {out.carrier} {out.flight_no} "
            f"{out.origin_iata}-{out.dest_iata} {out.depart_utc:%d %b %H:%M}Z, "
            f"{back.flight_no} back {back.depart_utc:%d %b %H:%M}Z"
        )
        print(
            f"            {out.cabin.replace('_', ' ')}, "
            f"${itinerary.flights.total_usd:,.2f}"
        )
    if itinerary.stay:
        hotel = itinerary.stay.recommended
        print(
            f"  {style('stay', DIM)}      {hotel.name} ({hotel.star_rating}*), "
            f"{hotel.distance_km_to_venue:.2f} km from the venue"
        )
        print(
            f"            {hotel.nights} nights at ${hotel.nightly_rate_usd:,.2f}, "
            f"${hotel.total_usd:,.2f}"
        )
    if itinerary.compliance:
        for finding in itinerary.compliance.findings:
            mark = {"violation": RED, "warning": YELLOW, "info": DIM}[finding.severity]
            print(
                f"  {style(f'{finding.severity:<9}', mark)} {finding.clause_id} "
                f"{finding.title}"
            )
    if itinerary.budget and itinerary.budget.authorization_code:
        print(
            f"  {style('approved', DIM)}  {itinerary.budget.authorization_code}, "
            f"${itinerary.budget.remaining_after_usd:,.2f} left in "
            f"{itinerary.budget.cost_center_id}"
        )
    print(f"  {style('total', DIM)}     ${itinerary.total_usd:,.2f}")

    rule("Itinerary")
    for line in itinerary.narrative.splitlines():
        print(f"  {line}")


def _report(name: str, result: tuple[bool, str]) -> bool:
    healthy, detail = result
    mark = style("ok  ", GREEN) if healthy else style("down", RED)
    print(f"  {mark}  {name:<22} {style(detail, DIM)}")
    return healthy


async def _check_postgres() -> tuple[bool, str]:
    try:
        from atlastrip_core import db

        row = await db.fetch_one("SELECT COUNT(*) AS n FROM flights")
        await db.close_pool()
        return True, f"{row['n']:,} flights in inventory"
    except Exception as error:
        return False, str(error)[:70]


async def _check_mcp() -> tuple[bool, str]:
    try:
        from atlastrip_core.mcp_http import MCPClient

        async with MCPClient() as mcp:
            tools = await mcp.list_tools()
        return True, f"{len(tools)} tools"
    except Exception as error:
        return False, str(error)[:70]


async def _check_agent(base_url: str) -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            response = await http.get(f"{base_url}/healthz")
        response.raise_for_status()
        return True, base_url
    except Exception as error:
        return False, str(error)[:70]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atlastrip", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("cards", help="read every agent's card").set_defaults(
        run=cmd_cards
    )

    plan = commands.add_parser("plan", help="plan a trip")
    plan.add_argument("request", nargs="?", help="the trip, in plain English")
    plan.add_argument("--trip-ref", help="use a specific trip reference")
    plan.add_argument(
        "--approve",
        dest="approve",
        action="store_const",
        const=True,
        help="approve any spend without asking",
    )
    plan.add_argument(
        "--decline",
        dest="approve",
        action="store_const",
        const=False,
        help="decline any spend without asking",
    )
    plan.set_defaults(run=cmd_plan, approve=None)

    trail = commands.add_parser("trail", help="replay the A2A exchanges")
    trail.add_argument("context_id", nargs="?", help="narrow to one conversation")
    trail.set_defaults(run=cmd_trail)

    commands.add_parser("doctor", help="check the network").set_defaults(run=cmd_doctor)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return asyncio.run(args.run(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
