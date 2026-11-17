# GTA6 Twitch CCU Forecaster

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/RobertAlbert11/gta6-twitch-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/RobertAlbert11/gta6-twitch-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecasts Grand Theft Auto VI'"'"'s launch-day (2026-11-19) Twitch concurrent viewers for hours 2–24, as five quantiles per hour, for make.fun'"'"'s [gta6-twitch-ccu-forecast-01](https://make.fun/bounty/gta6-twitch-ccu-forecast-01) bounty.

## How it works
Reads hour 1'"'"'s category print, then forecasts each hour with:
- a **comparables ensemble**: 37+ past game launches'"'"' hour-of-day curves (log ratios to their own hour-1 print), median-blended with scale-similarity and recency weights
- **empirical residual quantiles**: leave-one-out residual distributions pooled across comparables, blended with a Gaussian √h spread
- shrunk medians (×1.45) for honest coverage (~0.94) and a low pinball loss

## Run
```
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```
Python 3.13, standard library only, offline, deterministic.

Practice (real ground truth): mean loss **0.1955** vs house baseline 0.387 — see MODEL.md.
