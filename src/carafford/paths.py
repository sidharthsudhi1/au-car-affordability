from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
CLEAN = ROOT / "data" / "clean"
FIGURES = ROOT / "figures"

LISTINGS_RAW = RAW / "australian_vehicle_prices.csv"
EARNINGS_RAW = RAW / "abs_employee_earnings_aug2024.csv"
CPI_RAW = RAW / "abs_cpi.csv"
AWE_RAW = RAW / "abs_awe.csv"

STATES = {
    "1": "NSW", "2": "VIC", "3": "QLD", "4": "SA",
    "5": "WA", "6": "TAS", "7": "NT", "8": "ACT", "AUS": "AUS", "50": "AUS",
}
STATE_NAMES = {
    "New South Wales": "NSW", "Victoria": "VIC", "Queensland": "QLD",
    "South Australia": "SA", "Western Australia": "WA", "Tasmania": "TAS",
    "Northern Territory": "NT", "Australian Capital Territory": "ACT", "Australia": "AUS",
}
