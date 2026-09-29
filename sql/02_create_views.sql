BEGIN;

CREATE OR REPLACE VIEW energy_analytics.v_country_fuel_mix AS
WITH fuel_capacity AS (
    SELECT
        p.country_iso3,
        c.country_name,
        p.fuel_key,
        f.primary_fuel,
        f.fuel_group,
        COUNT(*) AS plant_count,
        SUM(p.capacity_mw) AS capacity_mw
    FROM energy_core.fact_power_plant AS p
    JOIN energy_core.dim_country AS c USING (country_iso3)
    JOIN energy_core.dim_fuel AS f USING (fuel_key)
    GROUP BY p.country_iso3, c.country_name, p.fuel_key, f.primary_fuel, f.fuel_group
)
SELECT
    fuel_capacity.*,
    100.0 * capacity_mw
        / NULLIF(SUM(capacity_mw) OVER (PARTITION BY country_iso3), 0)
        AS country_capacity_share_pct
FROM fuel_capacity;

CREATE OR REPLACE VIEW energy_analytics.v_country_kpi AS
WITH base AS (
    SELECT
        p.country_iso3,
        c.country_name,
        c.region_name,
        c.income_group_name,
        c.population,
        c.population_year,
        c.world_bank_match_status,
        COUNT(*) AS total_plants,
        SUM(p.capacity_mw) AS total_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE f.is_fossil) AS fossil_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE f.is_renewable) AS renewable_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE f.is_nuclear) AS nuclear_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE f.is_low_carbon) AS low_carbon_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE f.fuel_group = 'Other / Unknown') AS other_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE f.primary_fuel = 'Coal') AS coal_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE f.primary_fuel = 'Gas') AS gas_capacity_mw,
        AVG(p.capacity_mw) AS average_plant_capacity_mw,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.capacity_mw) AS median_plant_capacity_mw,
        SUM(p.plant_age_years * p.capacity_mw) FILTER (WHERE p.plant_age_years IS NOT NULL)
            / NULLIF(SUM(p.capacity_mw) FILTER (WHERE p.plant_age_years IS NOT NULL), 0)
            AS capacity_weighted_age_years,
        SUM(p.capacity_mw) FILTER (WHERE p.plant_age_years IS NOT NULL) AS known_age_capacity_mw,
        SUM(p.plant_age_years * p.capacity_mw)
            FILTER (WHERE f.is_fossil AND p.plant_age_years IS NOT NULL)
            / NULLIF(
                SUM(p.capacity_mw) FILTER (WHERE f.is_fossil AND p.plant_age_years IS NOT NULL),
                0
            ) AS fossil_capacity_weighted_age_years,
        SUM(p.capacity_mw) FILTER (WHERE f.is_fossil AND p.plant_age_years IS NOT NULL)
            AS fossil_known_age_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE p.is_fossil_over_30)
            AS fossil_capacity_over_30_years_mw,
        SUM(p.capacity_mw) FILTER (WHERE p.is_coal_under_15)
            AS coal_capacity_under_15_years_mw
    FROM energy_core.fact_power_plant AS p
    JOIN energy_core.dim_country AS c USING (country_iso3)
    JOIN energy_core.dim_fuel AS f USING (fuel_key)
    GROUP BY
        p.country_iso3,
        c.country_name,
        c.region_name,
        c.income_group_name,
        c.population,
        c.population_year,
        c.world_bank_match_status
),
diversity AS (
    SELECT
        country_iso3,
        SUM(POWER(country_capacity_share_pct / 100.0, 2)) AS fuel_concentration_hhi
    FROM energy_analytics.v_country_fuel_mix
    GROUP BY country_iso3
),
dominant AS (
    SELECT DISTINCT ON (country_iso3)
        country_iso3,
        primary_fuel AS dominant_primary_fuel,
        country_capacity_share_pct AS dominant_fuel_share_pct
    FROM energy_analytics.v_country_fuel_mix
    ORDER BY country_iso3, capacity_mw DESC, primary_fuel
)
SELECT
    base.country_iso3,
    base.country_name,
    base.region_name,
    base.income_group_name,
    base.population,
    base.population_year,
    base.world_bank_match_status,
    base.total_plants,
    base.total_capacity_mw,
    base.total_capacity_mw / 1000.0 AS total_capacity_gw,
    COALESCE(base.fossil_capacity_mw, 0) AS fossil_capacity_mw,
    COALESCE(base.renewable_capacity_mw, 0) AS renewable_capacity_mw,
    COALESCE(base.nuclear_capacity_mw, 0) AS nuclear_capacity_mw,
    COALESCE(base.low_carbon_capacity_mw, 0) AS low_carbon_capacity_mw,
    COALESCE(base.other_capacity_mw, 0) AS other_capacity_mw,
    COALESCE(base.coal_capacity_mw, 0) AS coal_capacity_mw,
    COALESCE(base.gas_capacity_mw, 0) AS gas_capacity_mw,
    100.0 * COALESCE(base.fossil_capacity_mw, 0) / NULLIF(base.total_capacity_mw, 0)
        AS fossil_share_pct,
    100.0 * COALESCE(base.renewable_capacity_mw, 0) / NULLIF(base.total_capacity_mw, 0)
        AS renewable_share_pct,
    100.0 * COALESCE(base.nuclear_capacity_mw, 0) / NULLIF(base.total_capacity_mw, 0)
        AS nuclear_share_pct,
    100.0 * COALESCE(base.low_carbon_capacity_mw, 0) / NULLIF(base.total_capacity_mw, 0)
        AS low_carbon_share_pct,
    100.0 * COALESCE(base.other_capacity_mw, 0) / NULLIF(base.total_capacity_mw, 0)
        AS other_share_pct,
    100.0 * COALESCE(base.coal_capacity_mw, 0) / NULLIF(base.total_capacity_mw, 0)
        AS coal_dependency_pct,
    base.average_plant_capacity_mw,
    base.median_plant_capacity_mw,
    base.capacity_weighted_age_years,
    COALESCE(base.known_age_capacity_mw, 0) AS known_age_capacity_mw,
    100.0 * COALESCE(base.known_age_capacity_mw, 0) / NULLIF(base.total_capacity_mw, 0)
        AS age_coverage_by_capacity_pct,
    base.total_capacity_mw - COALESCE(base.known_age_capacity_mw, 0)
        AS unknown_commissioning_capacity_mw,
    100.0 * (base.total_capacity_mw - COALESCE(base.known_age_capacity_mw, 0))
        / NULLIF(base.total_capacity_mw, 0) AS unknown_commissioning_capacity_share_pct,
    base.fossil_capacity_weighted_age_years,
    100.0 * COALESCE(base.fossil_known_age_capacity_mw, 0)
        / NULLIF(base.fossil_capacity_mw, 0) AS fossil_age_coverage_by_capacity_pct,
    COALESCE(base.fossil_capacity_over_30_years_mw, 0)
        AS fossil_capacity_over_30_years_mw,
    100.0 * COALESCE(base.fossil_capacity_over_30_years_mw, 0)
        / NULLIF(base.fossil_capacity_mw, 0) AS fossil_capacity_over_30_years_share_pct,
    COALESCE(base.coal_capacity_under_15_years_mw, 0)
        AS coal_capacity_under_15_years_mw,
    100.0 * COALESCE(base.coal_capacity_under_15_years_mw, 0)
        / NULLIF(base.coal_capacity_mw, 0) AS coal_capacity_under_15_years_share_pct,
    diversity.fuel_concentration_hhi,
    1.0 - diversity.fuel_concentration_hhi AS fuel_diversity_index,
    1.0 / NULLIF(diversity.fuel_concentration_hhi, 0) AS effective_fuel_count,
    dominant.dominant_primary_fuel,
    dominant.dominant_fuel_share_pct,
    base.total_capacity_mw / NULLIF(base.population / 1000000.0, 0)
        AS capacity_per_million_people_mw,
    base.total_capacity_mw >= 1000 AS eligible_for_share_ranking,
    1000.0 AS minimum_capacity_for_share_ranking_mw,
    RANK() OVER (ORDER BY base.total_capacity_mw DESC) AS total_capacity_rank
FROM base
JOIN diversity USING (country_iso3)
JOIN dominant USING (country_iso3);

CREATE OR REPLACE VIEW energy_analytics.v_global_kpi AS
WITH fuel_capacity AS (
    SELECT p.fuel_key, SUM(p.capacity_mw) AS capacity_mw
    FROM energy_core.fact_power_plant AS p
    GROUP BY p.fuel_key
),
fuel_total AS (
    SELECT SUM(capacity_mw) AS total_capacity_mw
    FROM fuel_capacity
),
concentration AS (
    SELECT
        SUM(POWER(fuel_capacity.capacity_mw / NULLIF(fuel_total.total_capacity_mw, 0), 2))
            AS fuel_concentration_hhi
    FROM fuel_capacity
    CROSS JOIN fuel_total
),
base AS (
    SELECT
        COUNT(*) AS total_plants,
        SUM(p.capacity_mw) AS total_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE f.is_fossil) AS fossil_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE f.is_renewable) AS renewable_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE f.is_nuclear) AS nuclear_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE f.is_low_carbon) AS low_carbon_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE f.fuel_group = 'Other / Unknown') AS other_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE f.primary_fuel = 'Coal') AS coal_capacity_mw,
        AVG(p.capacity_mw) AS average_plant_capacity_mw,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.capacity_mw) AS median_plant_capacity_mw,
        SUM(p.plant_age_years * p.capacity_mw) FILTER (WHERE p.plant_age_years IS NOT NULL)
            / NULLIF(SUM(p.capacity_mw) FILTER (WHERE p.plant_age_years IS NOT NULL), 0)
            AS capacity_weighted_age_years,
        SUM(p.capacity_mw) FILTER (WHERE p.plant_age_years IS NOT NULL) AS known_age_capacity_mw,
        SUM(p.plant_age_years * p.capacity_mw)
            FILTER (WHERE f.is_fossil AND p.plant_age_years IS NOT NULL)
            / NULLIF(
                SUM(p.capacity_mw) FILTER (WHERE f.is_fossil AND p.plant_age_years IS NOT NULL),
                0
            ) AS fossil_capacity_weighted_age_years,
        SUM(p.capacity_mw) FILTER (WHERE f.is_fossil AND p.plant_age_years IS NOT NULL)
            AS fossil_known_age_capacity_mw,
        SUM(p.capacity_mw) FILTER (WHERE p.is_fossil_over_30)
            AS fossil_capacity_over_30_years_mw,
        SUM(p.capacity_mw) FILTER (WHERE p.is_coal_under_15)
            AS coal_capacity_under_15_years_mw
    FROM energy_core.fact_power_plant AS p
    JOIN energy_core.dim_fuel AS f USING (fuel_key)
)
SELECT
    'Global'::TEXT AS scope,
    2020::SMALLINT AS reference_year,
    base.*,
    base.total_capacity_mw / 1000.0 AS total_capacity_gw,
    100.0 * base.fossil_capacity_mw / base.total_capacity_mw AS fossil_share_pct,
    100.0 * base.renewable_capacity_mw / base.total_capacity_mw AS renewable_share_pct,
    100.0 * base.nuclear_capacity_mw / base.total_capacity_mw AS nuclear_share_pct,
    100.0 * base.low_carbon_capacity_mw / base.total_capacity_mw AS low_carbon_share_pct,
    100.0 * base.other_capacity_mw / base.total_capacity_mw AS other_share_pct,
    100.0 * base.coal_capacity_mw / base.total_capacity_mw AS coal_dependency_pct,
    100.0 * base.known_age_capacity_mw / base.total_capacity_mw AS age_coverage_by_capacity_pct,
    base.total_capacity_mw - base.known_age_capacity_mw AS unknown_commissioning_capacity_mw,
    100.0 * (base.total_capacity_mw - base.known_age_capacity_mw) / base.total_capacity_mw
        AS unknown_commissioning_capacity_share_pct,
    100.0 * base.fossil_known_age_capacity_mw / base.fossil_capacity_mw
        AS fossil_age_coverage_by_capacity_pct,
    100.0 * base.fossil_capacity_over_30_years_mw / base.fossil_capacity_mw
        AS fossil_capacity_over_30_years_share_pct,
    100.0 * base.coal_capacity_under_15_years_mw / base.coal_capacity_mw
        AS coal_capacity_under_15_years_share_pct,
    concentration.fuel_concentration_hhi,
    1.0 - concentration.fuel_concentration_hhi AS fuel_diversity_index,
    1.0 / concentration.fuel_concentration_hhi AS effective_fuel_count
FROM base
CROSS JOIN concentration;

CREATE OR REPLACE VIEW energy_analytics.v_country_age_band AS
SELECT
    p.country_iso3,
    c.country_name,
    p.age_band,
    p.age_band_sort,
    f.fuel_group,
    COUNT(*) AS plant_count,
    SUM(p.capacity_mw) AS capacity_mw
FROM energy_core.fact_power_plant AS p
JOIN energy_core.dim_country AS c USING (country_iso3)
JOIN energy_core.dim_fuel AS f USING (fuel_key)
GROUP BY p.country_iso3, c.country_name, p.age_band, p.age_band_sort, f.fuel_group;

CREATE OR REPLACE VIEW energy_analytics.v_global_fuel AS
SELECT
    p.fuel_key,
    f.primary_fuel,
    f.fuel_group,
    COUNT(*) AS plant_count,
    SUM(p.capacity_mw) AS capacity_mw,
    100.0 * SUM(p.capacity_mw) / SUM(SUM(p.capacity_mw)) OVER ()
        AS global_capacity_share_pct
FROM energy_core.fact_power_plant AS p
JOIN energy_core.dim_fuel AS f USING (fuel_key)
GROUP BY p.fuel_key, f.primary_fuel, f.fuel_group;

CREATE OR REPLACE VIEW energy_analytics.v_country_ranking AS
SELECT
    country_kpi.*,
    CASE WHEN eligible_for_share_ranking THEN
        RANK() OVER (
            ORDER BY CASE WHEN eligible_for_share_ranking THEN renewable_share_pct END DESC NULLS LAST
        )
    END AS renewable_share_rank_eligible,
    CASE WHEN eligible_for_share_ranking THEN
        RANK() OVER (
            ORDER BY CASE WHEN eligible_for_share_ranking THEN low_carbon_share_pct END DESC NULLS LAST
        )
    END AS low_carbon_share_rank_eligible,
    CASE WHEN eligible_for_share_ranking THEN
        RANK() OVER (
            ORDER BY CASE WHEN eligible_for_share_ranking THEN coal_dependency_pct END DESC NULLS LAST
        )
    END AS coal_dependency_rank_eligible
FROM energy_analytics.v_country_kpi AS country_kpi;

CREATE OR REPLACE VIEW energy_analytics.v_region_kpi AS
SELECT
    c.region_name,
    COUNT(*) AS total_plants,
    SUM(p.capacity_mw) AS total_capacity_mw,
    SUM(p.capacity_mw) / 1000.0 AS total_capacity_gw,
    100.0 * SUM(p.capacity_mw) FILTER (WHERE f.is_fossil)
        / NULLIF(SUM(p.capacity_mw), 0) AS fossil_share_pct,
    100.0 * SUM(p.capacity_mw) FILTER (WHERE f.is_renewable)
        / NULLIF(SUM(p.capacity_mw), 0) AS renewable_share_pct,
    100.0 * SUM(p.capacity_mw) FILTER (WHERE f.is_low_carbon)
        / NULLIF(SUM(p.capacity_mw), 0) AS low_carbon_share_pct,
    100.0 * SUM(p.capacity_mw) FILTER (WHERE f.primary_fuel = 'Coal')
        / NULLIF(SUM(p.capacity_mw), 0) AS coal_dependency_pct,
    SUM(p.plant_age_years * p.capacity_mw) FILTER (WHERE p.plant_age_years IS NOT NULL)
        / NULLIF(SUM(p.capacity_mw) FILTER (WHERE p.plant_age_years IS NOT NULL), 0)
        AS capacity_weighted_age_years,
    100.0 * SUM(p.capacity_mw) FILTER (WHERE p.plant_age_years IS NOT NULL)
        / NULLIF(SUM(p.capacity_mw), 0) AS age_coverage_by_capacity_pct
FROM energy_core.fact_power_plant AS p
JOIN energy_core.dim_country AS c USING (country_iso3)
JOIN energy_core.dim_fuel AS f USING (fuel_key)
GROUP BY c.region_name;

CREATE OR REPLACE VIEW energy_analytics.v_data_quality_country AS
SELECT
    country_iso3,
    country_name,
    region_name,
    total_plants,
    total_capacity_mw,
    known_age_capacity_mw,
    age_coverage_by_capacity_pct,
    unknown_commissioning_capacity_mw,
    unknown_commissioning_capacity_share_pct,
    world_bank_match_status,
    population_year
FROM energy_analytics.v_country_kpi;

CREATE OR REPLACE VIEW energy_analytics.v_fossil_asset_risk AS
SELECT
    country_iso3,
    country_name,
    region_name,
    total_capacity_gw,
    fossil_capacity_mw,
    fossil_share_pct,
    coal_capacity_mw,
    coal_dependency_pct,
    fossil_capacity_weighted_age_years,
    fossil_age_coverage_by_capacity_pct,
    fossil_capacity_over_30_years_mw,
    fossil_capacity_over_30_years_share_pct,
    coal_capacity_under_15_years_mw,
    coal_capacity_under_15_years_share_pct
FROM energy_analytics.v_country_kpi;

COMMIT;
