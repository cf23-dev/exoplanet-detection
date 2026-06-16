import astropy.units as u
import matplotlib.pyplot as plt
import certifi, os
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
import lightkurve as lk
search_result = lk.search_lightcurve("Kepler-10", author="Kepler", 
cadence="long")
lc_collection = search_result.download_all()
lc = lc_collection.stitch()
lc.plot()
plt.savefig("stitched_lightcurve.png")
lc_clean = lc.remove_outliers().flatten()
lc_clean.plot()
plt.savefig("flattened_lightcurve.png")
import numpy as np

period_grid = np.arange(0.5, 5, 0.001)          # trial periods from 0.5 to 5 days
bls = lc_clean.to_periodogram(method="bls", period=period_grid)
bls.plot()
plt.savefig("bls_periodogram.png")
print("Best period:", bls.period_at_max_power)
best_period = bls.period_at_max_power
best_t0 = bls.transit_time_at_max_power
folded = lc_clean.fold(period=bls.period_at_max_power/2, 
epoch_time=bls.transit_time_at_max_power)

binned = folded.bin(time_bin_size=5 * u.min)
binned.plot()
plt.savefig("folded_binned.png")


