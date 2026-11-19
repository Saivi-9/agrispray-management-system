"""
AgriSpray Management System — Intelligent Drone Pesticide & Mission Telemetry Engine
"""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class DroneUnit:
    drone_id: str
    model: str
    tank_capacity_liters: float
    battery_pct: float
    flow_rate_l_per_min: float = 2.4


@dataclass
class SprayMission:
    mission_id: str
    field_name: str
    area_hectares: float
    target_dosage_l_per_ha: float
    wind_speed_kmh: float
    assigned_drone_id: str
    status: str = "SCHEDULED"

    @property
    def total_pesticide_required_liters(self) -> float:
        return round(self.area_hectares * self.target_dosage_l_per_ha, 2)

    @property
    def is_wind_safe(self) -> bool:
        """Agricultural drone spraying requires wind speed <= 22.0 km/h to prevent drift."""
        return self.wind_speed_kmh <= 22.0


class AgriSprayFleetManager:
    """Manages agricultural spraying drones, mission scheduling, and pesticide analytics."""

    def __init__(self) -> None:
        self.drones: Dict[str, DroneUnit] = {}
        self.missions: List[SprayMission] = []

    def register_drone(self, drone: DroneUnit) -> None:
        self.drones[drone.drone_id] = drone

    def schedule_mission(self, mission: SprayMission) -> Dict[str, object]:
        if mission.assigned_drone_id not in self.drones:
            raise ValueError(f"Unknown drone ID: {mission.assigned_drone_id}")

        drone = self.drones[mission.assigned_drone_id]
        required_l = mission.total_pesticide_required_liters
        refill_stops = max(0, int((required_l - 0.001) // drone.tank_capacity_liters)) if required_l > 0 else 0
        spray_duration_min = round(required_l / drone.flow_rate_l_per_min, 2)

        if not mission.is_wind_safe:
            mission.status = "HOLD_HIGH_WIND"
        elif drone.battery_pct < 30.0:
            mission.status = "HOLD_LOW_BATTERY"
        else:
            mission.status = "READY"

        self.missions.append(mission)
        return {
            "mission_id": mission.mission_id,
            "status": mission.status,
            "required_liters": required_l,
            "refill_stops": refill_stops,
            "estimated_spray_minutes": spray_duration_min,
            "wind_safe": mission.is_wind_safe,
        }

    def fleet_analytics(self) -> Dict[str, object]:
        total_ha = round(sum(m.area_hectares for m in self.missions), 2)
        total_liters = round(sum(m.total_pesticide_required_liters for m in self.missions), 2)
        ready_count = sum(1 for m in self.missions if m.status == "READY")
        return {
            "registered_drones": len(self.drones),
            "total_missions": len(self.missions),
            "ready_missions": ready_count,
            "total_area_hectares": total_ha,
            "total_pesticide_liters": total_liters,
        }
