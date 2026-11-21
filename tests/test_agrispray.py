import pytest
from agrispray import DroneUnit, SprayMission, AgriSprayFleetManager


def test_mission_scheduling_and_refills():
    mgr = AgriSprayFleetManager()
    mgr.register_drone(DroneUnit(drone_id="DRN-01", model="Agras-T30", tank_capacity_liters=30.0, battery_pct=92.0))

    m1 = SprayMission(
        mission_id="MSN-101",
        field_name="North Citrus Orchard",
        area_hectares=15.0,
        target_dosage_l_per_ha=3.0,
        wind_speed_kmh=12.5,
        assigned_drone_id="DRN-01",
    )
    plan = mgr.schedule_mission(m1)
    assert plan["status"] == "READY"
    assert plan["required_liters"] == 45.0
    assert plan["refill_stops"] == 1
    assert plan["wind_safe"] is True
    assert plan["thermal_safe"] is True
    assert plan["estimated_flight_km"] > 0


def test_high_wind_and_low_battery_safety_holds():
    mgr = AgriSprayFleetManager()
    mgr.register_drone(DroneUnit(drone_id="DRN-02", model="Agras-T10", tank_capacity_liters=10.0, battery_pct=20.0))

    windy = SprayMission(
        mission_id="MSN-102",
        field_name="East Olive Grove",
        area_hectares=5.0,
        target_dosage_l_per_ha=2.0,
        wind_speed_kmh=28.0,
        assigned_drone_id="DRN-02",
    )
    assert mgr.schedule_mission(windy)["status"] == "HOLD_HIGH_WIND"

    low_bat = SprayMission(
        mission_id="MSN-103",
        field_name="West Vineyard",
        area_hectares=4.0,
        target_dosage_l_per_ha=2.0,
        wind_speed_kmh=10.0,
        assigned_drone_id="DRN-02",
    )
    assert mgr.schedule_mission(low_bat)["status"] == "HOLD_LOW_BATTERY"
    summary = mgr.fleet_analytics()
    assert summary["total_missions"] == 2
    assert summary["hold_missions"] == 2
    assert summary["total_pesticide_liters"] == 18.0


def test_thermal_evaporation_hold_and_mission_completion():
    mgr = AgriSprayFleetManager()
    mgr.register_drone(DroneUnit(drone_id="DRN-03", model="Agras-T40", tank_capacity_liters=40.0, battery_pct=85.0))

    hot_dry = SprayMission(
        mission_id="MSN-201",
        field_name="South Melon Field",
        area_hectares=8.0,
        target_dosage_l_per_ha=2.5,
        wind_speed_kmh=14.0,
        assigned_drone_id="DRN-03",
        ambient_temp_c=38.5,
        relative_humidity_pct=19.0,
    )
    plan_hold = mgr.schedule_mission(hot_dry)
    assert plan_hold["status"] == "HOLD_THERMAL_EVAPORATION"
    assert plan_hold["thermal_safe"] is False

    with pytest.raises(RuntimeError):
        mgr.complete_mission("MSN-201")

    optimal = SprayMission(
        mission_id="MSN-202",
        field_name="Central Wheat Block",
        area_hectares=10.0,
        target_dosage_l_per_ha=2.0,
        wind_speed_kmh=9.0,
        assigned_drone_id="DRN-03",
        ambient_temp_c=24.0,
        relative_humidity_pct=60.0,
    )
    mgr.schedule_mission(optimal)
    done = mgr.complete_mission("MSN-202", actual_liters_used=19.6)
    assert done["status"] == "COMPLETED"
    assert done["actual_liters_dispensed"] == 19.6
    assert done["dosage_variance_pct"] == -2.0
    assert done["remaining_battery_pct"] == 67.0
    assert mgr.fleet_analytics()["completed_missions"] == 1
    assert mgr.fleet_analytics()["actual_liters_dispensed"] == 19.6


def test_recharge_drone_releases_low_battery_holds():
    mgr = AgriSprayFleetManager()
    mgr.register_drone(DroneUnit(drone_id="DRN-04", model="Agras-T20", tank_capacity_liters=20.0, battery_pct=18.0))
    m = SprayMission(
        mission_id="MSN-301",
        field_name="East Barley Plot",
        area_hectares=6.0,
        target_dosage_l_per_ha=2.0,
        wind_speed_kmh=11.0,
        assigned_drone_id="DRN-04",
    )
    assert mgr.schedule_mission(m)["status"] == "HOLD_LOW_BATTERY"

    recharge_res = mgr.recharge_drone("DRN-04", target_pct=95.0)
    assert recharge_res["battery_pct"] == 95.0
    assert recharge_res["missions_released_to_ready"] == 1
    assert m.status == "READY"

