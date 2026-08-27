"""The vocabulary the five agents share.

A2A carries opaque parts on the wire, so peers need an agreed shape for the
structured payloads they exchange. These models are that agreement: every
``DataPart`` sent between AtlasTrip agents validates against one of them.

Keeping the vocabulary in a tiny shared package (and nothing else) is the point
of the exercise: the agents share a data contract, never a runtime.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Payload(BaseModel):
    """Base class for everything that crosses an A2A boundary."""

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------
# The request that starts everything
# --------------------------------------------------------------------------


class TripRequest(_Payload):
    """A traveller's ask, normalised out of free text by the Concierge."""

    trip_ref: str = Field(description="Stable id for this trip, e.g. TRIP-2026-0042.")
    employee_email: str
    purpose: str
    origin_iata: str
    destination_iata: str
    depart_date: date
    return_date: date
    venue_id: str | None = Field(
        default=None, description="Customer site the traveller must be near."
    )
    notes: str = ""

    @property
    def nights(self) -> int:
        return max((self.return_date - self.depart_date).days, 1)


class TravellerProfile(_Payload):
    """Who is travelling, and the entitlements that follow from their grade."""

    employee_id: int
    full_name: str
    email: str
    title: str
    grade: str
    home_iata: str
    passport_country: str
    cost_center_id: str
    manager_email: str


# --------------------------------------------------------------------------
# The briefs the Concierge sends out
#
# Each specialist is asked for exactly one thing, described by one of these.
# They travel as the structured half of an A2A message, next to a text part
# written for the receiving agent's model.
# --------------------------------------------------------------------------


class FlightBrief(_Payload):
    trip_ref: str
    origin_iata: str
    dest_iata: str
    depart_date: date
    return_date: date
    traveller_grade: str
    cabin: str | None = Field(
        default=None, description="Force a cabin. Left unset, Skyline chooses."
    )
    preferred_carriers: list[str] = Field(default_factory=list)
    max_stops: int | None = None


class StayBrief(_Payload):
    trip_ref: str
    city: str
    check_in: date
    check_out: date
    venue_id: str | None = None
    nightly_cap_usd: float | None = Field(
        default=None,
        description=(
            "The policy cap, passed as guidance. Hearth weighs it against "
            "proximity and quality; it is Sentinel that enforces it."
        ),
    )
    enforce_cap: bool = Field(
        default=False,
        description="Set on a re-ask, when the cap has become a hard constraint.",
    )
    min_star_rating: int | None = None
    max_distance_km: float | None = None


class ScreeningRequest(_Payload):
    """Everything Sentinel needs to rule on a trip."""

    trip_ref: str
    traveller: TravellerProfile
    request: TripRequest
    flights: FlightProposal | None = None
    stay: StayProposal | None = None
    ground_usd: float = 0.0
    as_of: date | None = Field(
        default=None, description="Booking date, for the advance purchase rule."
    )


# --------------------------------------------------------------------------
# Skyline: flights
# --------------------------------------------------------------------------


class FlightOffer(_Payload):
    offer_id: str
    direction: Literal["outbound", "return"]
    carrier: str
    flight_no: str
    origin_iata: str
    dest_iata: str
    depart_utc: datetime
    arrive_utc: datetime
    duration_minutes: int
    stops: int
    cabin: str
    fare_basis: str
    total_usd: float
    refundable: bool
    co2_kg: float
    aircraft: str


class FlightProposal(_Payload):
    """What Skyline returns to the Concierge."""

    trip_ref: str
    outbound: FlightOffer
    inbound: FlightOffer
    total_usd: float
    alternatives: list[FlightOffer] = Field(default_factory=list)
    rationale: str = ""


# --------------------------------------------------------------------------
# Hearth: lodging
# --------------------------------------------------------------------------


class HotelOffer(_Payload):
    offer_id: str
    hotel_id: int
    name: str
    city: str
    address: str
    star_rating: int
    distance_km_to_venue: float
    nightly_rate_usd: float
    nights: int
    total_usd: float
    refundable: bool
    breakfast_included: bool
    corporate_code: str | None = None
    amenities: list[str] = Field(default_factory=list)


class StayProposal(_Payload):
    """What Hearth returns to the Concierge."""

    trip_ref: str
    recommended: HotelOffer
    alternatives: list[HotelOffer] = Field(default_factory=list)
    total_usd: float
    rationale: str = ""


# --------------------------------------------------------------------------
# Sentinel: policy and entry rules
# --------------------------------------------------------------------------


class PolicyFinding(_Payload):
    clause_id: str
    title: str
    severity: Literal["info", "warning", "violation"]
    detail: str
    requires_approval: bool = False


class VisaRequirement(_Payload):
    passport_country: str
    destination_country: str
    requirement: str
    processing_days: int
    notes: str = ""


class ComplianceVerdict(_Payload):
    """What Sentinel returns to the Concierge."""

    trip_ref: str
    compliant: bool
    findings: list[PolicyFinding] = Field(default_factory=list)
    visa: VisaRequirement | None = None
    requires_manager_approval: bool = False
    summary: str = ""


# --------------------------------------------------------------------------
# Ledger: budget and authorisation
# --------------------------------------------------------------------------


class SpendRequest(_Payload):
    """What the Concierge asks Ledger to authorise."""

    trip_ref: str
    cost_center_id: str
    employee_email: str
    flights_usd: float
    lodging_usd: float
    ground_usd: float = 0.0
    requires_manager_approval: bool = False
    manager_approval_token: str | None = Field(
        default=None,
        description="Set on the follow-up turn once a human has approved.",
    )

    @property
    def total_usd(self) -> float:
        return round(self.flights_usd + self.lodging_usd + self.ground_usd, 2)


class BudgetVerdict(_Payload):
    """What Ledger returns to the Concierge."""

    trip_ref: str
    cost_center_id: str
    requested_usd: float
    remaining_before_usd: float
    remaining_after_usd: float
    decision: Literal["approved", "needs_approval", "rejected"]
    reason: str
    approval_token: str | None = Field(
        default=None,
        description=(
            "Set when the decision is needs_approval: the token to send back "
            "on the same task once a human has said yes."
        ),
    )
    authorization_code: str | None = Field(
        default=None,
        description="Set only once the spend is committed.",
    )
    breakdown: dict[str, float] = Field(default_factory=dict)


# --------------------------------------------------------------------------
# Concierge: the assembled result
# --------------------------------------------------------------------------


class Itinerary(_Payload):
    """The Concierge's final artifact, assembled from the four specialists."""

    trip_ref: str
    status: Literal["confirmed", "awaiting_approval", "rejected"]
    traveller: TravellerProfile
    request: TripRequest
    flights: FlightProposal | None = None
    stay: StayProposal | None = None
    compliance: ComplianceVerdict | None = None
    budget: BudgetVerdict | None = None
    total_usd: float = 0.0
    narrative: str = ""
    generated_at: datetime | None = None
