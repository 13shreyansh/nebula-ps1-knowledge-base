from __future__ import annotations

from .instance import Activity, InputError, Instance


def split_sector_location(location_id: str) -> tuple[str, str, str]:
    parts = location_id.split(":")
    if len(parts) != 4 or parts[0] != "SEC" or "_" not in parts[2]:
        raise InputError(f"invalid sector location_id: {location_id}")
    return parts[1], ":".join(parts[:3]), parts[3]


def activity_footprint(instance: Instance, activity: Activity) -> tuple[str, ...]:
    cached = instance._activity_footprint_cache.get(activity)
    if cached is not None:
        return cached

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
    footprint = tuple(sorted(locations))
    instance._activity_footprint_cache.setdefault(activity, footprint)
    return instance._activity_footprint_cache[activity]


def affects_interchange_cross_line(instance: Instance, activity: Activity) -> bool:
    project = instance.projects[activity.contract_number]
    if project.nature_of_activity != "Live":
        return False
    return bool(interchange_cross_line_locations(instance, activity))


def interchange_cross_line_locations(instance: Instance, activity: Activity) -> tuple[str, ...]:
    """Derive Live interchange crossover locations from station metadata.

    A crossover bridge is a worked sector whose two endpoint stations are marked
    as interchanges. Matching endpoint pairs on other lines, in both bounds, plus
    their platforms are affected. No public station or sector identifier is baked
    into this derivation.
    """

    footprint_sector_ids = {
        ":".join(location_id.split(":")[:3])
        for location_id in activity_footprint(instance, activity)
        if location_id.startswith("SEC:")
    }
    worked_bridges = [
        sector
        for sector_id, sector in instance.sectors.items()
        if sector_id in footprint_sector_ids
        and instance.stations[(sector.line_code, sector.from_station_id)].is_interchange
        and instance.stations[(sector.line_code, sector.to_station_id)].is_interchange
    ]
    affected: set[str] = set()
    for bridge in worked_bridges:
        endpoints = {bridge.from_station_id, bridge.to_station_id}
        for other in instance.sectors.values():
            if other.line_code == bridge.line_code:
                continue
            if {other.from_station_id, other.to_station_id} != endpoints:
                continue
            if not (
                instance.stations[(other.line_code, other.from_station_id)].is_interchange
                and instance.stations[(other.line_code, other.to_station_id)].is_interchange
            ):
                continue
            local_sector = other.sector_id.split(":", 2)[2]
            for bound in ("EB", "WB"):
                affected.add(f"SEC:{other.line_code}:{local_sector}:{bound}")
                affected.add(f"PLAT:{other.line_code}:{other.from_station_id}:{bound}")
                affected.add(f"PLAT:{other.line_code}:{other.to_station_id}:{bound}")
    return tuple(sorted(affected))
