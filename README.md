# AgriSpray Management System — Intelligent Drone Pesticide & Mission Telemetry

An intelligent agricultural drone pesticide management engine for scheduling spraying missions, calculating dosage and tank refill stops, enforcing wind-drift and battery safety thresholds, and aggregating fleet pesticide usage analytics.

## Features

- **Precision Dosage, Swath Distance & Tank Refill Planner (`SprayMission`)**: Computes total pesticide volume (`L/ha * ha`), nozzle spray duration, swath-adjusted flight distance (`km`), and automated tank refill stops based on drone payload capacity.
- **Automated Meteorological, Thermal Evaporation & Battery Safety Cutoff**: Places missions on `HOLD_HIGH_WIND` when wind speeds exceed `22.0 km/h`, `HOLD_THERMAL_EVAPORATION` when ambient temperature exceeds `35.0 °C` or relative humidity drops below `25%`, or `HOLD_LOW_BATTERY` when charge is below `30%`.
- **Mission Execution & Fleet Analytics (`AgriSprayFleetManager`)**: Tracks mission completion (`complete_mission`), post-flight battery depletion, total hectares covered, total pesticide volume dispensed, and mission readiness/hold counts across the fleet.

## Quick Start

```bash
pip install -r requirements.txt
pytest tests/ -v
```
