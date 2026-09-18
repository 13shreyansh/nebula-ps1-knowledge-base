from __future__ import annotations

from .instance import Activity, InputError, Instance


def split_sector_location(location_id: str) -> tuple[str, str, str]:
    parts = location_id.split(":")
    if len(parts) != 4 or parts[0] != "SEC" or "_" not in parts[2]:
        raise InputError(f"invalid sector location_id: {location_id}")
    return parts[1], ":".join(parts[:3]), parts[3]


def activity_footprint(instance: Instance, activity: Activity) -> tuple[str, ...]:
    start_line, start_sector_id, start_bound = split_sector_location(activity.start_location_id)
    end_line, end_sector_id, end_bound = split_sector_location(activity.end_location_id)
    if start_line != end_line or start_bound != end_bound:
        raise InputError(
            f"activity {activity.activity_id}: endpoints must use one line and bound"
        )
    try:
        start = instance.sectors[start_sector_id]
        end = instance.sectors[end_sector_id]
    except KeyError as exc:
        raise InputError(f"activity {activity.activity_id}: endpoint sector is undefined") from exc
    if start.line_code != start_line or end.line_code != start_line:
        raise InputError(f"activity {activity.activity_id}: sector line mismatch")

    low, high = sorted((start.seq, end.seq))
    corridor = sorted(
        (
            sector
            for sector in instance.sectors.values()
            if sector.line_code == start_line and low <= sector.seq <= high
        ),
        key=lambda sector: sector.seq,
    )
    expected_count = high - low + 1
    if len(corridor) != expected_count:
        raise InputError(f"activity {activity.activity_id}: non-contiguous sector sequence")

    station_ids = [corridor[0].from_station_id]
    station_ids.extend(sector.to_station_id for sector in corridor)
    locations = [f"SEC:{start_line}:{sector.sector_id.split(':', 2)[2]}:{start_bound}" for sector in corridor]
    locations.extend(f"PLAT:{start_line}:{station_id}:{start_bound}" for station_id in station_ids)
    missing = sorted(set(locations) - set(instance.locations))
    if missing:
        raise InputError(f"activity {activity.activity_id}: footprint locations missing: {missing}")
    return tuple(sorted(locations))


def affects_interchange_cross_line(instance: Instance, activity: Activity) -> bool:
    project = instance.projects[activity.contract_number]
    if project.nature_of_activity != "Live":
        return False
    return any(":H01_H02:" in location_id for location_id in activity_footprint(instance, activity))

