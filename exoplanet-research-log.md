# Exoplanet Transit Detection — Research Log

**Researcher:** Chloey Fang
**Project:** Detecting an exoplanet with the transit method
**Target star:** Kepler-10 (host of Kepler-10b, Kepler's first confirmed rocky planet)
**Goal:** Build a Python pipeline that downloads a light curve, cleans and flattens it,
searches for transits with Box Least Squares (BLS), phase-folds the data, and estimates
the planet's radius relative to its star.

---

## Pipeline overview

| Step | What I do | Why (the physics) |
|------|-----------|-------------------|
| 1 | Set up venv + install `lightkurve`, `astropy` | Isolate project dependencies |
| 2 | Download Kepler-10 light curve | Light curve = brightness vs. time, from MAST archive |
| 3 | Clean + flatten | Remove slow stellar/instrument drift so transits stand out |
| 4 | BLS period search | Find the periodic box-shaped dip = orbital period |
| 5 | Phase-fold | Stack all transits to boost signal-to-noise |
| 6 | Estimate radius | depth = (R_planet / R_star)^2 |

---

## Environment notes
- OS: macOS (Darwin 21.6).
- Python: 3.13.7, installed from the **python.org** installer (Python.framework build).
- Project folder: `~/exoplanet-detection/`, virtual environment in `venv/`.
- Key packages: lightkurve, astropy, certifi 2026.5.20 (+ numpy, scipy, matplotlib, pandas as deps).
- **Reproducibility fix baked into the script:** the first lines set the SSL certificate
  bundle from certifi (see Session 4) so the pipeline downloads data on any fresh terminal.

---

## Log entries

### Session 1 — 2026-06-14 — Environment setup
- Created project folder `exoplanet-detection/`.
- Built a virtual environment: `python3 -m venv venv` (Python 3.13.7).
- Activated it: `source venv/bin/activate`.
- Verified isolation with `which python3` → confirmed it points inside venv/.
- Learned WHY we isolate: avoids version collisions between projects and makes the
  environment reproducible (part of the research methodology).
- Next: install lightkurve and astropy.

### Session 2 — 2026-06-14 — Installing the libraries
- Installed both with: `python3 -m pip install astropy lightkurve`.
- lightkurve pulled in numpy, scipy, astropy, matplotlib, pandas as dependencies.
- Note: lightkurve already depends on astropy, but I named astropy explicitly because my
  code imports it directly — good practice to declare direct dependencies.
- Verified versions with `python3 -m pip show lightkurve` / `... astropy`.
- Learned: `pip show` proves a package is *installed*; only an `import` proves it *runs*.
- Next: write a script to download Kepler-10's light curve.

### Session 3 — 2026-06-14 — First script + slow-import 
- Wrote `transit_pipeline.py`: import lightkurve, `search_lightcurve("Kepler-10")`, print.
- Workflow: edit in `nano`, save (Ctrl+O/Enter), exit (Ctrl+X), run `python3 transit_pipeline.py`.
- Key Python lessons: strings need quotes; a function call returns a value that must be
  stored in a variable with `=`; in a *script* nothing shows unless you wrap it in `print()`.
- **Problem:** first run looked frozen. Hit Ctrl+C → traceback showed it was still inside
  `import lightkurve` loading scipy. Diagnosis: the *first* import compiles bytecode for the
  whole scipy/numpy stack, which is slow once; later runs are cached and fast. Not a bug.
- Lesson: a long pause on first run ≠ a crash. Wait it out before interrupting.

### Session 4 — 2026-06-14 — SSL certificate debugging 
- **Problem:** script failed with `SSLCertVerificationError: CERTIFICATE_VERIFY_FAILED —
  unable to get local issuer certificate` when contacting the MAST archive (mast.stsci.edu).
- **What it means:** for an HTTPS connection, Python must verify the server's certificate
  against a trusted list of certificate authorities. The python.org macOS build ships
  *without* installing that trusted-CA bundle, so Python couldn't verify MAST and refused.
- **Ruled out a network firewall:** ran `curl -sS -o /dev/null -w "%{http_code}\n"
  https://mast.stsci.edu` → returned `301`. curl uses the macOS system trust store, so a
  success there proved the home network/Mac trust MAST fine — the problem was Python-only.
- Confirmed certifi (the trusted-CA bundle package) was present and current: version 2026.5.20.
- Direct test `python3 -c "import requests; requests.get('https://mast.stsci.edu')"` → `200`
  once the cert path was set, confirming requests could verify.
- **Durable fix (baked into the script, above the lightkurve import):**
      import certifi, os
      os.environ["SSL_CERT_FILE"] = certifi.where()
      os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
  - Two variables because the two networking layers read different ones: Python's stdlib SSL
    reads `SSL_CERT_FILE`; the `requests` library reads `REQUESTS_CA_BUNDLE`.
  - Must come *before* `import lightkurve`, because libraries read these vars as they load.
  - Putting the fix in the script (vs. a one-off `export`) keeps the pipeline reproducible.
- Lesson: when only Python fails but curl works, suspect Python's certificate setup, not
  the network.

### Session 5 — 2026-06-14 — Search succeeded
- `search_lightcurve("Kepler-10")` returned **109 data products** (a catalog, not the data).
- Read the table: two missions (Kepler rows 0–48, TESS rows 49+); `author` = the reduction
  pipeline (`Kepler` = official NASA pipeline); `exptime` = cadence (Kepler 60 s short /
  1800 s long); `target_name` `kplr011904151` = Kepler-10's Kepler Input Catalog ID.
- **Decision:** filter to mission=Kepler, author="Kepler", cadence="long" — the discovery
  dataset, long continuous baseline, manageable file sizes.
- **Plan:** download *all* Kepler long-cadence quarters and stitch them, because Kepler-10b's
  transit is only ~150 ppm deep — too shallow for one transit, so we stack hundreds of them.
- Next: re-run the search with the filters, then download all quarters.

### Session 6 — 2026-06-14 — Filtered search, download, and stitch
- Re-ran the search with filters: `lk.search_lightcurve("Kepler-10", author="Kepler",
  cadence="long")` → **15 products**, one per Kepler quarter (Q00–Q17).
- Noticed gaps: Q08, Q12, Q16 are missing. Reason: Kepler rolled 90° every quarter, so the
  star landed on a different CCD each season; **Module 3 failed in 2010**, so whenever the
  roll put Kepler-10 on that dead module there's no data. Instrument scars are visible in
  the data.
- Downloaded all 15 with `lc_collection = search_result.download_all()` → returned a
  `LightCurveCollection` of 15 `KeplerLightCurve` objects. Files cache locally after first
  download. All have `FLUX_ORIGIN=pdcsap_flux`.
- **PDCSAP vs SAP:** SAP = raw summed aperture flux (still has instrument drift); PDCSAP =
  same data after NASA's pipeline removed known instrument systematics. lightkurve defaults
  to PDCSAP — good for transit hunting. (It leaves *astrophysical* variability like starspots
  in, which is why we still flatten ourselves later.)
- Stitched into one light curve: `lc = lc_collection.stitch()`.
  - **Why stitch normalizes first:** each quarter sits at a different absolute flux level
    (different CCD/aperture each roll). `stitch()` divides each quarter by its median so
    every quarter is centered on 1.0, then concatenates — avoids fake step-jumps between
    quarters. Normalized flux is also the natural unit: a transit is a *fractional* dip.
- Result: **52,195 data points** spanning time ≈ 120–1591 days (~4 years). flux ~1.0,
  flux_err ≈ 40 ppm (smaller than the ~150 ppm transit depth — that's why detection works).
- Next: plot the raw stitched light curve (save to PNG), then flatten it.

### Session 7 — 2026-06-15 — Plotting + cleaning/flattening
- Plotting from a terminal script: a script doesn't pop open plot windows, so I save figures
  to PNG instead — `lc.plot()` then `plt.savefig("name.png")` (needs `import matplotlib.pyplot
  as plt` at the top), then `open name.png`. Bonus: PNGs are artifacts for the write-up.
- Python lesson (syntax error): two statements can't share one line — `lc.plot()` and
  `plt.savefig(...)` each need their own line (Python uses the newline as "end of statement").
- Environment lesson: a venv activation only lasts the current terminal session. After
  reopening the terminal I had to re-run `cd ~/exoplanet-detection` + `source venv/bin/activate`.
  Also ran the script with the wrong name (`transit_detection.py` vs the real
  `transit_pipeline.py`) — `ls` confirms the actual filename. Cached data made the rerun fast.
- **Raw stitched plot (`stitched_lightcurve.png`):** baseline ~1.0 with ±500 ppm scatter,
  visible gaps (missing quarters + data-downlink breaks), and several upward spikes. The
  spikes point UP, but transits dip DOWN, so they can't be transits — they're outliers
  (cosmic rays / flares / glitches). No transit visible by eye (150 ppm < 500 ppm scatter).
- **Cleaned + flattened:** `lc_clean = lc.remove_outliers().flatten()`.
  - `remove_outliers()` = sigma clipping (default 5σ) — drops the big anomalies; 150 ppm
    transits are far inside 5σ so they survive.
  - `flatten()` = fits a smooth trend that follows slow variations but is too smooth to bend
    into a ~2 hr transit, then divides it out. `window_length` (default 101 pts ≈ 2 days) must
    be much wider than a transit but narrower than the stellar wiggles. Removed the slow wobble
    (e.g. the t≈800–900 bulge) and left a flat 1.0 baseline.
- **Plot-reading gotcha (`flattened_lightcurve.png`):** looked "spikier," but that's just
  matplotlib auto-zooming the y-axis (range shrank from ~7500 ppm to ~2000 ppm once the tall
  spikes were removed) — same noise, bigger zoom. Diagonal lines across gaps are a plot
  artifact, not data. Transit still invisible by eye → motivates BLS.
- Next: run a Box Least Squares (BLS) period search over trial periods 0.5–5 days; expect a
  peak near the literature period of Kepler-10b ≈ 0.837 days.

### Session 8 — 2026-06-15 — BLS period search
- Built a trial-period grid with numpy: `period_grid = np.arange(0.5, 5, 0.001)` (0.5–5 d,
  step 0.001 d), then `bls = lc_clean.to_periodogram(method="bls", period=period_grid)`.
- **How BLS works:** for each trial period it folds the data and fits a rectangular "box" dip;
  at the true period all transits stack into one deep box → high power; at wrong periods they
  smear → low power. A transit really is ~box-shaped, so the box is the right template.
- Saved `bls_periodogram.png` (power vs. trial period) and printed
  `bls.period_at_max_power` → **1.675 d**.
- **Surprise:** 1.675 d, not the expected 0.837 d — but 1.675 ≈ 2 × 0.837.
- Periodogram is a comb of peaks all at integer multiples of 0.837 d (1.675 tallest, then
  3.35 = 4×, 2.51 = 3×, 4.18 = 5×). That comb = ONE real periodic signal (Kepler-10b) showing
  at its fundamental + harmonics; BLS just gave most power to the 2× harmonic (an alias).
- Lesson: BLS often locks onto a harmonic/multiple of the true period. Always sanity-check
  against expectations and resolve by folding.

### Session 9 — 2026-06-15 — Phase-fold + finding the true period
- **Phase-folding concept:** wrap the 4-yr timeline modulo the period (accordion-fold and
  stack), assigning each point a phase. ~1,500 orbits overlap → transits stack, noise averages
  down. This is what lifts the 150 ppm transit out of the 250 ppm noise.
- Folded with `lc_clean.fold(period=bls.period_at_max_power,
  epoch_time=bls.transit_time_at_max_power)`, plotted, saved.
- **Folded at 1.675 d (the alias):** saw a dip at phase 0 AND a dip split across the far
  edges (±0.83 d). The edge-dip is the second transit half a cycle away, wrapped around — the
  fingerprint that the period was doubled. Confirmed truth = 1.675 / 2 ≈ 0.837 d.
- **Re-folded at the true period** `bls.period_at_max_power / 2` (Python division operator `/`):
  the two dips merged into ONE clean V-shaped dip centered at phase 0, no edge dips. 
- **This is the detection of Kepler-10b.** Dip bottoms ~0.99985 → depth ≈ 150 ppm, matching
  the literature. Shape is V-ish/fuzzy because of noise.
- Next: bin the folded light curve (a few-min bins) to average down noise, then read off the
  transit depth and convert to planet radius via depth = (R_planet / R_star)^2.

### Session 10 — 2026-06-15 — Binning + planet radius (RESULT)
- **Binning concept:** each of the ~50k folded points is noisy (±250 ppm), bigger than the
  ~150 ppm transit. The noise is random but the transit is always at phase 0, so averaging
  points within small phase bins cancels noise (∝ 1/√N) and reveals the transit shape.
- Code: `import astropy.units as u`; `binned = folded.bin(time_bin_size=5 * u.min)`; plotted
  to `folded_binned.png`. Bin width (5 min) « transit duration (~2 h) so the shape isn't blurred.
- Result: a clean, flat-bottomed transit at phase 0. (matplotlib offset axis "+9.999e-1" means
  add 0.9999 to each tick label.)
- **Measured transit depth by eye:** baseline = 1.00000, dip bottom ≈ 0.99982 →
  **depth ≈ 0.00018 (180 ppm)**.
- **Radius from depth** (depth = (Rp/Rs)^2, so Rp = sqrt(depth) × Rstar):
  - sqrt(0.00018) ≈ 0.0134  (planet ≈ 1.34% of the star's radius)
  - Rstar ≈ 1.06 Rsun × 109 Rearth/Rsun ≈ 116 Rearth
  - **Rp ≈ 0.0134 × 116 ≈ 1.55 Rearth**
- **Comparison:** literature Kepler-10b radius ≈ 1.47 Rearth → my estimate is within ~5%. 
- **Likely error sources (why slightly high):** eyeballed depth read ~180 ppm vs true ~152 ppm;
  limb darkening rounds/deepens the transit center, so reading the very bottom overestimates the
  effective depth; plus stellar-radius uncertainty.
- **PIPELINE COMPLETE:** download → stitch → clean/flatten → BLS → phase-fold → bin → radius.
- Possible extensions: fit a proper transit model for a cleaner depth; propagate uncertainties
  with astropy units; hunt for the second planet Kepler-10c (P ≈ 45 d); write up results.

---

## Results summary

| Quantity | My measurement | Literature (Kepler-10b) | Notes |
|----------|----------------|--------------------------|-------|
| Orbital period | 0.837 d (from BLS, after halving the 1.675 d alias) | 0.8375 d | ~20-hour orbit |
| Transit depth | ~180 ppm (eyeballed) | ~152 ppm | overestimate (limb darkening + by-eye read) |
| Planet radius | ~1.55 R⊕ | ~1.47 R⊕ | within ~5% |

**Science interpretation:** Kepler-10b was the first unambiguously *rocky* exoplanet confirmed
(2011). My results match its claim to fame — a ~1.5 R⊕ super-Earth on a 20-hour orbit, so close
to its star it is a ~1800 K lava world. Detected by stacking ~1,500 transits to pull a 150 ppm
dip out of 250 ppm noise.

**Method, one line:** download all Kepler long-cadence quarters of KIC 11904151 → stitch
(normalize + concatenate) → remove outliers + flatten → BLS period search → phase-fold at the
true period → bin → measure depth → radius from depth = (Rp/Rstar)^2.

**Key gotchas solved along the way:** python.org macOS SSL cert fix (certifi env vars in-script);
first-import slowness (bytecode caching); per-session venv activation; BLS harmonic alias
(found 2× the true period); matplotlib y-axis offset notation.


