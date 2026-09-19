"""Build UI views exclusively from the uploaded instance and generated CSVs."""
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from .evaluate import load_submission
from .instance import Instance
from .objective import CONTRACT_WEIGHT, ACTIVITY_NUDGE
from .topology import activity_footprint


def schedule_insights(instance: Instance, output: Path, capacity_overrides: dict | None = None) -> dict:
    access, occupancy, results = load_submission(output)
    visits = defaultdict(list)
    groups = defaultdict(set)
    for row in access:
        visits[row.activity_id].append(row)
    for row in occupancy:
        groups[row.week, row.location_id].add(row.co_share_group)
    activities = []
    for aid, activity in sorted(instance.activities.items()):
        rows = sorted(visits[aid], key=lambda r: (r.week, r.access_night))
        project = instance.projects[activity.contract_number]
        activities.append({
            "id": aid, "contract": activity.contract_number,
            "type": activity.activity_type, "nature": project.nature_of_activity,
            "access_type": project.access_type, "priority": activity.activity_priority,
            "line": activity.start_location_id.split(":")[1],
            "bound": activity.start_location_id.split(":")[-1],
            "start_location": activity.start_location_id, "end_location": activity.end_location_id,
            "required_work": activity.total_accesses,
            "delivered_work": sum(1.5 if r.eclo else 1 for r in rows),
            "planned_start": activity.planned_start_date.isoformat(),
            "predecessor": activity.predecessor_activity_id,
            "first_week": rows[0].week, "last_week": rows[-1].week,
            "completion_date": instance.completion_date(rows[-1].week).isoformat(),
            "visits": [{"week": r.week, "night": r.access_night, "eclo": bool(r.eclo)} for r in rows],
            "locations": list(activity_footprint(instance, activity)),
        })
    contracts = []
    for row in results:
        project = instance.projects[row.contract_number]
        members = [a for a in activities if a["contract"] == row.contract_number]
        weight = CONTRACT_WEIGHT[project.contract_priority] * sum(1 + ACTIVITY_NUDGE[a["priority"]] for a in members)
        contracts.append({
            "id": row.contract_number, "priority": project.contract_priority,
            "nature": project.nature_of_activity, "workfronts": project.number_of_workfronts,
            "weekly_night_cap": project.number_of_maximum_access_per_week,
            "planned_completion": project.planned_completion_date.isoformat(),
            "completion": row.simulated_completion_date.isoformat(),
            "delay_days": row.overrun_days, "delay_cost": round(weight * row.overrun_days, 1),
            "activity_count": len(members), "access_count": sum(len(a["visits"]) for a in members),
        })
    weeks = []
    for w in range(1, instance.horizon_weeks + 1):
        rows = [r for r in access if r.week == w]
        locations = [{"id": loc, "used": len(labels), "supply": (capacity_overrides or {}).get((loc, week), instance.locations[loc].supply_capacity),
                      "excess": max(0, len(labels) - (capacity_overrides or {}).get((loc, week), instance.locations[loc].supply_capacity))}
                     for (week, loc), labels in groups.items() if week == w]
        weeks.append({
            "week": w, "start": (instance.horizon_start + timedelta(days=7 * (w - 1))).isoformat(),
            "end": instance.completion_date(w).isoformat(), "accesses": len(rows),
            "activities": len({r.activity_id for r in rows}), "eclo": sum(r.eclo for r in rows),
            "excess": sum(r["excess"] for r in locations),
            "locations": sorted(locations, key=lambda r: (-r["excess"], -r["used"] / max(1, r["supply"]), r["id"])),
        })
    return {
        "summary": {"activities": len(activities), "contracts": len(contracts),
                    "required_work": sum(a.total_accesses for a in instance.activities.values()),
                    "delivered_work": sum(a["delivered_work"] for a in activities),
                    "on_time_contracts": sum(c["delay_days"] == 0 for c in contracts),
                    "horizon_weeks": instance.horizon_weeks, "locations": len(instance.locations)},
        "activities": activities, "contracts": contracts, "weeks": weeks,
        "location_catalog": [{"id": loc, "supply": item.supply_capacity} for loc, item in sorted(instance.locations.items())],
        "lines": [{"id": line, "stations": [{"id": s.station_id, "interchange": s.is_interchange}
                  for s in sorted(instance.stations.values(), key=lambda s: s.seq) if s.line_code == line]}
                  for line in instance.lines],
    }
