# GTA VI Trophy Rarity Forecast

[![make.fun](https://img.shields.io/badge/make.fun-gta6--trophy--rarity--forecast--01-blue)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Forecasts each GTA VI (PS5) trophy's Exophase earn rate at 2026-11-26T00:00Z
as five quantiles, from the house's recorded reads up to the deadline.
Entry for the make.fun competition
[gta6-trophy-rarity-forecast-01](https://make.fun/bounty/gta6-trophy-rarity-forecast-01).

`main.py` (Python 3.13, stdlib only, no network) grows each trophy's earned
count and the tracked-player count separately in log-time since release,
catches both up over the hours since Exophase last refreshed, then divides
again. See `STRATEGY.md`.
