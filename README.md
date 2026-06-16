# Exoplanet Transit Detection — Kepler-10

Detecting the exoplanet Kepler-10b from NASA Kepler data using the transit 
method,
built as an independent high school astrophysics research project.

## What it does
A Python pipeline that:
1. Downloads Kepler-10's light curve from the MAST archive (lightkurve)
2. Stitches all Kepler long-cadence quarters and normalizes them
3. Removes outliers and flattens out stellar/instrument variability
4. Runs a Box Least Squares (BLS) search to find the orbital period
5. Phase-folds and bins the data to reveal the transit
6. Estimates the planet's radius from the transit depth

## Results
- Orbital period: ~0.837 days (a 20-hour orbit)
- Transit depth: ~180 ppm
- Planet radius: ~1.55 Earth radii (literature: ~1.47 — within ~5%)

Kepler-10b is a rocky "super-Earth" so close to its star it's a lava 
world.

## Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 transit_pipeline.py


See `exoplanet-research-log.md` for the full step-by-step research log.
