"""New England TMAX pipeline for Part 3 of Lesson 1 (`01_intro_presentation.ipynb`).

This is a trimmed re-run of the experiment in Case Study 04
(`case_studies/04_learning_temperature_graphs.ipynb`), restricted to the three
constructions the talk compares:

    geographic kernel  ->  Kalofolias (learned graph)  ->  PCA (no graph)

Everything that matters for honesty is kept: the same station set and quality
control, the same daily-anomaly representation, the same season-balanced blocked
split with gap days, hyperparameters chosen on validation only, and test days
touched exactly once.

Data files expected under case_studies/data (all cached by Case Study 04, nothing is
downloaded):
    ghcn_tmax_ct_ri_ma_2015-08-06.csv   the single day that defines the station set
    ghcn_tmax_ct_ri_ma_2015_2017.csv    three years of daily TMAX
    cb_2023_us_state_500k.zip           Census cartographic state boundaries
    fits/                               cached Kalofolias solutions (optional)

Source: NOAA GHCN-Daily, https://www.ncei.noaa.gov/products/land-based-station/
global-historical-climatology-network-daily
"""

import os
import io
import sys
import zipfile
import hashlib

import numpy as np
import pandas as pd
import shapefile
from pyproj import Transformer

# The solver and the cached data belong to Case Study 04; find them from this file's
# location so the lesson runs whatever the working directory.
CASE_STUDIES = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                            "case_studies")
sys.path.insert(0, os.path.normpath(CASE_STUDIES))

import glearn as gl

SEED = 7
DATA_DIR = os.path.normpath(os.path.join(CASE_STUDIES, "data"))
CACHE_DIR = os.path.join(DATA_DIR, "fits")
YEARS = (2015, 2016, 2017)
COVERAGE_RULE = 0.90
CRS_PROJECTED = "EPSG:26986"          # NAD83 / Massachusetts Mainland, metres

# experiment settings, identical to Case Study 04
MASK_FRACTION = 0.20
MASK_REPEATS = 4
GAMMA_GRID = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0]
SIGMA_MULT_GRID = [0.25, 0.5, 1.0, 2.0]
KNN_GRID = [4, 6, 10]
KALO_GRID = [(a, b) for a in (0.5, 1.0, 2.0) for b in (0.1, 1.0, 10.0)]
PCA_GRID = [1, 2, 3, 5, 8, 12, 20]


# ----------------------------------------------------------------- stations
def _lesson3_stations():
    """Stations carrying a valid TMAX on 2015-08-06, de-duplicated by coordinates."""
    raw = pd.read_csv(os.path.join(DATA_DIR, "ghcn_tmax_ct_ri_ma_2015-08-06.csv"), dtype=str)
    at = raw["TMAX_ATTRIBUTES"].fillna("").str.split(",")
    raw["qflag"] = at.str[1].fillna("")
    raw["val"] = pd.to_numeric(raw["TMAX"], errors="coerce")
    ok = raw["val"].notna() & (raw["val"] != -9999) & (raw["qflag"] == "")
    sel = raw.loc[ok].copy()
    for c in ("LATITUDE", "LONGITUDE", "ELEVATION"):
        sel[c] = pd.to_numeric(sel[c])
    sel = (sel.sort_values("STATION")
              .drop_duplicates(subset=["LATITUDE", "LONGITUDE"], keep="first")
              .reset_index(drop=True))
    return sel.rename(columns={"STATION": "station", "LATITUDE": "lat",
                               "LONGITUDE": "lon", "ELEVATION": "elev_m"})[
        ["station", "lat", "lon", "elev_m"]]


meta0 = _lesson3_stations()
raw_year = pd.read_csv(os.path.join(DATA_DIR,
                                    f"ghcn_tmax_ct_ri_ma_{YEARS[0]}_{YEARS[-1]}.csv"),
                       dtype=str)

# quality control, per the GHCN-Daily readme: a blank QFLAG means it passed
_obs = raw_year.copy()
_at = _obs["TMAX_ATTRIBUTES"].fillna("").str.split(",")
_obs["qflag"] = _at.str[1].fillna("")
_obs["rawv"] = pd.to_numeric(_obs["TMAX"], errors="coerce")
_pass = _obs["rawv"].notna() & (_obs["rawv"] != -9999) & (_obs["qflag"] == "")
n_flagged = int((_obs["rawv"].notna() & (_obs["rawv"] != -9999) & ~_pass).sum())
_obs = _obs.loc[_pass].copy()
_obs["tmax_c"] = _obs["rawv"] / 10.0                 # tenths of degC -> degC

all_days = pd.date_range(f"{YEARS[0]}-01-01", f"{YEARS[-1]}-12-31").strftime("%Y-%m-%d")
Ywide = (_obs.pivot_table(index="STATION", columns="DATE", values="tmax_c", aggfunc="first")
             .reindex(columns=all_days))
coverage = Ywide.notna().mean(axis=1)
Ywide = Ywide.loc[sorted(coverage.index[coverage >= COVERAGE_RULE])]

meta = meta0.set_index("station").reindex(Ywide.index).rename_axis("station").reset_index()
station_ids = Ywide.index.tolist()
N = len(station_ids)
dates = pd.to_datetime(Ywide.columns)
Y = Ywide.to_numpy(float)                            # (N, 1096) degC, NaN where missing
observed = ~np.isnan(Y)
complete_day = observed.all(axis=0)

# ----------------------------------------------------------------- geometry
_to_metric = Transformer.from_crs("EPSG:4326", CRS_PROJECTED, always_xy=True)
_e, _n = _to_metric.transform(meta["lon"].to_numpy(), meta["lat"].to_numpy())
P = np.column_stack([_e, _n])                        # station positions, metres
PK = P / 1000.0                                      # ... in km, for plotting
elev = meta["elev_m"].to_numpy()

ei = gl.EdgeIndex(N)
D2_edge = ei.pair_distance(P @ P.T)                  # squared distance per edge, m^2
med_d = float(np.sqrt(np.median(D2_edge)))


def _load_state_rings():
    """Shoreline-clipped CT/MA/RI outlines, in the same projected km coordinates."""
    base = "cb_2023_us_state_500k"
    zf = zipfile.ZipFile(os.path.join(DATA_DIR, base + ".zip"))
    sf = shapefile.Reader(shp=io.BytesIO(zf.read(base + ".shp")),
                          dbf=io.BytesIO(zf.read(base + ".dbf")),
                          shx=io.BytesIO(zf.read(base + ".shx")))
    fields = [f[0] for f in sf.fields[1:]]
    rings = []
    for rec, shp in zip(sf.records(), sf.shapes()):
        if dict(zip(fields, rec)).get("STATEFP") not in {"09", "25", "44"}:
            continue
        pts = np.asarray(shp.points, float)
        bounds = list(shp.parts) + [len(pts)]
        for a_, b_ in zip(bounds[:-1], bounds[1:]):
            seg = pts[a_:b_]
            x_, y_ = _to_metric.transform(seg[:, 0], seg[:, 1])
            rings.append(np.column_stack([x_, y_]) / 1000.0)
    return rings


STATE_RINGS = _load_state_rings()


def draw_states(ax, color="0.45", lw=0.6, zorder=0, alpha=0.9):
    """Draw the CT / MA / RI shoreline. Call before plotting stations."""
    for ring in STATE_RINGS:
        ax.plot(ring[:, 0], ring[:, 1], color=color, lw=lw, zorder=zorder,
                alpha=alpha, solid_joinstyle="round")


# ------------------------------------------------- signal, split, matrices
def daily_center(Ymat, mask):
    """Subtract, per day, the mean over the stations visible that day."""
    Z = np.array(Ymat, float)
    lvl = np.full(Ymat.shape[1], np.nan)
    for t in range(Ymat.shape[1]):
        o = mask[:, t]
        if o.any():
            lvl[t] = Ymat[o, t].mean()
            Z[:, t] = Ymat[:, t] - lvl[t]
    return Z, lvl


Zfull, day_level = daily_center(Y, observed)

# season-balanced blocked split: 6 train / gap / 3 val / gap / 3 test / gap
_CYCLE = [("train", 6), ("gap", 1), ("val", 3), ("gap", 1), ("test", 3), ("gap", 1)]
labels = np.empty(len(all_days), dtype=object)
_pos = 0
while _pos < len(all_days):
    for _name, _len in _CYCLE:
        _end = min(_pos + _len, len(all_days))
        labels[_pos:_end] = _name
        _pos = _end
        if _pos >= len(all_days):
            break

train_days = np.where(labels == "train")[0]
val_days = np.where((labels == "val") & complete_day)[0]
test_days = np.where((labels == "test") & complete_day)[0]

_Ztr_raw = Zfull[:, train_days]
_tr_mask = observed[:, train_days]
station_bias = np.array([_Ztr_raw[i, _tr_mask[i]].mean() if _tr_mask[i].any() else 0.0
                         for i in range(N)])
Ztrain = np.where(_tr_mask, np.nan_to_num(_Ztr_raw), station_bias[:, None])
Zval = Zfull[:, val_days]
Ztest = Zfull[:, test_days]

DATA_TAG = hashlib.sha1(np.ascontiguousarray(Ztrain).tobytes()).hexdigest()[:10]


def L_of(w):
    return ei.L(np.asarray(w))


def trace_normalised(w):
    """Rescale so tr(L) = N, which is what makes energies comparable across graphs."""
    return gl.rescale_trace(np.maximum(np.asarray(w, float), 0.0), N)


# ------------------------------------------------------- the reconstruction
def make_masks(day_idx, n_rep, frac, seed):
    """Identical hidden-station sets for every method."""
    r = np.random.default_rng(seed)
    n_hide = int(round(frac * N))
    return {t: [r.choice(N, n_hide, replace=False) for _ in range(n_rep)] for t in day_idx}


val_masks = make_masks(val_days, MASK_REPEATS, MASK_FRACTION, seed=SEED)
test_masks = make_masks(test_days, MASK_REPEATS, MASK_FRACTION, seed=SEED + 1000)
N_HIDDEN = int(round(MASK_FRACTION * N))


def reconstruct_day(L, y, hidden, gamma):
    """Tikhonov interpolation on the graph; level estimated from visible stations only.

        min_x  ||(x - y)|_visible||^2 + gamma * x' L x
    """
    obs_idx = np.setdiff1d(np.arange(N), hidden)
    lvl = y[obs_idx].mean()
    z = y - lvl
    Io = np.zeros(N)
    Io[obs_idx] = 1.0
    A = np.diag(Io) + gamma * L
    return np.linalg.solve(A, Io * z) + lvl


def eval_graph(w, day_idx, masks, gammas=GAMMA_GRID):
    """RMSE over hidden stations, degC, for each gamma. Returns (best_gamma, rmse, all)."""
    L = L_of(trace_normalised(w))
    out = {}
    for g in gammas:
        errs = []
        for t in day_idx:
            y = Y[:, t]
            for hid in masks[t]:
                errs.append(reconstruct_day(L, y, hid, g)[hid] - y[hid])
        out[g] = float(np.sqrt(np.mean(np.concatenate(errs) ** 2)))
    best = min(out, key=out.get)
    return best, out[best], out


# ------------------------------------------------------------- baselines
_b_elev = np.column_stack([np.ones(N), elev, elev ** 2])
_coef_elev, *_ = np.linalg.lstsq(_b_elev, Ztrain.mean(axis=1), rcond=None)
elev_pred = _b_elev @ _coef_elev

pca_mean = Ztrain.mean(axis=1, keepdims=True)
Upca, Spca, _ = np.linalg.svd(Ztrain - pca_mean, full_matrices=False)
pca_var = Spca ** 2 / np.sum(Spca ** 2)


def predict_baseline(kind, y, hidden, n_comp=None):
    obs_idx = np.setdiff1d(np.arange(N), hidden)
    lvl = y[obs_idx].mean()
    z = y - lvl
    if kind == "mean":
        zh = np.zeros(N)
    elif kind == "elev":
        zh = elev_pred.copy()
    elif kind == "pca":
        B = Upca[:, :n_comp]
        c, *_ = np.linalg.lstsq(B[obs_idx], (z - pca_mean.ravel())[obs_idx], rcond=None)
        zh = pca_mean.ravel() + B @ c
    else:
        raise ValueError(kind)
    return zh + lvl


def eval_baseline(kind, day_idx, masks, n_comp=None):
    errs = []
    for t in day_idx:
        y = Y[:, t]
        for hid in masks[t]:
            errs.append(predict_baseline(kind, y, hid, n_comp)[hid] - y[hid])
    return float(np.sqrt(np.mean(np.concatenate(errs) ** 2)))


# ------------------------------------------------------- the constructions
def _fit_cached(key, fn, *args, **kwargs):
    """Reuse Lesson 4's cached solver output when the training matrix is identical."""
    path = os.path.join(CACHE_DIR, f"{key}__{DATA_TAG}.npz")
    if os.path.exists(path):
        d = np.load(path, allow_pickle=True)
        return {k: (d[k].item() if d[k].shape == () else d[k]) for k in d.files}
    out = fn(*args, **kwargs)
    os.makedirs(CACHE_DIR, exist_ok=True)
    np.savez(path, **{k: v for k, v in out.items() if v is not None})
    return out


def build_geographic():
    """Gaussian kernel on physical distance, truncated to k nearest neighbours."""
    cand = {}
    for mult in SIGMA_MULT_GRID:
        w = gl.gaussian_weights(D2_edge, (mult * med_d) ** 2)
        for k in KNN_GRID:
            cand[f"sigma={mult}x median, k={k}"] = gl.knn_sparsify(w, ei, k)
    return cand


def build_kalofolias():
    """Kalofolias (AISTATS 2016): min_w 2 z'w - a*sum log(deg) + b*||w||^2, w >= 0."""
    Zd = ei.pair_distance(Ztrain @ Ztrain.T)        # pairwise history distance per edge
    Zk = Zd / Zd.mean()                             # scale-normalised so (a, b) transfer
    cand = {}
    for a, b in KALO_GRID:
        r = _fit_cached(f"kalo_a{a}_b{b}", gl.kalofolias, Zk, ei, alpha=a, beta=b)
        cand[f"alpha={a}, beta={b}"] = np.asarray(r["w"])
    return cand


def select_on_validation(cand):
    """Pick the (setting, gamma) with the lowest validation RMSE. Never sees test days."""
    rows = []
    for label, w in cand.items():
        g, rmse, _ = eval_graph(w, val_days, val_masks)
        rows.append(dict(label=label, w=w, gamma=g, val=rmse))
    rows.sort(key=lambda r: r["val"])
    return rows[0], rows


def per_day_rmse(day_idx, masks, w=None, gamma=None, kind=None, n_comp=None):
    """One RMSE per day, so two methods can be compared as a paired sample."""
    L = None if w is None else L_of(trace_normalised(w))
    out = []
    for t in day_idx:
        y = Y[:, t]
        e = []
        for hid in masks[t]:
            pred = (reconstruct_day(L, y, hid, gamma) if L is not None
                    else predict_baseline(kind, y, hid, n_comp))
            e.append(pred[hid] - y[hid])
        out.append(np.sqrt(np.mean(np.concatenate(e) ** 2)))
    return np.array(out)


def paired(a, b):
    """Mean paired difference a - b, its standard error, and the ratio."""
    d = np.asarray(a) - np.asarray(b)
    se = d.std(ddof=1) / np.sqrt(len(d))
    return float(d.mean()), float(se), float(d.mean() / se)


def sample_size_curve(sizes, reps=5, alpha=2.0, beta=0.1, gamma=0.1, pca_k=8, seed=0):
    """Test RMSE against the number of training days, for the learned graph and for PCA.

    Both methods keep the hyperparameters chosen on the full training set, so neither
    is re-tuned as the sample shrinks. Random subsets of training days, `reps` draws
    per size. Returns mean and standard deviation across draws.
    """
    rng = np.random.default_rng(seed)
    saveU, saveM = Upca, pca_mean
    out = {"sizes": list(sizes), "graph": [], "graph_sd": [], "pca": [], "pca_sd": []}
    try:
        for n_days in sizes:
            rk, rp = [], []
            for _ in range(reps if n_days < Ztrain.shape[1] else 1):
                cols = rng.choice(Ztrain.shape[1], n_days, replace=False)
                Zs = Ztrain[:, cols]

                zd = ei.pair_distance(Zs @ Zs.T)
                w = gl.kalofolias(zd / zd.mean(), ei, alpha=alpha, beta=beta)["w"]
                rk.append(eval_graph(w, test_days, test_masks, [gamma])[1])

                mu = Zs.mean(axis=1, keepdims=True)
                U, _, _ = np.linalg.svd(Zs - mu, full_matrices=False)
                globals()["Upca"], globals()["pca_mean"] = U, mu
                rp.append(eval_baseline("pca", test_days, test_masks,
                                        min(pca_k, U.shape[1])))
            out["graph"].append(float(np.mean(rk)))
            out["graph_sd"].append(float(np.std(rk)))
            out["pca"].append(float(np.mean(rp)))
            out["pca_sd"].append(float(np.std(rp)))
    finally:
        globals()["Upca"], globals()["pca_mean"] = saveU, saveM
    return out
