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
    assert summary["total_pesticide_liters"] == 18.0
