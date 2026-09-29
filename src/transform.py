"""Clean the WRI snapshot and build Phase 1 analytical tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from paths import (
    COUNTRY_OVERRIDES_FILE,
    DIM_COUNTRY_FILE,
    DIM_FUEL_FILE,
    FACT_POWER_PLANT_FILE,
    FUEL_MAPPING_FILE,
    RAW_DATA_FILE,
    ensure_directories,
)


REQUIRED_COLUMNS = {
    "country",
    "country_long",
    "name",
    "gppd_idnr",
    "capacity_mw",
    "latitude",
    "longitude",
    "primary_fuel",
    "commissioning_year",
    "owner",
    "source",
    "url",
    "year_of_capacity_data",
}
NUMERIC_COLUMNS = [
    "capacity_mw",
    "latitude",
    "longitude",
    "commissioning_year",
    "year_of_capacity_data",
    "generation_gwh_2013",
    "generation_gwh_2014",
    "generation_gwh_2015",
    "generation_gwh_2016",
    "generation_gwh_2017",
    "generation_gwh_2018",
    "generation_gwh_2019",
    "estimated_generation_gwh_2013",
    "estimated_generation_gwh_2014",
    "estimated_generation_gwh_2015",
    "estimated_generation_gwh_2016",
    "estimated_generation_gwh_2017",
]


def clean_strings(data: pd.DataFrame) -> pd.DataFrame:
    for column in data.select_dtypes(include=["object", "string"]).columns:
        data[column] = data[column].astype("string").str.strip().replace("", pd.NA)
    return data


def build_country_dimension(
    data: pd.DataFrame, overrides_path: Path = COUNTRY_OVERRIDES_FILE
) -> pd.DataFrame:
    countries = (
        data[["country", "country_long"]]
        .drop_duplicates()
        .rename(columns={"country": "source_country_code", "country_long": "source_country_name"})
    )
    if countries["source_country_code"].duplicated().any():
        raise ValueError("Satu source country code memiliki lebih dari satu nama negara.")

    countries["country_iso3"] = countries["source_country_code"]
    countries["country_name"] = countries["source_country_name"]
    countries["mapping_method"] = "source_iso3"
    countries["mapping_note"] = pd.NA

    overrides = pd.read_csv(overrides_path, dtype="string").set_index("source_country_code")
    for source_code, override in overrides.iterrows():
        match = countries["source_country_code"].eq(source_code)
        if not match.any():
            raise ValueError(f"Country override tidak ditemukan pada sumber: {source_code}")
        countries.loc[match, "country_iso3"] = override["country_iso3"]
        countries.loc[match, "country_name"] = override["country_name"]
        countries.loc[match, "mapping_method"] = "manual_override"
        countries.loc[match, "mapping_note"] = override["mapping_note"]

    countries["is_iso3_format"] = countries["country_iso3"].str.fullmatch(r"[A-Z]{3}")
    countries = countries[
        [
            "country_iso3",
            "country_name",
            "source_country_code",
            "source_country_name",
            "mapping_method",
            "mapping_note",
            "is_iso3_format",
        ]
    ].sort_values("country_iso3")
    return countries.reset_index(drop=True)


def transform_data(
    input_path: Path = RAW_DATA_FILE,
    output_path: Path = FACT_POWER_PLANT_FILE,
) -> pd.DataFrame:
    ensure_directories()
    data = pd.read_csv(input_path, low_memory=False)
    missing_columns = REQUIRED_COLUMNS.difference(data.columns)
    if missing_columns:
        raise ValueError(f"Kolom wajib tidak ditemukan: {sorted(missing_columns)}")

    data = clean_strings(data)
    for column in NUMERIC_COLUMNS:
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    countries = build_country_dimension(data)
    countries.to_csv(DIM_COUNTRY_FILE, index=False)

    fuel_mapping = pd.read_csv(FUEL_MAPPING_FILE)
    if fuel_mapping["primary_fuel"].duplicated().any():
        raise ValueError("Fuel mapping mengandung primary_fuel duplikat.")
    fuel_mapping.to_csv(DIM_FUEL_FILE, index=False)

    cleaned = data.rename(
        columns={
            "country": "source_country_code",
            "country_long": "source_country_name",
            "name": "plant_name",
            "gppd_idnr": "plant_id",
        }
    )
    cleaned = cleaned.merge(
        countries[["source_country_code", "country_iso3", "country_name"]],
        on="source_country_code",
        how="left",
        validate="many_to_one",
    )
    cleaned = cleaned.merge(fuel_mapping, on="primary_fuel", how="left", validate="many_to_one")

    commissioning_raw = cleaned["commissioning_year"].copy()
    cleaned["commissioning_year_is_fractional"] = (
        commissioning_raw.notna() & commissioning_raw.mod(1).ne(0)
    )
    cleaned["year_of_capacity_data"] = cleaned["year_of_capacity_data"].astype("Int64")

    cleaned["dq_capacity_issue"] = pd.Series("ok", index=cleaned.index, dtype="string")
    cleaned.loc[cleaned["capacity_mw"].isna(), "dq_capacity_issue"] = "missing"
    cleaned.loc[cleaned["capacity_mw"].le(0), "dq_capacity_issue"] = "non_positive"

    cleaned["dq_coordinate_issue"] = pd.Series("ok", index=cleaned.index, dtype="string")
    coordinate_missing = cleaned["latitude"].isna() | cleaned["longitude"].isna()
    coordinate_invalid = (
        (~cleaned["latitude"].between(-90, 90) & cleaned["latitude"].notna())
        | (~cleaned["longitude"].between(-180, 180) & cleaned["longitude"].notna())
    )
    cleaned.loc[coordinate_missing, "dq_coordinate_issue"] = "missing"
    cleaned.loc[coordinate_invalid, "dq_coordinate_issue"] = "out_of_range"

    cleaned["dq_commissioning_issue"] = pd.Series("ok", index=cleaned.index, dtype="string")
    cleaned.loc[commissioning_raw.isna(), "dq_commissioning_issue"] = "missing"
    snapshot_range_issue = commissioning_raw.notna() & ~commissioning_raw.between(1800, 2020)
    cleaned.loc[snapshot_range_issue, "dq_commissioning_issue"] = "outside_snapshot_range"

    cleaned["dq_has_blocking_issue"] = (
        cleaned["plant_id"].isna()
        | cleaned["country_iso3"].isna()
        | cleaned["fuel_key"].isna()
        | cleaned["dq_capacity_issue"].ne("ok")
    )

    leading_columns = [
        "plant_id",
        "plant_name",
        "country_iso3",
        "country_name",
        "source_country_code",
        "source_country_name",
        "primary_fuel",
        "fuel_key",
        "fuel_group",
        "is_fossil",
        "is_renewable",
        "is_nuclear",
        "is_low_carbon",
        "capacity_mw",
        "latitude",
        "longitude",
        "commissioning_year",
        "commissioning_year_is_fractional",
        "dq_capacity_issue",
        "dq_coordinate_issue",
        "dq_commissioning_issue",
        "dq_has_blocking_issue",
    ]
    remaining_columns = [column for column in cleaned.columns if column not in leading_columns]
    cleaned = cleaned[leading_columns + remaining_columns]
    cleaned.to_csv(output_path, index=False)

    print(f"Transformasi selesai: {len(cleaned):,} baris -> {output_path}")
    return cleaned


if __name__ == "__main__":
    transform_data()
