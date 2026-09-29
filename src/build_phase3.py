"""Build the Phase 3 country-year energy-transition model from OWID data."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from paths import (
    ANALYTICS_DIR,
    OWID_ENERGY_FILE,
    PHASE3_REPORT_DIR,
    ensure_directories,
)


DEFAULT_START_YEAR = 2005
DEFAULT_END_YEAR = 2022
WORLD_ENTITY_CODE = "OWID_WRL"
ELECTRICITY_COLUMNS = [
    "population",
    "electricity_generation",
    "electricity_demand",
    "fossil_electricity",
    "renewables_electricity",
    "nuclear_electricity",
    "low_carbon_electricity",
    "coal_electricity",
    "gas_electricity",
    "oil_electricity",
    "hydro_electricity",
    "solar_electricity",
    "wind_electricity",
    "biofuel_electricity",
    "other_renewable_electricity",
    "fossil_share_elec",
    "renewables_share_elec",
    "nuclear_share_elec",
    "low_carbon_share_elec",
    "coal_share_elec",
    "gas_share_elec",
    "oil_share_elec",
    "hydro_share_elec",
    "solar_share_elec",
    "wind_share_elec",
    "biofuel_share_elec",
    "other_renewables_share_elec",
    "carbon_intensity_elec",
    "greenhouse_gas_emissions",
    "per_capita_electricity",
]
OUTPUT_RENAMES = {
    "country": "source_entity_name",
    "iso_code": "entity_code",
    "electricity_generation": "electricity_generation_twh",
    "electricity_demand": "electricity_demand_twh",
    "fossil_electricity": "fossil_electricity_twh",
    "renewables_electricity": "renewables_electricity_twh",
    "nuclear_electricity": "nuclear_electricity_twh",
    "low_carbon_electricity": "low_carbon_electricity_twh",
    "coal_electricity": "coal_electricity_twh",
    "gas_electricity": "gas_electricity_twh",
    "oil_electricity": "oil_electricity_twh",
    "hydro_electricity": "hydro_electricity_twh",
    "solar_electricity": "solar_electricity_twh",
    "wind_electricity": "wind_electricity_twh",
    "biofuel_electricity": "biofuel_electricity_twh",
    "other_renewable_electricity": "other_renewable_electricity_twh",
    "fossil_share_elec": "fossil_share_pct",
    "renewables_share_elec": "renewables_share_pct",
    "nuclear_share_elec": "nuclear_share_pct",
    "low_carbon_share_elec": "low_carbon_share_pct",
    "coal_share_elec": "coal_share_pct",
    "gas_share_elec": "gas_share_pct",
    "oil_share_elec": "oil_share_pct",
    "hydro_share_elec": "hydro_share_pct",
    "solar_share_elec": "solar_share_pct",
    "wind_share_elec": "wind_share_pct",
    "biofuel_share_elec": "biofuel_share_pct",
    "other_renewables_share_elec": "other_renewables_share_pct",
    "carbon_intensity_elec": "carbon_intensity_gco2_per_kwh",
    "greenhouse_gas_emissions": "greenhouse_gas_emissions_mtco2e",
    "per_capita_electricity": "electricity_generation_per_capita_kwh",
}


def safe_change(end_value: Any, start_value: Any) -> float | None:
    if pd.isna(start_value) or pd.isna(end_value):
        return None
    return float(end_value - start_value)


def build_entity_dimension(source: pd.DataFrame, country_dim: pd.DataFrame) -> pd.DataFrame:
    country_codes = set(country_dim["country_iso3"])
    entities = (
        source.loc[
            source["iso_code"].isin(country_codes) | source["iso_code"].eq(WORLD_ENTITY_CODE),
            ["iso_code", "country"],
        ]
        .drop_duplicates()
        .rename(columns={"iso_code": "entity_code", "country": "source_entity_name"})
    )
    entities = entities.merge(
        country_dim[
            [
                "country_iso3",
                "country_name",
                "region_name",
                "income_group_name",
            ]
        ],
        left_on="entity_code",
        right_on="country_iso3",
        how="left",
        validate="one_to_one",
    )
    entities["entity_type"] = "country"
    world = entities["entity_code"].eq(WORLD_ENTITY_CODE)
    entities.loc[world, "entity_type"] = "world"
    entities["entity_name"] = entities["country_name"].fillna(entities["source_entity_name"])
    entities.loc[world, "region_name"] = "World"
    entities.loc[world, "income_group_name"] = "Not applicable"
    entities = entities[
        [
            "entity_code",
            "entity_name",
            "entity_type",
            "country_iso3",
            "source_entity_name",
            "region_name",
            "income_group_name",
        ]
    ].sort_values(["entity_type", "entity_name"])
    return entities.reset_index(drop=True)


def build_momentum(fact: pd.DataFrame, entities: pd.DataFrame) -> pd.DataFrame:
    countries = entities.loc[entities["entity_type"].eq("country"), "entity_code"]
    subset = fact[
        fact["entity_code"].isin(countries)
        & fact["year"].isin([DEFAULT_START_YEAR, DEFAULT_END_YEAR])
    ]
    start = subset[subset["year"].eq(DEFAULT_START_YEAR)].set_index("entity_code")
    end = subset[subset["year"].eq(DEFAULT_END_YEAR)].set_index("entity_code")
    rows: list[dict[str, Any]] = []
    metrics = [
        "renewables_share_pct",
        "fossil_share_pct",
        "nuclear_share_pct",
        "low_carbon_share_pct",
        "carbon_intensity_gco2_per_kwh",
        "electricity_generation_twh",
    ]
    for entity_code in countries:
        entity = entities.loc[entities["entity_code"].eq(entity_code)].iloc[0]
        row: dict[str, Any] = {
            "entity_code": entity_code,
            "country_name": entity["entity_name"],
            "region_name": entity["region_name"],
            "start_year": DEFAULT_START_YEAR,
            "end_year": DEFAULT_END_YEAR,
            "period_years": DEFAULT_END_YEAR - DEFAULT_START_YEAR,
        }
        start_row = start.loc[entity_code] if entity_code in start.index else None
        end_row = end.loc[entity_code] if entity_code in end.index else None
        for metric in metrics:
            start_value = start_row[metric] if start_row is not None else None
            end_value = end_row[metric] if end_row is not None else None
            row[f"{metric}_start"] = start_value
            row[f"{metric}_end"] = end_value
            row[f"{metric}_change"] = safe_change(end_value, start_value)
        renewable_change = row["renewables_share_pct_change"]
        row["renewable_transition_momentum_pp_per_year"] = (
            renewable_change / row["period_years"]
            if renewable_change is not None
            else None
        )
        row["has_comparable_endpoints"] = renewable_change is not None
        rows.append(row)
    momentum = pd.DataFrame(rows)
    comparable = momentum["has_comparable_endpoints"]
    momentum["renewable_momentum_rank"] = pd.Series(pd.NA, index=momentum.index, dtype="Int64")
    momentum.loc[comparable, "renewable_momentum_rank"] = (
        momentum.loc[comparable, "renewable_transition_momentum_pp_per_year"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )
    return momentum


def write_insights(fact: pd.DataFrame, momentum: pd.DataFrame) -> None:
    world = fact[fact["entity_code"].eq(WORLD_ENTITY_CODE)].set_index("year")
    world_start = world.loc[DEFAULT_START_YEAR]
    world_end = world.loc[DEFAULT_END_YEAR]
    comparable = momentum[momentum["has_comparable_endpoints"]]
    leaders = comparable.nlargest(5, "renewable_transition_momentum_pp_per_year")

    lines = [
        "# Insight Awal Tren Transisi — Fase 3",
        "",
        f"Periode ranking yang dapat dibandingkan: **{DEFAULT_START_YEAR}–{DEFAULT_END_YEAR}**. Tahun 2023–2025 tetap tersedia untuk eksplorasi, tetapi tidak dipakai sebagai endpoint ranking default karena coverage lintas negara menurun.",
        "",
        "## Dunia",
        "",
        f"Renewable electricity share dunia berubah dari {world_start['renewables_share_pct']:.2f}% pada {DEFAULT_START_YEAR} menjadi {world_end['renewables_share_pct']:.2f}% pada {DEFAULT_END_YEAR}, atau {world_end['renewables_share_pct'] - world_start['renewables_share_pct']:+.2f} percentage points.",
        f"Fossil electricity share berubah {world_end['fossil_share_pct'] - world_start['fossil_share_pct']:+.2f} percentage points pada periode yang sama.",
        "",
        "## Renewable momentum tertinggi",
        "",
        "| Negara | Perubahan renewable share (pp) | Momentum (pp/tahun) |",
        "|---|---:|---:|",
    ]
    for _, row in leaders.iterrows():
        lines.append(
            f"| {row['country_name']} | {row['renewables_share_pct_change']:+.2f} | {row['renewable_transition_momentum_pp_per_year']:+.3f} |"
        )
    lines.extend(
        [
            "",
            "## Batasan",
            "",
            "OWID menggabungkan beberapa sumber dan memperbarui data secara berkala. Perubahan di sini mengukur bauran produksi listrik country-year, bukan perubahan kapasitas WRI dan bukan dampak kausal kebijakan tertentu.",
        ]
    )
    (PHASE3_REPORT_DIR / "initial_transition_insights.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def build_phase3() -> None:
    ensure_directories()
    if not OWID_ENERGY_FILE.exists():
        raise FileNotFoundError("OWID Energy Data belum tersedia. Jalankan download_owid.py.")

    source = pd.read_csv(OWID_ENERGY_FILE, low_memory=False)
    required = {"country", "year", "iso_code", *ELECTRICITY_COLUMNS}
    missing = required.difference(source.columns)
    if missing:
        raise ValueError(f"Kolom OWID wajib tidak ditemukan: {sorted(missing)}")

    # OWID represents Kosovo with a missing ISO code; use the project's explicit XKX mapping.
    source.loc[source["country"].eq("Kosovo"), "iso_code"] = "XKX"
    source.loc[source["country"].eq("World"), "iso_code"] = WORLD_ENTITY_CODE
    country_dim = pd.read_csv(ANALYTICS_DIR / "dim_country.csv")
    entities = build_entity_dimension(source, country_dim)
    entities.to_csv(ANALYTICS_DIR / "dim_energy_entity.csv", index=False)

    selected_codes = set(entities["entity_code"])
    fact = source.loc[
        source["iso_code"].isin(selected_codes),
        ["country", "year", "iso_code", *ELECTRICITY_COLUMNS],
    ].copy()
    fact = fact.rename(columns=OUTPUT_RENAMES)
    fact = fact.merge(
        entities[["entity_code", "entity_name", "entity_type"]],
        on="entity_code",
        how="left",
        validate="many_to_one",
    )
    fact["data_type"] = "compiled"
    fact["population"] = pd.to_numeric(fact["population"], errors="coerce").astype("Int64")
    key_mix = [
        "renewables_share_pct",
        "fossil_share_pct",
        "nuclear_share_pct",
        "low_carbon_share_pct",
    ]
    fact["has_complete_key_mix"] = fact[key_mix].notna().all(axis=1)
    fact = fact[
        [
            "entity_code",
            "year",
            "data_type",
            "has_complete_key_mix",
            *[OUTPUT_RENAMES.get(column, column) for column in ELECTRICITY_COLUMNS],
        ]
    ].sort_values(["entity_code", "year"])
    fact.to_csv(ANALYTICS_DIR / "fact_country_energy_year.csv", index=False)

    coverage = (
        fact.groupby("year")
        .agg(
            entity_rows=("entity_code", "size"),
            countries_with_generation=("electricity_generation_twh", "count"),
            countries_with_renewable_share=("renewables_share_pct", "count"),
            countries_with_fossil_share=("fossil_share_pct", "count"),
            countries_with_low_carbon_share=("low_carbon_share_pct", "count"),
            countries_with_carbon_intensity=("carbon_intensity_gco2_per_kwh", "count"),
            entities_with_complete_key_mix=("has_complete_key_mix", "sum"),
        )
        .reset_index()
    )
    coverage.to_csv(ANALYTICS_DIR / "mart_energy_year_coverage.csv", index=False)

    momentum = build_momentum(fact, entities)
    momentum.to_csv(ANALYTICS_DIR / "mart_transition_momentum.csv", index=False)

    latest = (
        fact[fact["renewables_share_pct"].notna()]
        .sort_values(["entity_code", "year"])
        .groupby("entity_code", as_index=False)
        .tail(1)
    )
    latest.to_csv(ANALYTICS_DIR / "mart_transition_latest.csv", index=False)

    config = {
        "source": "Our World in Data Energy Data",
        "default_start_year": DEFAULT_START_YEAR,
        "default_end_year": DEFAULT_END_YEAR,
        "latest_source_year": int(fact["year"].max()),
        "world_entity_code": WORLD_ENTITY_CODE,
        "data_type": "compiled",
        "ranking_rule": "Both period endpoints must be non-null.",
    }
    (ANALYTICS_DIR / "phase3_model_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_insights(fact, momentum)
    print(
        f"Model Fase 3 selesai: {len(fact):,} country-year rows, "
        f"{len(entities)} entities, {fact['year'].min()}-{fact['year'].max()}."
    )


if __name__ == "__main__":
    build_phase3()
