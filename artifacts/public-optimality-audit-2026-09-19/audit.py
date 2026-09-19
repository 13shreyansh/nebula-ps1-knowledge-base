"""Independent public-instance lower bounds and exact relaxed infeasibility checks.

Run from the repository root with .venv/bin/python <this file>.
The proof code parses raw CSVs and does not import nebula_ps1. Existing local
checkers are used only in the separately labelled feasible-witness validation.
No production files, protected schedules, or portal state are changed.
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import ortools
from ortools.sat.python import cp_model

SCRIPT_DIR = Path(__file__).resolve().parent
OUT = Path(os.environ.get("NEBULA_PS1_OPTIMALITY_AUDIT_OUT", SCRIPT_DIR))
OUT.mkdir(parents=True, exist_ok=True)
ROOT = SCRIPT_DIR.parent.parent
DATA = ROOT / "current-problem-statement/PS1/01_data"


def rows(name):
    with (DATA / name).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def write_csv(name, records):
    with (OUT / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


raw = {p.name: rows(p.name) for p in sorted(DATA.glob("*.csv"))}
lines = {r["line_code"] for r in raw["01_LINES.csv"]}
stations = {(r["line_code"], r["station_id"]): r for r in raw["02_STATIONS.csv"]}
sectors = {r["sector_id"]: r for r in raw["03_SECTORS.csv"]}
locations = {r["location_id"]: r for r in raw["04_LOCATION_SUPPLY.csv"]}
buffers = {r["nature_of_works"]: r for r in raw["05_BUFFER_LOCATION.csv"]}
parameters = {r["key"]: r["value"] for r in raw["06_PARAMETERS.csv"]}
contracts = {r["contract_number"]: r for r in raw["07_PROJECT_DETAILS.csv"]}
activities = {r["activity_id"]: r for r in raw["08_ACTIVITY_DETAILS.csv"]}
start = date.fromisoformat(parameters["horizon_start"])
horizon = int(parameters["horizon_weeks"])
members = {c: [a for a, r in activities.items() if r["contract_number"] == c] for c in contracts}
release = {a: (date.fromisoformat(r["planned_start_date"]) - start).days // 7 + 1 for a, r in activities.items()}
demand = {a: int(r["total_accesses"]) for a, r in activities.items()}
deadlines = {c: date.fromisoformat(r["planned_completion_date"]) for c, r in contracts.items()}
due_week = {c: ((d - start).days + 1) // 7 for c, d in deadlines.items()}
# Exact integer tenths: independent expression of observed contract aggregation.
contract_weight = {c: {1: 100, 2: 10, 3: 1}[int(r["contract_priority"])] for c, r in contracts.items()}
weight10 = {c: contract_weight[c] * sum({1: 13, 2: 12, 3: 10}[int(activities[a]["activity_priority"])] for a in aa) for c, aa in members.items()}


def finish_date(week):
    return start + timedelta(days=7 * week - 1)


def delay10(contract, week):
    return max(0, (finish_date(week) - deadlines[contract]).days) * weight10[contract]


def corridor(activity):
    r = activities[activity]
    s, e = r["start_location_id"].split(":"), r["end_location_id"].split(":")
    assert s[1] == e[1] and s[3] == e[3]
    ordered = sorted((x for x in sectors.values() if x["line_code"] == s[1]), key=lambda x: int(x["seq"]))
    positions = {x["sector_id"]: i for i, x in enumerate(ordered)}
    lo, hi = sorted([positions[":".join(s[:3])], positions[":".join(e[:3])]])
    return s[1], s[3], ordered, lo, hi


def work_footprint(activity):
    line, bound, ordered, lo, hi = corridor(activity)
    result = set()
    for sector in ordered[lo:hi + 1]:
        result.add(sector["sector_id"] + ":" + bound)
        result.update(f"PLAT:{line}:{sector[k]}:{bound}" for k in ("from_station_id", "to_station_id"))
    return result


def affected_lines(activity):
    line, _, ordered, lo, hi = corridor(activity)
    result = {line}
    if contracts[activities[activity]["contract_number"]]["nature_of_activity"] != "Live":
        return result
    for sector in ordered[lo:hi + 1]:
        endpoints = {sector["from_station_id"], sector["to_station_id"]}
        if not all(int(stations[(line, node)]["is_interchange"]) for node in endpoints):
            continue
        for other in sectors.values():
            if other["line_code"] != line and {other["from_station_id"], other["to_station_id"]} == endpoints:
                result.add(other["line_code"])
    return result


def blocked(activity):
    line, bound, ordered, lo, hi = corridor(activity)
    nature = contracts[activities[activity]["contract_number"]]["nature_of_activity"]
    distance = int(buffers[nature]["up_to_buffer_sectors"])
    result = work_footprint(activity)
    result |= {sector["sector_id"] + ":" + bound for i, sector in enumerate(ordered) if lo - distance <= i <= hi + distance and not lo <= i <= hi}
    if int(buffers[nature]["opposite_bound_required"]):
        opposite = "EB" if bound == "WB" else "WB"
        result |= {x.rsplit(":", 1)[0] + ":" + opposite for x in tuple(result)}
    if nature == "Live":
        for sector in ordered[lo:hi + 1]:
            endpoints = {sector["from_station_id"], sector["to_station_id"]}
            if not all(int(stations[(line, node)]["is_interchange"]) for node in endpoints):
                continue
            for other_line in lines - {line}:
                other_ordered = sorted((x for x in sectors.values() if x["line_code"] == other_line), key=lambda x: int(x["seq"]))
                for index, bridge in enumerate(other_ordered):
                    if {bridge["from_station_id"], bridge["to_station_id"]} != endpoints:
                        continue
                    for x in other_ordered[max(0, index - distance):index + distance + 1]:
                        for other_bound in ("EB", "WB"):
                            result.add(x["sector_id"] + ":" + other_bound)
                            result.update(f"PLAT:{other_line}:{x[k]}:{other_bound}" for k in ("from_station_id", "to_station_id"))
    return result


footprints = {a: work_footprint(a) for a in activities}
blocked_sets = {a: blocked(a) for a in activities}
pm_pairs = []
for a, b in itertools.combinations(activities, 2):
    if not any(contracts[activities[k]["contract_number"]]["access_type"] == "PM" for k in (a, b)):
        continue
    overlap = (footprints[a] & blocked_sets[b]) | (footprints[b] & blocked_sets[a])
    if overlap:
        pm_pairs.append((a, b, sorted(overlap)))


def integrity():
    assert len(raw) == 8
    assert len(contracts) == len(raw["07_PROJECT_DETAILS.csv"])
    assert len(activities) == len(raw["08_ACTIVITY_DETAILS.csv"])
    assert len(locations) == len(raw["04_LOCATION_SUPPLY.csv"])
    assert len(stations) == len(raw["02_STATIONS.csv"])
    assert len(sectors) == len(raw["03_SECTORS.csv"])
    for (line, _), s in stations.items():
        assert line in lines
    for s in sectors.values():
        assert (s["line_code"], s["from_station_id"]) in stations
        assert (s["line_code"], s["to_station_id"]) in stations
    for r in locations.values():
        assert int(r["supply_capacity"]) >= 0 and r["line_code"] in lines
    for c, r in contracts.items():
        assert r["nature_of_activity"] in buffers
        assert r["access_type"] in {"PM", "PC", "C"}
        assert int(r["number_of_maximum_access_per_week"]) > 0
        assert int(r["number_of_workfronts"]) > 0
        assert members[c]
    for a, r in activities.items():
        assert r["contract_number"] in contracts
        assert footprints[a] <= set(locations)
        assert 1 <= release[a] <= horizon and demand[a] > 0
        assert not r["predecessor_activity_id"] or r["predecessor_activity_id"] in activities
        seen = {a}
        parent = r["predecessor_activity_id"]
        while parent:
            assert parent not in seen
            seen.add(parent)
            parent = activities[parent]["predecessor_activity_id"]
    return {
        "files": {p.name: {"rows": len(raw[p.name]), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(DATA.glob("*.csv"))},
        "all_references_valid": True,
        "all_activity_corridors_resolve_to_supplied_locations": True,
        "predecessor_graph_acyclic": True,
        "predecessor_links": sum(bool(r["predecessor_activity_id"]) for r in activities.values()),
        "all_planned_starts_are_mondays": all(date.fromisoformat(r["planned_start_date"]).weekday() == 0 for r in activities.values()),
        "all_planned_deadlines_are_sundays": all(d.weekday() == 6 for d in deadlines.values()),
        "required_standard_work_units": sum(demand.values()),
        "mandatory_pm_conflicts": pm_pairs,
    }


def analytical_relaxation(scenario):
    """Enumerate every contract finish week, ignoring all resource/dependency coupling.

    For a proposed contract finish, each activity uses the largest available
    number of useful weeks, and only the minimum ECLO needed. C keeps the
    necessary <=2 ECLO/activity condition but drops common line windows.
    """
    curves, minima = [], {}
    for c, aa in members.items():
        choices = []
        for end in range(1, horizon + 1):
            if scenario == "B" and end > due_week[c]:
                continue
            details, possible = {}, True
            for a in aa:
                slots = max(0, min(demand[a], end - release[a] + 1))
                need_e = max(0, 2 * demand[a] - 2 * slots)
                max_e = 0 if scenario == "A" else (min(2, slots) if scenario == "C" else slots)
                if not slots or need_e > max_e:
                    possible = False
                    break
                details[a] = need_e
            if not possible:
                continue
            delay = 0 if scenario == "B" else delay10(c, end)
            cost = delay + 50 * sum(details.values())
            record = {"scenario": scenario, "contract": c, "finish_week": end, "delay_score": delay / 10, "eclo_rows": sum(details.values()), "lower_bound_cost": cost / 10}
            curves.append(record)
            choices.append((cost, end, details, delay))
        assert choices, (scenario, c)
        best = min(choices)
        minima[c] = {"bound": best[0] / 10, "earliest_best_finish_week": best[1], "eclo_by_activity": best[2], "delay": best[3] / 10}
    return {"score": round(sum(v["bound"] for v in minima.values()), 10), "contracts": minima}, curves


def exhaustive_a_pair():
    """Enumerate every within-horizon access subset, including surplus rows."""
    a, b = "A036", "A075"
    assert any({x, y} == {a, b} for x, y, _ in pm_pairs)
    ca, cb = activities[a]["contract_number"], activities[b]["contract_number"]
    candidates, all_count = [], 0
    for n in range(demand[a], horizon - release[a] + 2):
        for aw in itertools.combinations(range(release[a], horizon + 1), n):
            for m in range(demand[b], horizon - release[b] + 2):
                for bw in itertools.combinations(range(release[b], horizon + 1), m):
                    all_count += 1
                    if set(aw) & set(bw):
                        continue
                    value = delay10(ca, max(aw)) + delay10(cb, max(bw))
                    candidates.append({"a036_weeks": " ".join(map(str, aw)), "a075_weeks": " ".join(map(str, bw)), "a036_contract_cost": delay10(ca, max(aw)) / 10, "a075_contract_cost": delay10(cb, max(bw)) / 10, "total": value / 10})
    write_csv("a_pair_exhaustive.csv", candidates)
    return {"all_pairs_enumerated": all_count, "nonconflicting_pairs": len(candidates), "minimum_pair_cost": min(r["total"] for r in candidates), "minimum_if_a075_on_time": min(r["total"] for r in candidates if max(map(int, r["a075_weeks"].split())) <= due_week[cb])}


def model_check(scenario, *, pm=True, c_window=True, strict_below=None,
                label=None, eclo_budget=None, finish_by=None):
    """Independent relaxed CP-SAT model; no hints or frozen activities.

    Every real feasible schedule maps into this model. Capacity, legal packing,
    workfronts, and non-PM closure constraints are deliberately absent.
    """
    model = cp_model.CpModel()
    x, e, first, last = {}, {}, {}, {}
    for a in activities:
        xx, ee, starts, ends = [], [], [], []
        for w in range(release[a], horizon + 1):
            x[a, w] = model.new_bool_var(f"x_{a}_{w}")
            e[a, w] = model.new_bool_var(f"e_{a}_{w}")
            model.add(e[a, w] <= x[a, w])
            if scenario == "A":
                model.add(e[a, w] == 0)
            xx.append(x[a, w]); ee.append(e[a, w])
            starts.append(w * x[a, w] + (horizon + 1) * (1 - x[a, w]))
            ends.append(w * x[a, w])
        model.add(2 * sum(xx) + sum(ee) >= 2 * demand[a])
        first[a] = model.new_int_var(1, horizon, f"first_{a}")
        last[a] = model.new_int_var(1, horizon, f"last_{a}")
        model.add_min_equality(first[a], starts)
        model.add_max_equality(last[a], ends)
        if scenario == "B":
            model.add(last[a] <= due_week[activities[a]["contract_number"]])
    for a, r in activities.items():
        if r["predecessor_activity_id"]:
            model.add(first[a] > last[r["predecessor_activity_id"]])
    if pm:
        for a, b, _ in pm_pairs:
            for w in range(max(release[a], release[b]), horizon + 1):
                model.add(x[a, w] + x[b, w] <= 1)
    if scenario == "C" and c_window:
        window_start = {line: model.new_int_var(1, horizon, f"eclo_window_{line}") for line in sorted(lines)}
        for (a, w), var in e.items():
            for line in affected_lines(a):
                model.add(window_start[line] <= w).only_enforce_if(var)
                model.add(window_start[line] + 1 >= w).only_enforce_if(var)
    if eclo_budget is not None:
        model.add(sum(e.values()) <= eclo_budget)
    for a, deadline in (finish_by or {}).items():
        model.add(last[a] <= deadline)
    total = 50 * sum(e.values())
    for c, aa in members.items():
        finish = model.new_int_var(1, horizon, f"finish_{c}")
        model.add_max_equality(finish, [last[a] for a in aa])
        late = model.new_int_var(0, 7 * horizon + abs((deadlines[c] - start).days), f"delay_days_{c}")
        model.add_max_equality(late, [0, 7 * finish - 1 - (deadlines[c] - start).days])
        if scenario != "B":
            total += weight10[c] * late
    if strict_below is None:
        model.minimize(total)
    else:
        model.add(total <= strict_below - 1)
    label = label or scenario
    model.export_to_file(str(OUT / f"{label}.pbtxt"))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 20260919
    status = solver.solve(model)
    (OUT / f"{label}.response.txt").write_text(solver.response_stats() + "\n")
    result = {"status": solver.status_name(status), "wall_seconds": solver.wall_time, "branches": solver.num_branches, "conflicts": solver.num_conflicts, "no_hints": True, "no_frozen_activities": True, "pm_exclusion_included": pm, "c_line_windows_included": scenario == "C" and c_window, "eclo_budget": eclo_budget, "forced_finish_weeks": finish_by or {}}
    if strict_below is not None:
        result["tested_score_at_most"] = (strict_below - 1) / 10
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result["score"] = solver.value(total) / 10
        if strict_below is None:
            result["best_bound"] = solver.best_objective_bound / 10
        chosen = [{"activity_id": a, "week": w, "eclo": solver.value(e[a, w])} for a, w in x if solver.value(x[a, w])]
        write_csv(f"{label}.relaxed_access.csv", chosen)
    return result


def witnesses():
    """Upper-bound validation only: check the unchanged official witness bytes."""
    import zipfile
    sys.path.insert(0, str(ROOT / "src"))
    from nebula_ps1.instance import load_instance
    from nebula_ps1.evaluate import evaluate_submission, load_submission
    from nebula_ps1.independent_score import independently_score
    from nebula_ps1.closure import screen_closures
    instance = load_instance(DATA)
    result = {}
    pinned_hashes = {
        "A-002.zip": "76bf26e19161337daf4f186d2a678aeb23bcb8613bc3bba42d00451d30325437",
        "B-001.zip": "1ef95698cc456f5a037bcd3939a6ee6a6ea06bd32fc4c74c0ff403eb3d00b76c",
        "C-001.zip": "ee6b09ccf0584cf4d3dfb6b825669c39491329a9f756ca50dc1879fd5e274f43",
    }
    for scenario, name in [("A", "A-002.zip"), ("B", "B-001.zip"), ("C", "C-001.zip")]:
        directory = ROOT / "deliverables/public" / scenario
        ev = evaluate_submission(instance, directory, scenario)
        score = independently_score(DATA, directory)
        access, occupancy, _ = load_submission(directory)
        archive_hash = hashlib.sha256((ROOT / "deliverables/validator" / name).read_bytes()).hexdigest()
        assert archive_hash == pinned_hashes[name]
        with zipfile.ZipFile(ROOT / "deliverables/validator" / name) as old, zipfile.ZipFile(ROOT / "deliverables/final-submission" / (scenario + ".zip")) as final:
            exact = set(final.namelist()) == {"SCHEDULE_ACCESS.csv", "SCHEDULE_OCCUPANCY.csv", "RESULTS.csv"} and len(final.namelist()) == 3
            same = all(old.read(n) == final.read(n) == (directory / n).read_bytes() for n in final.namelist())
        # Third, raw-CSV score calculation is independent of both production scorers.
        by_activity = defaultdict(list)
        for r in access:
            by_activity[r.activity_id].append(r)
        independent_delay = sum(delay10(c, max(r.week for a in aa for r in by_activity[a])) for c, aa in members.items())
        groups = defaultdict(set)
        for r in occupancy:
            groups[r.location_id, r.week].add(r.co_share_group)
        excess = sum(max(0, len(gg) - int(locations[loc]["supply_capacity"])) for (loc, _), gg in groups.items())
        ec = sum(r.eclo for r in access)
        own = ((independent_delay if scenario != "B" else 0) + 70 * excess + 50 * ec) / 10
        strict = screen_closures(instance, access, occupancy, forbid_buffer_overlap=True)
        assert not ev.hard_violations and not strict
        assert ev.objective_score == score.objective_score == own and exact and same
        result[scenario] = {"score": own, "delay_score": independent_delay / 10, "excess": excess, "eclo_rows": ec, "official_record": name[:-4], "official_archive_sha256": archive_hash, "matches_pinned_official_archive_hash": True, "matches_archived_successful_csv_bytes": same, "exact_three_root_files": exact, "hard_violations": list(ev.hard_violations), "strict_closure_conflicts": len(strict), "three_score_calculations_agree": True, "submission_hash": ev.submission_hash}
    return result


def main():
    report = {"generated_utc": datetime.now(timezone.utc).isoformat(), "scope": "exact current public input; no portal interaction", "ortools_version": ortools.__version__, "input_audit": integrity()}
    # Lower bounds are computed before reading any schedule witness.
    report["enumerated_contract_relaxations"] = {}
    all_curves = []
    for s in "ABC":
        report["enumerated_contract_relaxations"][s], curves = analytical_relaxation(s)
        all_curves.extend(curves)
    write_csv("contract_bound_curves.csv", all_curves)
    write_csv("activity_input_audit.csv", [{"activity": a, "contract": r["contract_number"], "work_units": demand[a], "release_week": release[a], "deadline_week": due_week[r["contract_number"]], "minimum_standard_finish": release[a] + demand[a] - 1, "minimum_b_eclo": max(0, 2 * demand[a] - 2 * max(0, due_week[r["contract_number"]] - release[a] + 1)), "activity_weight": {1: 1.3, 2: 1.2, 3: 1.0}[int(r["activity_priority"])], "contract_weight_per_day": weight10[r["contract_number"]] / 10, "footprint_locations": len(footprints[a]), "predecessor": r["predecessor_activity_id"]} for a, r in activities.items()])
    report["exhaustive_a_pair"] = exhaustive_a_pair()
    relaxed = report["enumerated_contract_relaxations"]
    ca, cb = activities["A036"]["contract_number"], activities["A075"]["contract_number"]
    a_bound = relaxed["A"]["score"] - relaxed["A"]["contracts"][ca]["bound"] - relaxed["A"]["contracts"][cb]["bound"] + report["exhaustive_a_pair"]["minimum_pair_cost"]
    bounds = {"A": round(a_bound, 10), "B": relaxed["B"]["score"], "C": relaxed["C"]["score"]}
    report["analytical_lower_bounds"] = bounds
    report["independent_cp_relaxations"] = {}
    report["strictly_better_infeasibility_checks"] = {}
    for s in "ABC":
        print(f"Solving independent {s} relaxation...", flush=True)
        report["independent_cp_relaxations"][s] = model_check(s)
        assert report["independent_cp_relaxations"][s]["status"] == "OPTIMAL"
        assert report["independent_cp_relaxations"][s]["score"] == bounds[s]
        report["strictly_better_infeasibility_checks"][s] = model_check(s, strict_below=round(bounds[s] * 10), label=f"{s}_strictly_better")
        assert report["strictly_better_infeasibility_checks"][s]["status"] == "INFEASIBLE"
    report["sensitivity"] = {
        "A_without_pm_closure": model_check("A", pm=False, label="A_no_pm_closure"),
        "C_without_two_week_eclo_window": model_check("C", c_window=False, label="C_no_eclo_window"),
        "A_keep_A075_on_time": model_check("A", finish_by={"A075": due_week[cb]}, label="A_keep_A075_on_time"),
        "B_at_most_five_eclo": model_check("B", eclo_budget=5, label="B_eclo_budget_five"),
        "C_at_most_three_eclo": model_check("C", eclo_budget=3, label="C_eclo_budget_three"),
        "C_A036_on_time": model_check("C", finish_by={"A036": due_week[ca]}, label="C_A036_on_time"),
    }
    assert report["sensitivity"]["A_without_pm_closure"]["score"] == 130.9
    assert report["sensitivity"]["C_without_two_week_eclo_window"]["score"] == 30.0
    assert report["sensitivity"]["A_keep_A075_on_time"]["score"] == 173.6
    assert report["sensitivity"]["B_at_most_five_eclo"]["status"] == "INFEASIBLE"
    assert report["sensitivity"]["C_at_most_three_eclo"]["score"] == 98.2
    assert report["sensitivity"]["C_A036_on_time"]["status"] == "INFEASIBLE"
    report["feasible_witnesses"] = witnesses()
    report["exact_optima"] = {s: {"lower_bound": bounds[s], "achieved_upper_bound": report["feasible_witnesses"][s]["score"], "absolute_gap": round(report["feasible_witnesses"][s]["score"] - bounds[s], 10)} for s in "ABC"}
    assert all(r["absolute_gap"] == 0 for r in report["exact_optima"].values())
    dump("CERTIFICATE.json", report)
    print(json.dumps({"exact_optima": report["exact_optima"], "a_exhaustive": report["exhaustive_a_pair"], "sensitivity": report["sensitivity"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
