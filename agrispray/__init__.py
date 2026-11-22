"""
AgriSpray Management System — Intelligent Drone Pesticide & Mission Telemetry Engine
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class DroneUnit:
    drone_id: str
    model: str
    tank_capacity_liters: float
    battery_pct: float
    flow_rate_l_per_min: float = 2.4
    swath_width_m: float = 6.5


@dataclass
class SprayMission:
    mission_id: str
    field_name: str
    area_hectares: float
    target_dosage_l_per_ha: float
    wind_speed_kmh: float
    assigned_drone_id: str
    ambient_temp_c: float = 25.0
    relative_humidity_pct: float = 55.0
    status: str = "SCHEDULED"
    actual_liters_dispensed: Optional[float] = None

    @property
    def total_pesticide_required_liters(self) -> float:
        return round(self.area_hectares * self.target_dosage_l_per_ha, 2)

    @property
    def is_wind_safe(self) -> bool:
        """Agricultural drone spraying requires wind speed <= 22.0 km/h to prevent drift."""
        return self.wind_speed_kmh <= 22.0

    @property
    def is_thermal_safe(self) -> bool:
        """Prevents fine-droplet evaporation before canopy deposition (<= 35 C and >= 25% RH)."""
        return self.ambient_temp_c <= 35.0 and self.relative_humidity_pct >= 25.0

    @property
    def dosage_variance_pct(self) -> Optional[float]:
        """Percentage variance between actual dispensed liters and planned required liters."""
        if self.actual_liters_dispensed is None or self.total_pesticide_required_liters <= 0:
            return None
        delta = self.actual_liters_dispensed - self.total_pesticide_required_liters
        return round((delta / self.total_pesticide_required_liters) * 100.0, 2)



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
        flight_distance_km = round((mission.area_hectares * 10.0 / max(drone.swath_width_m, 0.1)) * 1.15, 2)

        if not mission.is_wind_safe:
            mission.status = "HOLD_HIGH_WIND"
        elif not mission.is_thermal_safe:
            mission.status = "HOLD_THERMAL_EVAPORATION"
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
            "estimated_flight_km": flight_distance_km,
            "wind_safe": mission.is_wind_safe,
            "thermal_safe": mission.is_thermal_safe,
        }

    def complete_mission(self, mission_id: str, actual_liters_used: Optional[float] = None) -> Dict[str, object]:
        mission = next((m for m in self.missions if m.mission_id == mission_id), None)
        if mission is None:
            raise ValueError(f"Unknown mission ID: {mission_id}")
        if mission.status != "READY":
            raise RuntimeError(f"Cannot complete mission {mission_id} with status {mission.status}")

        drone = self.drones[mission.assigned_drone_id]
        dispensed = round(
            actual_liters_used if actual_liters_used is not None else mission.total_pesticide_required_liters,
            2,
        )
        mission.actual_liters_dispensed = dispensed
        mission.status = "COMPLETED"
        drone.battery_pct = round(max(0.0, drone.battery_pct - mission.area_hectares * 1.8), 2)

        return {
            "mission_id": mission.mission_id,
            "status": mission.status,
            "actual_liters_dispensed": dispensed,
            "dosage_variance_pct": mission.dosage_variance_pct,
            "remaining_battery_pct": drone.battery_pct,
        }

    def recharge_drone(self, drone_id: str, target_pct: float = 100.0) -> Dict[str, object]:
        if drone_id not in self.drones:
            raise ValueError(f"Unknown drone ID: {drone_id}")
        drone = self.drones[drone_id]
        drone.battery_pct = round(max(0.0, min(100.0, target_pct)), 2)

        released = 0
        for m in self.missions:
            if m.assigned_drone_id == drone_id and m.status == "HOLD_LOW_BATTERY":
                if drone.battery_pct >= 30.0 and m.is_wind_safe and m.is_thermal_safe:
                    m.status = "READY"
                    released += 1
        return {
            "drone_id": drone_id,
            "battery_pct": drone.battery_pct,
            "missions_released_to_ready": released,
        }

    def update_weather_conditions(
        self,
        mission_id: str,
        wind_speed_kmh: float,
        ambient_temp_c: float = 25.0,
        relative_humidity_pct: float = 55.0,
    ) -> Dict[str, object]:
        """Re-evaluate mission safety holds when field meteorological telemetry updates."""
        mission = next((m for m in self.missions if m.mission_id == mission_id), None)
        if mission is None:
            raise ValueError(f"Unknown mission ID: {mission_id}")
        if mission.status == "COMPLETED":
            raise RuntimeError(f"Cannot update weather for completed mission {mission_id}")

        mission.wind_speed_kmh = wind_speed_kmh
        mission.ambient_temp_c = ambient_temp_c
        mission.relative_humidity_pct = relative_humidity_pct
        drone = self.drones[mission.assigned_drone_id]

        if not mission.is_wind_safe:
            mission.status = "HOLD_HIGH_WIND"
        elif not mission.is_thermal_safe:
            mission.status = "HOLD_THERMAL_EVAPORATION"
        elif drone.battery_pct < 30.0:
            mission.status = "HOLD_LOW_BATTERY"
        else:
            mission.status = "READY"

        return {
            "mission_id": mission.mission_id,
            "status": mission.status,
            "wind_safe": mission.is_wind_safe,
            "thermal_safe": mission.is_thermal_safe,
        }


    def fleet_analytics(self) -> Dict[str, object]:
        total_ha = round(sum(m.area_hectares for m in self.missions), 2)
        total_liters = round(sum(m.total_pesticide_required_liters for m in self.missions), 2)
        actual_dispensed = round(
            sum(m.actual_liters_dispensed for m in self.missions if m.actual_liters_dispensed is not None),
            2,
        )
        ready_count = sum(1 for m in self.missions if m.status == "READY")
        completed_count = sum(1 for m in self.missions if m.status == "COMPLETED")
        hold_count = sum(1 for m in self.missions if m.status.startswith("HOLD_"))
        return {
            "registered_drones": len(self.drones),
            "total_missions": len(self.missions),
            "ready_missions": ready_count,
            "completed_missions": completed_count,
            "hold_missions": hold_count,
            "total_area_hectares": total_ha,
            "total_pesticide_liters": total_liters,
            "actual_liters_dispensed": actual_dispensed,
        }
