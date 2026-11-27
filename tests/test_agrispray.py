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


def test_update_weather_conditions_releases_and_applies_holds():
    mgr = AgriSprayFleetManager()
    mgr.register_drone(DroneUnit(drone_id="DRN-05", model="Agras-T30", tank_capacity_liters=30.0, battery_pct=90.0))
    m = SprayMission(
        mission_id="MSN-401",
        field_name="North Sunflowers",
        area_hectares=7.5,
        target_dosage_l_per_ha=2.0,
        wind_speed_kmh=26.5,
        assigned_drone_id="DRN-05",
    )
    assert mgr.schedule_mission(m)["status"] == "HOLD_HIGH_WIND"

    cleared = mgr.update_weather_conditions("MSN-401", wind_speed_kmh=14.0, ambient_temp_c=23.0, relative_humidity_pct=58.0)
    assert cleared["status"] == "READY"
    assert cleared["wind_safe"] is True
    assert cleared["thermal_safe"] is True


def test_reassign_mission_drone_updates_status_and_refills():
    mgr = AgriSprayFleetManager()
    mgr.register_drone(DroneUnit(drone_id="DRN-LOW", model="Agras-T10", tank_capacity_liters=10.0, battery_pct=15.0))
    mgr.register_drone(DroneUnit(drone_id="DRN-FULL", model="Agras-T40", tank_capacity_liters=40.0, battery_pct=96.0))

    m = SprayMission(
        mission_id="MSN-501",
        field_name="South Citrus Block",
        area_hectares=12.0,
        target_dosage_l_per_ha=2.5,
        wind_speed_kmh=10.0,
        assigned_drone_id="DRN-LOW",
    )
    assert mgr.schedule_mission(m)["status"] == "HOLD_LOW_BATTERY"

    reassigned = mgr.reassign_mission_drone("MSN-501", "DRN-FULL")
    assert reassigned["assigned_drone_id"] == "DRN-FULL"
    assert reassigned["status"] == "READY"
    assert reassigned["refill_stops"] == 0
    assert m.assigned_drone_id == "DRN-FULL"


def test_drone_utilization_report():
    mgr = AgriSprayFleetManager()
    mgr.register_drone(DroneUnit(drone_id="DRN-09", model="Agras-T30", tank_capacity_liters=30.0, battery_pct=88.0))
    m1 = SprayMission(
        mission_id="MSN-901",
        field_name="West Vineyard",
        area_hectares=5.0,
        target_dosage_l_per_ha=2.0,
        wind_speed_kmh=10.0,
        assigned_drone_id="DRN-09",
    )
    m2 = SprayMission(
        mission_id="MSN-902",
        field_name="Ridge Olive Plot",
        area_hectares=4.0,
        target_dosage_l_per_ha=2.5,
        wind_speed_kmh=25.0,
        assigned_drone_id="DRN-09",
    )
    mgr.schedule_mission(m1)
    mgr.schedule_mission(m2)
    mgr.complete_mission("MSN-901", actual_liters_used=10.0, battery_drain_pct=20.0)

    report = mgr.drone_utilization_report("DRN-09")
    assert report["drone_id"] == "DRN-09"
    assert report["assigned_missions_count"] == 2
    assert report["completed_missions_count"] == 1
    assert report["held_missions_count"] == 1
    assert report["total_assigned_hectares"] == 9.0
    assert report["total_dispensed_liters"] == 10.0
    assert report["battery_pct"] == 68.0
    assert report["needs_recharge"] is False


def test_weather_hold_summary():
    mgr = AgriSprayFleetManager()
    mgr.register_drone(DroneUnit(drone_id="DRN-10", model="Agras-T40", tank_capacity_liters=40.0, battery_pct=90.0))
    mgr.register_drone(DroneUnit(drone_id="DRN-11", model="Agras-T20", tank_capacity_liters=20.0, battery_pct=20.0))

    mgr.schedule_mission(
        SprayMission(
            mission_id="MSN-W1",
            field_name="Windy Ridge",
            area_hectares=6.0,
            target_dosage_l_per_ha=2.0,
            wind_speed_kmh=26.0,
            assigned_drone_id="DRN-10",
        )
    )
    mgr.schedule_mission(
        SprayMission(
            mission_id="MSN-T1",
            field_name="Arid South Block",
            area_hectares=4.0,
            target_dosage_l_per_ha=2.5,
            wind_speed_kmh=12.0,
            ambient_temp_c=38.0,
            relative_humidity_pct=20.0,
            assigned_drone_id="DRN-10",
        )
    )
    mgr.schedule_mission(
        SprayMission(
            mission_id="MSN-B1",
            field_name="Low Battery Meadow",
            area_hectares=3.0,
            target_dosage_l_per_ha=2.0,
            wind_speed_kmh=10.0,
            assigned_drone_id="DRN-11",
        )
    )

    summary = mgr.weather_hold_summary()
    assert summary["total_held_missions"] == 3
    assert summary["high_wind_holds"] == 1
    assert summary["thermal_evaporation_holds"] == 1
    assert summary["low_battery_holds"] == 1
    assert summary["held_area_hectares"] == 13.0
    assert summary["held_pesticide_liters"] == 28.0
    assert summary["held_mission_ids_by_reason"]["HOLD_HIGH_WIND"] == ["MSN-W1"]


def test_dosage_efficiency_report():
    mgr = AgriSprayFleetManager()
    mgr.register_drone(DroneUnit(drone_id="DRN-12", model="Agras-T40", tank_capacity_liters=40.0, battery_pct=95.0))

    m1 = SprayMission(
        mission_id="MSN-D1",
        field_name="Precision Block A",
        area_hectares=10.0,
        target_dosage_l_per_ha=2.0,
        wind_speed_kmh=10.0,
        assigned_drone_id="DRN-12",
    )
    m2 = SprayMission(
        mission_id="MSN-D2",
        field_name="Over-dispensed Block B",
        area_hectares=10.0,
        target_dosage_l_per_ha=2.0,
        wind_speed_kmh=11.0,
        assigned_drone_id="DRN-12",
    )
    mgr.schedule_mission(m1)
    mgr.schedule_mission(m2)
    mgr.complete_mission("MSN-D1", actual_liters_used=20.4, battery_drain_pct=15.0)
    mgr.complete_mission("MSN-D2", actual_liters_used=22.0, battery_drain_pct=15.0)

    report = mgr.dosage_efficiency_report(tolerance_pct=5.0)
    assert report["completed_missions_evaluated"] == 2
    assert report["planned_liters_total"] == 40.0
    assert report["actual_liters_total"] == 42.4
    assert report["overall_dosage_variance_pct"] == 6.0
    assert report["within_tolerance_count"] == 1
    assert report["out_of_tolerance_mission_ids"] == ["MSN-D2"]


def test_fleet_battery_readiness_audit():
    mgr = AgriSprayFleetManager()
    mgr.register_drone(DroneUnit(drone_id="DRN-A1", model="Agras-T40", tank_capacity_liters=40.0, battery_pct=90.0))
    mgr.register_drone(DroneUnit(drone_id="DRN-A2", model="Agras-T20", tank_capacity_liters=20.0, battery_pct=18.0))

    audit = mgr.fleet_battery_readiness_audit(min_ready_pct=30.0)
    assert audit["total_drones"] == 2
    assert audit["ready_drones_count"] == 1
    assert audit["low_battery_drones_count"] == 1
    assert audit["average_battery_pct"] == 54.0
    assert audit["low_battery_drone_ids"] == ["DRN-A2"]






