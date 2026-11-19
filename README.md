# AgriSpray Management System — Intelligent Drone Pesticide & Mission Telemetry

An intelligent agricultural drone pesticide management engine for scheduling spraying missions, calculating dosage and tank refill stops, enforcing wind-drift and battery safety thresholds, and aggregating fleet pesticide usage analytics.

## Features

- **Precision Dosage & Tank Refill Planner (`SprayMission`)**: Computes total pesticide volume (`L/ha * ha`), nozzle spray duration, and automated tank refill stops based on drone payload capacity.
- **Automated Meteorological & Battery Safety Cutoff**: Places missions on `HOLD_HIGH_WIND` when wind speeds exceed `22.0 km/h` (preventing off-target chemical drift) or `HOLD_LOW_BATTERY` when charge is below `30%`.
- **Fleet Analytics (`AgriSprayFleetManager`)**: Tracks total hectares covered, total pesticide volume dispensed, and mission readiness across the fleet.

## Quick Start

```bash
pip install -r requirements.txt
pytest tests/ -v
```
