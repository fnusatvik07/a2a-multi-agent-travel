# The dataset

Everything the agents reason over is in this repository. Nothing is fetched at
runtime, nothing is random at runtime, and the whole thing rebuilds in about
four seconds with `make seed`.

The split is deliberate: **hand-authored where a person should be able to read
and change it, generated where volume is needed.**

---

## What is generated, and how

`scripts/seed_data.py` reads the files in `data/seed/` and expands two of them.

**Flights.** `routes.json` describes 5 city pairs, each with a handful of real
services: carrier, flight number, local departure time, aircraft, and a list
fare per cabin. The seeder expands each service across its date window and
across the fare products for each cabin:

```
economy           SAVER  x1.00  non-refundable
economy           FLEX   x1.42  refundable
premium_economy   SAVER  x1.00  non-refundable
premium_economy   FLEX   x1.33  refundable
business          FLEX   x1.00  refundable
```

Mid-week departures cost 8 percent more, weekend departures 4 percent less, and
each row carries a wobble of up to 6 percent so prices are not suspiciously
uniform. Emissions are modelled from the route distance and the cabin, at 0.090,
0.144 and 0.261 kg of CO2 equivalent per passenger kilometre.

That produces **1,938 rows**.

**Hotel rates.** `hotels.json` describes 19 properties with coordinates, star
rating, amenities, a corporate code and a base rate. The seeder prices every
night from 1 September to 15 December 2026, in three room types:

```
saver      x0.86  non-refundable
standard   x1.00  refundable
executive  x1.28  refundable, breakfast
```

Business hotels discount 12 percent on Friday and Saturday nights. That
produces **6,042 rows**.

Both generators use `random.Random(20261014)`, so the same input always
produces byte-identical output and the demo is reproducible.

---

## What is hand-authored

| File | Rows | What it is |
|---|---|---|
| `airports.json` | 10 | IATA code, city, country, timezone |
| `routes.json` | 5 | City pairs and the services flying them |
| `hotels.json` | 19 | Tokyo, London, Singapore, San Francisco, New York |
| `employees.json` | 6 | Grade, passport, home airport, cost centre, manager |
| `cost_centers.json` | 4 | Quarterly budget and owner |
| `budget_ledger.json` | 11 | Opening commitments, so budgets are already partly spent |
| `ground_transport.json` | 13 | Airport transfers by mode and price |
| `venues.json` | 5 | Customer sites with coordinates |
| `policies.json` | 10 | The travel policy |
| `visa_rules.json` | 12 | Passport and destination pairs |

The timezone on each airport matters more than it looks. `search_flights` takes
a departure date and compares it in the origin airport's own timezone:

```sql
WHERE (f.depart_utc AT TIME ZONE a.timezone)::date = $3::date
```

Without that, a search for 14 October out of San Francisco returns flights that
depart on the 15th, because a 10:55 local departure is 17:55 UTC and a naive
UTC window smears across two calendar days. It is the sort of bug that produces
a plausible itinerary for the wrong day.

---

## The policy, which is two things at once

Every clause in `policies.json` carries both halves:

```json
{
  "clause_id": "TRV-003",
  "title": "Lodging nightly cap",
  "category": "lodging",
  "text": "Room rates are capped per city, excluding tax ...",
  "hard_rule": true,
  "rule": {
    "type": "lodging_cap",
    "caps": {"Tokyo": 280, "London": 260, "Singapore": 250,
             "San Francisco": 300, "New York": 320},
    "default_cap": 220,
    "overage_tolerance_pct": 20
  }
}
```

- `text` is prose. Sentinel's LlamaIndex vector index is built from it, and it
  is what gets retrieved and quoted when the agent explains a ruling.
- `rule` is a structured description of the same clause.
  `sentinel_llamaindex/rules.py` has one handler per `rule.type` and evaluates
  it in ordinary Python. This is the binding ruling.

Retrieval decides which clauses are worth explaining. The structured rule
decides which are broken. The two must agree, and keeping them in one document
is what makes that likely.

Rule types currently implemented: `cabin_entitlement`, `preferred_carrier`,
`lodging_cap`, `advance_purchase`, `spend_threshold`, `refundable_window`,
`ground_cap`, `carbon_ceiling`, `entry_documents`, `informational`.

Adding a clause means adding a document and one handler function.
`tests/agents/sentinel/test_rules.py` runs against the shipped policy file, so
a change that breaks a rule fails there rather than in front of a traveller.

---

## The numbers the demo turns on

The sample scenario is tuned so the interesting things happen. Change any of
these and the story changes with it.

| | Value | Where | Effect |
|---|---|---|---|
| Shinagawa Bay Tower base rate | $315 | `hotels.json` | Prices at $298.33 a night for the sample dates, over the cap |
| Tokyo nightly cap | $280 | `policies.json` TRV-003 | The violation that triggers the renegotiation |
| Auto-approval threshold | $3,000 | `policies.json` TRV-005 | The trip lands at $3,688.76, so a human is required |
| CC-ROBOTICS-APAC budget | $60,000 | `cost_centers.json` | |
| Opening commitments | $52,400 | `budget_ledger.json` | Leaves $7,600, enough to approve but not comfortably |
| Mira's grade | IC5 | `employees.json` | Entitled to premium economy on a flight over 8 hours |
| SFO to HND duration | 675 min | `routes.json` | Over the 480 minute long-haul threshold |

Two worked examples:

- Raise the Tokyo cap to $300 and the renegotiation never happens. The trip
  costs more, and Hearth's judgement stands.
- Drop the opening commitments to $30,000 and the trip is under the auto
  approval threshold relative to a comfortable budget, but TRV-005 is an
  absolute threshold, so it still needs a human. Lower the threshold in
  TRV-005 instead to see the approval disappear.

---

## The runtime files

`data/tinydb/` holds the seeded documents and, at runtime, the audit trail:

```
policies.json          seeded
visa_rules.json        seeded
venues.json            seeded
audit_concierge.json   written at runtime
audit_skyline.json     written at runtime
audit_hearth.json      ...
audit_sentinel.json
audit_ledger.json
```

One audit file per writing service, because TinyDB keeps its document index in
memory and hands out sequential ids; two processes writing one file collide.
`audit.trail()` merges them in timestamp order on read, which is what
`make trail` prints. The audit files are git-ignored.

`make reset` rebuilds the dataset and clears the trail.

---

## Changing it

```bash
$EDITOR data/seed/hotels.json
make seed
```

The schema is `packages/atlastrip_core/src/atlastrip_core/schema.sql`, which is
dropped and recreated on every seed. It is short enough to read in one sitting.

If you add a city, add its airport to `airports.json` with the right timezone,
add hotels with real coordinates, and add a venue if you want lodging ranked by
walking distance. If you add a passport country, add its rows to
`visa_rules.json`, or Sentinel will escalate the trip for manual confirmation
rather than guessing, which is the correct behaviour but not a useful demo.
