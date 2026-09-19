from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Protocol

from .instance import Instance
from .topology import activity_footprint, split_sector_location


class AccessLike(Protocol):
    activity_id: str
    week: int


class OccupancyLike(Protocol):
    activity_id: str
    week: int
    location_id: str
    co_share_group: str


@dataclass(frozen=True)
class ClosureConflict:
    week: int
    first_activities: tuple[str, ...]
    second_activities: tuple[str, ...]
    locations: tuple[str, ...]

    def describe(self) -> str:
        return (
            f"week {self.week}: closure conflict between {list(self.first_activities)} and "
            f"{list(self.second_activities)} at {list(self.locations)}"
        )


def _opposite(bound: str) -> str:
    return {"EB": "WB", "WB": "EB"}[bound]


def _replace_bound(location_id: str, bound: str) -> str:
    parts = location_id.split(":")
    parts[-1] = bound
    return ":".join(parts)


def _external_buffer_sectors(instance: Instance, activity_id: str) -> set[str]:
    activity = instance.activities[activity_id]
    project = instance.projects[activity.contract_number]
    distance = instance.buffers[project.nature_of_activity].up_to_buffer_sectors
    if distance == 0:
        return set()
    line, start_sector_id, bound = split_sector_location(activity.start_location_id)
    _, end_sector_id, _ = split_sector_location(activity.end_location_id)
    start_seq = instance.sectors[start_sector_id].seq
    end_seq = instance.sectors[end_sector_id].seq
    low, high = sorted((start_seq, end_seq))
    line_sectors = {
        sector.seq: sector
        for sector in instance.sectors.values()
        if sector.line_code == line
    }
    selected = [
        sector
        for seq, sector in line_sectors.items()
        if low - distance <= seq < low or high < seq <= high + distance
    ]
    return {
        f"SEC:{line}:{sector.sector_id.split(':', 2)[2]}:{bound}"
        for sector in selected
    }


def _interchange_cross_line_closure(instance: Instance, activity_id: str) -> set[str]:
    """Expand a Live interchange closure and its buffer onto the other line."""

    activity = instance.activities[activity_id]
    project = instance.projects[activity.contract_number]
    if project.nature_of_activity != "Live":
        return set()
    distance = instance.buffers[project.nature_of_activity].up_to_buffer_sectors
    worked_sector_ids = {
        ":".join(location_id.split(":")[:3])
        for location_id in activity_footprint(instance, activity)
        if location_id.startswith("SEC:")
    }
    worked_bridges = [
        sector
        for sector_id, sector in instance.sectors.items()
        if sector_id in worked_sector_ids
        and instance.stations[(sector.line_code, sector.from_station_id)].is_interchange
        and instance.stations[(sector.line_code, sector.to_station_id)].is_interchange
    ]
    affected: set[str] = set()
    for bridge in worked_bridges:
        endpoints = {bridge.from_station_id, bridge.to_station_id}
        for cross_bridge in instance.sectors.values():
            if cross_bridge.line_code == bridge.line_code:
                continue
            if {cross_bridge.from_station_id, cross_bridge.to_station_id} != endpoints:
                continue
            if not (
                instance.stations[
                    (cross_bridge.line_code, cross_bridge.from_station_id)
                ].is_interchange
                and instance.stations[
                    (cross_bridge.line_code, cross_bridge.to_station_id)
                ].is_interchange
            ):
                continue
            corridor = sorted(
                (
                    sector
                    for sector in instance.sectors.values()
                    if sector.line_code == cross_bridge.line_code
                    and cross_bridge.seq - distance <= sector.seq <= cross_bridge.seq + distance
                ),
                key=lambda sector: sector.seq,
            )
            for sector in corridor:
                local_sector = sector.sector_id.split(":", 2)[2]
                for bound in ("EB", "WB"):
                    affected.add(
                        f"SEC:{cross_bridge.line_code}:{local_sector}:{bound}"
                    )
                    affected.add(
                        f"PLAT:{cross_bridge.line_code}:{sector.from_station_id}:{bound}"
                    )
                    affected.add(
                        f"PLAT:{cross_bridge.line_code}:{sector.to_station_id}:{bound}"
                    )
    return affected


def _blocked_locations(instance: Instance, component: set[str]) -> set[str]:
    blocked: set[str] = set()
    for activity_id in sorted(component):
        activity = instance.activities[activity_id]
        project = instance.projects[activity.contract_number]
        footprint = set(activity_footprint(instance, activity))
        buffer_sectors = _external_buffer_sectors(instance, activity_id)
        blocked.update(footprint)
        blocked.update(buffer_sectors)
        if project.nature_of_activity != "Live":
            continue
        line, _, bound = split_sector_location(activity.start_location_id)
        opposite_bound = _opposite(bound)
        blocked.update(_replace_bound(location_id, opposite_bound) for location_id in footprint)
        blocked.update(_replace_bound(location_id, opposite_bound) for location_id in buffer_sectors)
        blocked.update(_interchange_cross_line_closure(instance, activity_id))
        # Official diagnostics include endpoint platforms of own-line Live
        # buffer sectors on both bounds, as well as the worked footprint.
        for location_id in buffer_sectors:
            _, buffer_line, sector_id, _ = location_id.split(":")
            sector = instance.sectors[f"SEC:{buffer_line}:{sector_id}"]
            for station in (sector.from_station_id, sector.to_station_id):
                for affected_bound in (bound, opposite_bound):
                    blocked.add(f"PLAT:{buffer_line}:{station}:{affected_bound}")
    return blocked


def _buffer_locations(instance: Instance, component: set[str]) -> set[str]:
    """Return external buffer sectors, including Live opposite-bound mirroring."""

    buffered: set[str] = set()
    for activity_id in sorted(component):
        activity = instance.activities[activity_id]
        project = instance.projects[activity.contract_number]
        external = _external_buffer_sectors(instance, activity_id)
        buffered.update(external)
        if project.nature_of_activity == "Live":
            _, _, bound = split_sector_location(activity.start_location_id)
            buffered.update(
                _replace_bound(location_id, _opposite(bound))
                for location_id in external
            )
    return buffered


def screen_closures(
    instance: Instance,
    access_rows: Iterable[AccessLike],
    occupancy_rows: Iterable[OccupancyLike],
    *,
    forbid_buffer_overlap: bool = False,
) -> tuple[ClosureConflict, ...]:
    """Screen possession-component closures under the published co-sharing model."""

    activities_by_week: dict[int, set[str]] = defaultdict(set)
    for row in access_rows:
        activities_by_week[row.week].add(row.activity_id)
    shared_groups: dict[tuple[int, str, str], list[str]] = defaultdict(list)
    for row in occupancy_rows:
        shared_groups[(row.week, row.location_id, row.co_share_group)].append(
            row.activity_id
        )

    conflicts: list[ClosureConflict] = []
    for week in sorted(activities_by_week):
        activity_ids = sorted(activities_by_week[week])
        parent = {activity_id: activity_id for activity_id in activity_ids}

        def find(activity_id: str) -> str:
            while parent[activity_id] != activity_id:
                parent[activity_id] = parent[parent[activity_id]]
                activity_id = parent[activity_id]
            return activity_id

        def union(first: str, second: str) -> None:
            first_root, second_root = find(first), find(second)
            if first_root != second_root:
                parent[second_root] = first_root

        for (group_week, _, _), grouped_activities in sorted(shared_groups.items()):
            if group_week != week or len(grouped_activities) < 2:
                continue
            ordered_group = sorted(set(grouped_activities))
            first = ordered_group[0]
            for other in ordered_group[1:]:
                union(first, other)

        components: dict[str, set[str]] = defaultdict(set)
        for activity_id in activity_ids:
            components[find(activity_id)].add(activity_id)
        component_data: list[tuple[set[str], set[str], set[str], set[str]]] = []
        ordered_components = sorted(
            components.values(), key=lambda component: tuple(sorted(component))
        )
        for component in ordered_components:
            work = {
                location_id
                for activity_id in sorted(component)
                for location_id in activity_footprint(
                    instance, instance.activities[activity_id]
                )
            }
            component_data.append(
                (
                    component,
                    work,
                    _blocked_locations(instance, component),
                    _buffer_locations(instance, component),
                )
            )

        for first_index, (
            first_component,
            _,
            first_blocked,
            first_buffer,
        ) in enumerate(component_data):
            for (
                second_component,
                _,
                second_blocked,
                second_buffer,
            ) in component_data[first_index + 1 :]:
                for intruder in sorted(first_component):
                    collision = set(
                        activity_footprint(instance, instance.activities[intruder])
                    ) & second_blocked
                    if collision:
                        conflicts.append(
                            ClosureConflict(
                                week=week,
                                first_activities=(intruder,),
                                second_activities=tuple(sorted(second_component)),
                                locations=tuple(sorted(collision)),
                            )
                        )
                for intruder in sorted(second_component):
                    collision = set(
                        activity_footprint(instance, instance.activities[intruder])
                    ) & first_blocked
                    if collision:
                        conflicts.append(
                            ClosureConflict(
                                week=week,
                                first_activities=(intruder,),
                                second_activities=tuple(sorted(first_component)),
                                locations=tuple(sorted(collision)),
                            )
                        )
                if forbid_buffer_overlap:
                    collision = first_buffer & second_buffer
                    if collision:
                        conflicts.append(
                            ClosureConflict(
                                week=week,
                                first_activities=tuple(sorted(first_component)),
                                second_activities=tuple(sorted(second_component)),
                                locations=tuple(sorted(collision)),
                            )
                        )
    return tuple(conflicts)
