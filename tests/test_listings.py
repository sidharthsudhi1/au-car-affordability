import pandas as pd

from carafford import listings


def raw_row(**overrides):
    row = {
        "Brand": "Toyota", "Year": "2019", "Model": "Corolla", "Car/Suv": "Hatchback",
        "Title": "2019 Toyota Corolla Ascent Sport", "UsedOrNew": "USED", "Transmission": "Automatic",
        "Engine": "4 cyl, 2 L", "DriveType": "Front", "FuelType": "Unleaded",
        "FuelConsumption": "6 L / 100 km", "Kilometres": "45000", "ColourExtInt": "White / -",
        "Location": "Blacktown, NSW", "CylindersinEngine": "4 cyl", "BodyType": "Hatchback",
        "Doors": " 5 Doors", "Seats": " 5 Seats", "Price": "24990",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_parse_numeric_fields():
    out = listings.parse(raw_row())
    r = out.iloc[0]
    assert r["engine_litres"] == 2.0
    assert r["cylinders"] == 4
    assert r["fuel_l_100km"] == 6.0
    assert r["doors"] == 5 and r["seats"] == 5
    assert r["state"] == "NSW"
    assert r["age"] == 4


def test_split_brand_recovered_from_title():
    out = listings.parse(raw_row(Brand="Land", Model="Rover", Title="2017 Land Rover Discovery Sport HSE"))
    assert out.iloc[0]["brand"] == "Land Rover"
    assert out.iloc[0]["model"] == "Discovery"


def test_seats_shifted_into_doors_column():
    out = listings.parse(raw_row(Doors=" 7 Seats", Seats=None))
    assert pd.isna(out.iloc[0]["doors"])
    assert out.iloc[0]["seats"] == 7


def test_placeholders_become_missing():
    out = listings.parse(raw_row(Kilometres="-", Price="POA", Transmission="-"))
    r = out.iloc[0]
    assert pd.isna(r["km"]) and pd.isna(r["price"]) and pd.isna(r["transmission"])


def test_clean_drops_new_car_with_high_km():
    raw = pd.concat([raw_row(), raw_row(UsedOrNew="NEW", Kilometres="60000", Title="x")])
    out, log = listings.clean(raw)
    assert len(out) == 1
    assert log["dropped"].sum() == 1
