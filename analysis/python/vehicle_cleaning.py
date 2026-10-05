import re, sys, argparse
from pathlib import Path
import numpy as np, pandas as pd

RAW_DEFAULT = "AUSTRALIAN CAR PIRCE - AUSTRALIAN CAR PIRCE.csv.csv"
OUT_SIMPLE  = Path("vehicle_price_clean_v2.csv")
OUT_STATE   = Path("vehicle_price_clean_v2_state.csv")

YEAR_MIN, YEAR_MAX = 2014, 2023

CANON = ["SUV","Sedan","Hatchback","Wagon","Ute/Pickup","Commercial",
         "Convertible","Coupe","People Mover","MPV","Van"]

BODY_MAP = {
    r"\bsuv(s)?\b":"SUV", r"\bcrossover\b":"SUV",
    r"\bsedan(s)?\b":"Sedan", r"\bsaloon\b":"Sedan",
    r"\bhatch(back)?s?\b":"Hatchback",
    r"\b(wagon|estate)s?\b":"Wagon",
    r"\b(ute|pick[\s-]?up|pickup|dual[\s-]?cab|tray)s?\b":"Ute/Pickup",
    r"\b(light|heavy)\s*commercial\b":"Commercial", r"\bchassis\b":"Commercial",
    r"\bconvertible|cabrio(let)?|roadster\b":"Convertible",
    r"\bcoup[eé]\b":"Coupe", r"\bfastback\b":"Coupe",
    r"\b(people\s*mover|mpv)\b":"People Mover", r"\bvan(s)?\b":"Van",
}

STATE_MAP = {
    "nsw":"NSW","new south wales":"NSW","vic":"VIC","victoria":"VIC",
    "qld":"QLD","queensland":"QLD","wa":"WA","western australia":"WA",
    "sa":"SA","south australia":"SA","tas":"TAS","tasmania":"TAS",
    "nt":"NT","northern territory":"NT","act":"ACT",
    "australian capital territory":"ACT",
}

def find_col(df, patterns, default=None):
    cols = {c.lower(): c for c in df.columns}
    for pat in ([patterns] if isinstance(patterns,str) else patterns):
        rx = re.compile(pat, re.I)
        for lc, orig in cols.items():
            if rx.search(lc): return orig
    return default

def clean_price(x):
    if pd.isna(x): return np.nan
    s = re.sub(r"[^\d.]", "", str(x))
    return float(s) if s else np.nan

def normalise_bodytype(s):
    if pd.isna(s): return np.nan
    t = str(s).lower().strip()
    for rx, canon in BODY_MAP.items():
        if re.search(rx, t): return canon
    if t=="mpv": return "People Mover"
    if t=="ute": return "Ute/Pickup"
    return t.title()

def normalise_state(s):
    if pd.isna(s): return np.nan
    t = str(s).strip().lower()
    # allow "Sydney, NSW" -> NSW
    m = re.search(r"\b(act|nsw|nt|qld|sa|tas|vic|wa)\b", t)
    if m: return m.group(1).upper()
    return STATE_MAP.get(t, t.upper())

def coerce_year(s):
    if pd.isna(s): return np.nan
    m = re.search(r"(20\d{2})", str(s))
    return int(m.group(1)) if m else np.nan

def clip_outliers(df, group_cols, val_col="price", lo=0.01, hi=0.99):
    def _clip(g):
        ql, qh = g[val_col].quantile([lo, hi]).values
        return g[(g[val_col] >= ql) & (g[val_col] <= qh)]
    return df.groupby(group_cols, group_keys=False).apply(_clip)

# -------- args --------
ap = argparse.ArgumentParser()
ap.add_argument("--raw", default=RAW_DEFAULT)
ap.add_argument("--year",  help="explicit year column name")
ap.add_argument("--price", help="explicit price column name")
ap.add_argument("--body",  help="explicit body/segment column name")
ap.add_argument("--state", help="explicit state/region/location column name (optional)")
args = ap.parse_args()

raw_path = Path(args.raw)
df = pd.read_csv(raw_path, low_memory=False)

# auto-detect (now catches Price($))
col_year  = args.year  or find_col(df, [r"^year$", r"\bmodel[_\s-]?year\b", r"\bbuild[_\s-]?year\b"])
col_price = args.price or find_col(df, [r"^price(\W*\$?\)?)?$", r"list[_\s-]?price", r"advertised[_\s-]?price", r"driveaway", r"retail"])
col_body  = args.body  or find_col(df, [r"body", r"body[_\s-]?type", r"\bsegment\b", r"car\s*type"])
col_state = args.state or find_col(df, [r"^state$", r"location", r"region", r"city"])

missing = [name for name, c in [("year",col_year),("price",col_price),("body",col_body)] if c is None]
if missing:
    print("ERROR: Could not locate columns:", ", ".join(missing))
    print("Columns found:", list(df.columns)); sys.exit(1)

keep_cols = [c for c in [col_year, col_body, col_price, col_state] if c is not None]
df = df[keep_cols].copy()

df["year"]         = df[col_year].apply(coerce_year)
df["price"]        = df[col_price].apply(clean_price)
df["bodytype_std"] = df[col_body].apply(normalise_bodytype)
if col_state: df["state"] = df[col_state].apply(normalise_state)

df = df[(df["year"].between(2014,2023)) & (df["price"]>0) & (~df["bodytype_std"].isna())]

df = clip_outliers(df, ["year","bodytype_std"], "price", 0.01, 0.99)

simple = df[["year","bodytype_std","price"]].sort_values(["year","bodytype_std"]).reset_index(drop=True)
simple.to_csv(OUT_SIMPLE, index=False)
print(f"Saved: {OUT_SIMPLE.resolve()}  rows={len(simple):,}")

if "state" in df.columns and df["state"].notna().any():
    with_state = df[["year","bodytype_std","state","price"]].dropna(subset=["state"]) \
                 .sort_values(["year","state","bodytype_std"]).reset_index(drop=True)
    with_state.to_csv(OUT_STATE, index=False)
    print(f"Saved: {OUT_STATE.resolve()}  rows={len(with_state):,}")
else:
    print("No usable state column → skipped writing state-level file.")