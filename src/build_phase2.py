"""Build the Phase 2 asset-analysis model and dashboard-ready marts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from paths import (
    ANALYTICS_DIR,
    DIM_COUNTRY_FILE,
    DIM_FUEL_FILE,
    FACT_POWER_PLANT_FILE,
    PHASE2_REPORT_DIR,
    WORLD_BANK_COUNTRIES_FILE,
    WORLD_BANK_POPULATION_FILE,
    ensure_directories,
)


REFERENCE_YEAR = 2020
SHARE_RANKING_MIN_CAPACITY_MW = 1_000.0
AGE_BANDS = [
    {"age_band": "0-14 years", "age_band_sort": 1, "lower_bound": 0, "upper_bound": 15},
    {"age_band": "15-29 years", "age_band_sort": 2, "lower_bound": 15, "upper_bound": 30},
    {"age_band": "30-39 years", "age_band_sort": 3, "lower_bound": 30, "upper_bound": 40},
    {"age_band": "40+ years", "age_band_sort": 4, "lower_bound": 40, "upper_bound": None},
    {"age_band": "Unknown", "age_band_sort": 5, "lower_bound": None, "upper_bound": None},
]


def safe_pct(numerator: float, denominator: float) -> float | None:
    if denominator == 0 or pd.isna(denominator):
        return None
    return float(numerator / denominator * 100)


def capacity_weighted_mean(group: pd.DataFrame, value_column: str) -> float | None:
    known = group[value_column].notna() & group["capacity_mw"].notna()
    denominator = group.loc[known, "capacity_mw"].sum()
    if denominator == 0:
        return None
    numerator = (group.loc[known, value_column] * group.loc[known, "capacity_mw"]).sum()
    return float(numerator / denominator)


def load_world_bank_dimension() -> pd.DataFrame:
    countries_response = json.loads(WORLD_BANK_COUNTRIES_FILE.read_text(encoding="utf-8"))
    population_response = json.loads(WORLD_BANK_POPULATION_FILE.read_text(encoding="utf-8"))

    country_rows: list[dict[str, Any]] = []
    for item in countries_response[1]:
        if item["region"]["id"] == "NA":
            continue
        country_rows.append(
            {
                "country_iso3": item["id"],
                "world_bank_country_name": item["name"].strip(),
                "region_code": item["region"]["id"],
                "region_name": item["region"]["value"].strip(),
                "income_group_code": item["incomeLevel"]["id"],
                "income_group_name": item["incomeLevel"]["value"].strip(),
                "capital_city": item["capitalCity"].strip() or None,
            }
        )
    metadata = pd.DataFrame(country_rows).drop_duplicates("country_iso3")

    population_rows = [
        {
            "country_iso3": item["countryiso3code"],
            "population": item["value"],
            "population_year": int(item["date"]),
        }
        for item in population_response[1]
        if item["countryiso3code"] and item["value"] is not None
    ]
    population = pd.DataFrame(population_rows).drop_duplicates("country_iso3")
    return metadata.merge(population, on="country_iso3", how="left", validate="one_to_one")


def add_asset_derivations(fact: pd.DataFrame) -> pd.DataFrame:
    fact = fact.copy()
    commissioning = pd.to_numeric(fact["commissioning_year"], errors="coerce")
    valid_commissioning = commissioning.notna() & commissioning.between(1800, REFERENCE_YEAR)
    fact["plant_age_years"] = (REFERENCE_YEAR - commissioning).where(valid_commissioning)
    fact["commissioning_decade"] = (
        commissioning.where(valid_commissioning).floordiv(10).mul(10).astype("Int64")
    )

    age_band = pd.cut(
        fact["plant_age_years"],
        bins=[-0.000001, 15, 30, 40, float("inf")],
        labels=["0-14 years", "15-29 years", "30-39 years", "40+ years"],
        right=False,
    )
    fact["age_band"] = age_band.astype("string").fillna("Unknown")
    age_sort = {row["age_band"]: row["age_band_sort"] for row in AGE_BANDS}
    fact["age_band_sort"] = fact["age_band"].map(age_sort).astype("Int64")
    fact["is_fossil_over_30"] = (
        fact["is_fossil"].eq(1) & fact["plant_age_years"].gt(30)
    )
    fact["is_coal_under_15"] = (
        fact["primary_fuel"].eq("Coal") & fact["plant_age_years"].lt(15)
    )
    return fact


def summarize_assets(group: pd.DataFrame) -> dict[str, Any]:
    total_capacity = float(group["capacity_mw"].sum())
    fossil_capacity = float(group.loc[group["is_fossil"].eq(1), "capacity_mw"].sum())
    renewable_capacity = float(group.loc[group["is_renewable"].eq(1), "capacity_mw"].sum())
    nuclear_capacity = float(group.loc[group["is_nuclear"].eq(1), "capacity_mw"].sum())
    low_carbon_capacity = float(group.loc[group["is_low_carbon"].eq(1), "capacity_mw"].sum())
    other_capacity = total_capacity - fossil_capacity - renewable_capacity - nuclear_capacity
    coal_capacity = float(group.loc[group["primary_fuel"].eq("Coal"), "capacity_mw"].sum())
    gas_capacity = float(group.loc[group["primary_fuel"].eq("Gas"), "capacity_mw"].sum())

    known_age = group["plant_age_years"].notna()
    known_age_capacity = float(group.loc[known_age, "capacity_mw"].sum())
    fossil = group["is_fossil"].eq(1)
    fossil_known_age = fossil & known_age
    fossil_known_age_capacity = float(group.loc[fossil_known_age, "capacity_mw"].sum())
    fossil_over_30_capacity = float(group.loc[group["is_fossil_over_30"], "capacity_mw"].sum())
    coal_under_15_capacity = float(group.loc[group["is_coal_under_15"], "capacity_mw"].sum())

    fuel_capacity = group.groupby("primary_fuel", observed=True)["capacity_mw"].sum()
    fuel_shares = fuel_capacity / total_capacity if total_capacity else fuel_capacity * 0
    hhi = float((fuel_shares**2).sum()) if total_capacity else None
    dominant_fuel = fuel_capacity.idxmax() if not fuel_capacity.empty else None
    dominant_fuel_capacity = float(fuel_capacity.max()) if not fuel_capacity.empty else 0.0

    return {
        "total_plants": int(group["plant_id"].nunique()),
        "total_capacity_mw": total_capacity,
        "total_capacity_gw": total_capacity / 1_000,
        "fossil_capacity_mw": fossil_capacity,
        "renewable_capacity_mw": renewable_capacity,
        "nuclear_capacity_mw": nuclear_capacity,
        "low_carbon_capacity_mw": low_carbon_capacity,
        "other_capacity_mw": other_capacity,
        "coal_capacity_mw": coal_capacity,
        "gas_capacity_mw": gas_capacity,
        "fossil_share_pct": safe_pct(fossil_capacity, total_capacity),
        "renewable_share_pct": safe_pct(renewable_capacity, total_capacity),
        "nuclear_share_pct": safe_pct(nuclear_capacity, total_capacity),
        "low_carbon_share_pct": safe_pct(low_carbon_capacity, total_capacity),
        "other_share_pct": safe_pct(other_capacity, total_capacity),
        "coal_dependency_pct": safe_pct(coal_capacity, total_capacity),
        "average_plant_capacity_mw": float(group["capacity_mw"].mean()),
        "median_plant_capacity_mw": float(group["capacity_mw"].median()),
        "capacity_weighted_age_years": capacity_weighted_mean(group, "plant_age_years"),
        "known_age_capacity_mw": known_age_capacity,
        "age_coverage_by_capacity_pct": safe_pct(known_age_capacity, total_capacity),
        "unknown_commissioning_capacity_mw": total_capacity - known_age_capacity,
        "unknown_commissioning_capacity_share_pct": safe_pct(
            total_capacity - known_age_capacity, total_capacity
        ),
        "fossil_capacity_weighted_age_years": capacity_weighted_mean(
            group.loc[fossil], "plant_age_years"
        ),
        "fossil_age_coverage_by_capacity_pct": safe_pct(
            fossil_known_age_capacity, fossil_capacity
        ),
        "fossil_capacity_over_30_years_mw": fossil_over_30_capacity,
        "fossil_capacity_over_30_years_share_pct": safe_pct(
            fossil_over_30_capacity, fossil_capacity
        ),
        "coal_capacity_under_15_years_mw": coal_under_15_capacity,
        "coal_capacity_under_15_years_share_pct": safe_pct(
            coal_under_15_capacity, coal_capacity
        ),
        "fuel_concentration_hhi": hhi,
        "fuel_diversity_index": 1 - hhi if hhi is not None else None,
        "effective_fuel_count": 1 / hhi if hhi not in (None, 0) else None,
        "dominant_primary_fuel": dominant_fuel,
        "dominant_fuel_share_pct": safe_pct(dominant_fuel_capacity, total_capacity),
    }


def grouped_summary(data: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grouper: str | list[str] = keys[0] if len(keys) == 1 else keys
    for group_key, group in data.groupby(grouper, dropna=False, observed=True, sort=True):
        key_values = (group_key,) if len(keys) == 1 else group_key
        row = dict(zip(keys, key_values))
        row.update(summarize_assets(group))
        rows.append(row)
    return pd.DataFrame(rows)


def rank_eligible(frame: pd.DataFrame, metric: str, output_column: str) -> None:
    eligible = frame["eligible_for_share_ranking"]
    frame[output_column] = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    frame.loc[eligible, output_column] = (
        frame.loc[eligible, metric].rank(method="min", ascending=False).astype("Int64")
    )


def write_initial_insights(global_kpi: pd.DataFrame, countries: pd.DataFrame) -> None:
    global_row = global_kpi.iloc[0]
    top_capacity = countries.nlargest(5, "total_capacity_mw")
    eligible = countries[countries["eligible_for_share_ranking"]]
    top_renewable = eligible.nlargest(5, "renewable_share_pct")
    top_coal_dependency = eligible.nlargest(5, "coal_dependency_pct")
    old_fossil = countries.nlargest(5, "fossil_capacity_over_30_years_mw")
    young_coal = countries.nlargest(5, "coal_capacity_under_15_years_mw")

    def table(frame: pd.DataFrame, columns: list[str], labels: list[str]) -> list[str]:
        lines = ["| " + " | ".join(labels) + " |", "|" + "---|" * len(labels)]
        for _, row in frame.iterrows():
            values: list[str] = []
            for column in columns:
                value = row[column]
                if isinstance(value, float):
                    values.append(f"{value:,.2f}")
                else:
                    values.append(str(value))
            lines.append("| " + " | ".join(values) + " |")
        return lines

    lines = [
        "# Insight Awal Analisis Aset — Fase 2",
        "",
        f"Reference year umur aset: **{REFERENCE_YEAR}**. Ranking share default hanya memasukkan negara dengan kapasitas minimal **{SHARE_RANKING_MIN_CAPACITY_MW / 1000:.1f} GW**.",
        "",
        "## Struktur global",
        "",
        f"Dataset mencatat {int(global_row['total_plants']):,} pembangkit dengan kapasitas {global_row['total_capacity_gw']:,.1f} GW. Porsi kapasitas fosil adalah {global_row['fossil_share_pct']:.2f}%, renewable {global_row['renewable_share_pct']:.2f}%, dan low-carbon {global_row['low_carbon_share_pct']:.2f}%.",
        "",
        "## Negara dengan kapasitas terbesar",
        "",
        *table(top_capacity, ["country_name", "total_capacity_gw", "low_carbon_share_pct"], ["Negara", "Kapasitas (GW)", "Low-carbon share (%)"]),
        "",
        "## Renewable share tertinggi — negara eligible",
        "",
        *table(top_renewable, ["country_name", "total_capacity_gw", "renewable_share_pct"], ["Negara", "Kapasitas (GW)", "Renewable share (%)"]),
        "",
        "## Coal dependency tertinggi — negara eligible",
        "",
        *table(top_coal_dependency, ["country_name", "total_capacity_gw", "coal_dependency_pct"], ["Negara", "Kapasitas (GW)", "Coal dependency (%)"]),
        "",
        "## Kapasitas fosil berumur lebih dari 30 tahun terbesar",
        "",
        *table(old_fossil, ["country_name", "fossil_capacity_over_30_years_mw", "fossil_age_coverage_by_capacity_pct"], ["Negara", "Kapasitas (MW)", "Coverage umur fosil (%)"]),
        "",
        "## Kapasitas batu bara berumur kurang dari 15 tahun terbesar",
        "",
        *table(young_coal, ["country_name", "coal_capacity_under_15_years_mw", "fossil_age_coverage_by_capacity_pct"], ["Negara", "Kapasitas (MW)", "Coverage umur fosil (%)"]),
        "",
        "## Batasan",
        "",
        "Temuan di atas menggambarkan struktur kapasitas pada snapshot WRI, bukan produksi listrik, status operasi terkini, atau perubahan historis. Ranking umur harus dibaca bersama coverage commissioning year.",
    ]
    (PHASE2_REPORT_DIR / "initial_insights.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def build_phase2() -> None:
    ensure_directories()
    required_files = [
        FACT_POWER_PLANT_FILE,
        DIM_COUNTRY_FILE,
        DIM_FUEL_FILE,
        WORLD_BANK_COUNTRIES_FILE,
        WORLD_BANK_POPULATION_FILE,
    ]
    missing = [str(path) for path in required_files if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Input Fase 2 belum tersedia: {missing}")

    fact = pd.read_csv(FACT_POWER_PLANT_FILE, low_memory=False)
    if fact["dq_has_blocking_issue"].fillna(True).astype(bool).any():
        raise ValueError("Fase 2 tidak dapat dibangun karena ada blocking issue pada fact_power_plant.")
    fact = add_asset_derivations(fact)

    dim_country = pd.read_csv(DIM_COUNTRY_FILE)
    world_bank = load_world_bank_dimension()
    dim_country = dim_country.merge(
        world_bank, on="country_iso3", how="left", validate="one_to_one"
    )
    dim_country["world_bank_match_status"] = dim_country["region_code"].notna().map(
        {True: "matched", False: "unmatched"}
    )
    dim_country["region_name"] = dim_country["region_name"].fillna(
        "Unmatched / Not classified"
    )
    dim_country["income_group_name"] = dim_country["income_group_name"].fillna(
        "Unmatched / Not classified"
    )
    dim_country["population"] = pd.to_numeric(
        dim_country["population"], errors="coerce"
    ).astype("Int64")
    dim_country["population_year"] = pd.to_numeric(
        dim_country["population_year"], errors="coerce"
    ).astype("Int64")
    dim_country.to_csv(ANALYTICS_DIR / "dim_country.csv", index=False)

    dim_fuel = pd.read_csv(DIM_FUEL_FILE)
    dim_fuel.to_csv(ANALYTICS_DIR / "dim_fuel.csv", index=False)
    pd.DataFrame(AGE_BANDS).to_csv(ANALYTICS_DIR / "dim_age_band.csv", index=False)

    fact = fact.merge(
        dim_country[["country_iso3", "region_name", "income_group_name", "population", "population_year"]],
        on="country_iso3",
        how="left",
        validate="many_to_one",
    )
    fact["year_of_capacity_data"] = pd.to_numeric(
        fact["year_of_capacity_data"], errors="coerce"
    ).astype("Int64")
    core_fact_columns = [
        "plant_id",
        "plant_name",
        "country_iso3",
        "fuel_key",
        "capacity_mw",
        "latitude",
        "longitude",
        "commissioning_year",
        "commissioning_decade",
        "plant_age_years",
        "age_band",
        "age_band_sort",
        "is_fossil_over_30",
        "is_coal_under_15",
        "owner",
        "source",
        "url",
        "year_of_capacity_data",
        "dq_capacity_issue",
        "dq_coordinate_issue",
        "dq_commissioning_issue",
        "dq_has_blocking_issue",
    ]
    fact[core_fact_columns].rename(
        columns={
            "source": "source_name",
            "url": "source_url",
            "year_of_capacity_data": "capacity_data_year",
        }
    ).to_csv(ANALYTICS_DIR / "fact_power_plant.csv", index=False)

    global_kpi = pd.DataFrame([{"scope": "Global", "reference_year": REFERENCE_YEAR, **summarize_assets(fact)}])
    global_kpi.to_csv(ANALYTICS_DIR / "mart_global_kpi.csv", index=False)

    country_kpi = grouped_summary(fact, ["country_iso3", "country_name"])
    country_kpi = country_kpi.merge(
        dim_country[
            [
                "country_iso3",
                "region_name",
                "income_group_name",
                "population",
                "population_year",
                "world_bank_match_status",
            ]
        ],
        on="country_iso3",
        how="left",
        validate="one_to_one",
    )
    country_kpi["capacity_per_million_people_mw"] = (
        country_kpi["total_capacity_mw"] / (country_kpi["population"] / 1_000_000)
    )
    country_kpi["eligible_for_share_ranking"] = country_kpi["total_capacity_mw"].ge(
        SHARE_RANKING_MIN_CAPACITY_MW
    )
    country_kpi["minimum_capacity_for_share_ranking_mw"] = SHARE_RANKING_MIN_CAPACITY_MW
    country_kpi["total_capacity_rank"] = (
        country_kpi["total_capacity_mw"].rank(method="min", ascending=False).astype("Int64")
    )
    rank_eligible(country_kpi, "renewable_share_pct", "renewable_share_rank_eligible")
    rank_eligible(country_kpi, "low_carbon_share_pct", "low_carbon_share_rank_eligible")
    rank_eligible(country_kpi, "coal_dependency_pct", "coal_dependency_rank_eligible")
    country_kpi.to_csv(ANALYTICS_DIR / "mart_country_kpi.csv", index=False)

    region_kpi = grouped_summary(fact, ["region_name"])
    region_kpi.to_csv(ANALYTICS_DIR / "mart_region_kpi.csv", index=False)

    country_fuel = (
        fact.groupby(
            ["country_iso3", "country_name", "fuel_key", "primary_fuel", "fuel_group"],
            observed=True,
            dropna=False,
        )
        .agg(plant_count=("plant_id", "nunique"), capacity_mw=("capacity_mw", "sum"))
        .reset_index()
    )
    country_totals = country_fuel.groupby("country_iso3")["capacity_mw"].transform("sum")
    country_fuel["country_capacity_share_pct"] = country_fuel["capacity_mw"] / country_totals * 100
    country_fuel.to_csv(ANALYTICS_DIR / "mart_country_fuel.csv", index=False)

    global_fuel = (
        fact.groupby(["fuel_key", "primary_fuel", "fuel_group"], observed=True)
        .agg(plant_count=("plant_id", "nunique"), capacity_mw=("capacity_mw", "sum"))
        .reset_index()
    )
    global_fuel["global_capacity_share_pct"] = (
        global_fuel["capacity_mw"] / global_fuel["capacity_mw"].sum() * 100
    )
    global_fuel.to_csv(ANALYTICS_DIR / "mart_global_fuel.csv", index=False)

    country_age = (
        fact.groupby(
            ["country_iso3", "country_name", "age_band", "age_band_sort", "fuel_group"],
            observed=True,
            dropna=False,
        )
        .agg(plant_count=("plant_id", "nunique"), capacity_mw=("capacity_mw", "sum"))
        .reset_index()
        .sort_values(["country_iso3", "age_band_sort", "fuel_group"])
    )
    country_age.to_csv(ANALYTICS_DIR / "mart_country_age_band.csv", index=False)

    fossil_risk_columns = [
        "country_iso3",
        "country_name",
        "region_name",
        "total_capacity_gw",
        "fossil_capacity_mw",
        "fossil_share_pct",
        "coal_capacity_mw",
        "coal_dependency_pct",
        "fossil_capacity_weighted_age_years",
        "fossil_age_coverage_by_capacity_pct",
        "fossil_capacity_over_30_years_mw",
        "fossil_capacity_over_30_years_share_pct",
        "coal_capacity_under_15_years_mw",
        "coal_capacity_under_15_years_share_pct",
    ]
    country_kpi[fossil_risk_columns].to_csv(
        ANALYTICS_DIR / "mart_fossil_asset_risk.csv", index=False
    )

    data_quality_columns = [
        "country_iso3",
        "country_name",
        "region_name",
        "total_plants",
        "total_capacity_mw",
        "known_age_capacity_mw",
        "age_coverage_by_capacity_pct",
        "unknown_commissioning_capacity_mw",
        "unknown_commissioning_capacity_share_pct",
        "world_bank_match_status",
        "population_year",
    ]
    country_kpi[data_quality_columns].to_csv(
        ANALYTICS_DIR / "mart_data_quality_country.csv", index=False
    )

    configuration = {
        "reference_year": REFERENCE_YEAR,
        "share_ranking_min_capacity_mw": SHARE_RANKING_MIN_CAPACITY_MW,
        "population_year": 2020,
        "low_carbon_definition": "Renewable + Nuclear",
        "fossil_over_30_definition": "plant_age_years > 30",
        "coal_under_15_definition": "plant_age_years < 15",
        "diversity_definition": "1 - sum(primary_fuel_capacity_share^2)",
    }
    (ANALYTICS_DIR / "model_config.json").write_text(
        json.dumps(configuration, indent=2) + "\n", encoding="utf-8"
    )
    write_initial_insights(global_kpi, country_kpi)
    print(
        f"Model Fase 2 selesai: {len(fact):,} plants, "
        f"{len(country_kpi)} countries, reference year {REFERENCE_YEAR}."
    )


if __name__ == "__main__":
    build_phase2()
