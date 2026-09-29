BEGIN;

CREATE OR REPLACE VIEW energy_analytics.v_energy_trend AS
SELECT
    f.entity_code,
    e.entity_name,
    e.entity_type,
    e.country_iso3,
    e.region_name,
    e.income_group_name,
    f.year,
    f.data_type,
    f.has_complete_key_mix,
    f.population,
    f.electricity_generation_twh,
    f.electricity_demand_twh,
    f.fossil_electricity_twh,
    f.renewables_electricity_twh,
    f.nuclear_electricity_twh,
    f.low_carbon_electricity_twh,
    f.coal_electricity_twh,
    f.gas_electricity_twh,
    f.oil_electricity_twh,
    f.hydro_electricity_twh,
    f.solar_electricity_twh,
    f.wind_electricity_twh,
    f.biofuel_electricity_twh,
    f.other_renewable_electricity_twh,
    f.fossil_share_pct,
    f.renewables_share_pct,
    f.nuclear_share_pct,
    f.low_carbon_share_pct,
    f.coal_share_pct,
    f.gas_share_pct,
    f.oil_share_pct,
    f.hydro_share_pct,
    f.solar_share_pct,
    f.wind_share_pct,
    f.biofuel_share_pct,
    f.other_renewables_share_pct,
    f.carbon_intensity_gco2_per_kwh,
    f.greenhouse_gas_emissions_mtco2e,
    f.electricity_generation_per_capita_kwh
FROM energy_core.fact_country_energy_year AS f
JOIN energy_core.dim_energy_entity AS e USING (entity_code);

CREATE OR REPLACE VIEW energy_analytics.v_energy_year_coverage AS
SELECT
    year,
    COUNT(*) AS entity_rows,
    COUNT(electricity_generation_twh) AS entities_with_generation,
    COUNT(renewables_share_pct) AS entities_with_renewable_share,
    COUNT(fossil_share_pct) AS entities_with_fossil_share,
    COUNT(low_carbon_share_pct) AS entities_with_low_carbon_share,
    COUNT(carbon_intensity_gco2_per_kwh) AS entities_with_carbon_intensity,
    COUNT(*) FILTER (WHERE has_complete_key_mix) AS entities_with_complete_key_mix
FROM energy_core.fact_country_energy_year
GROUP BY year;

CREATE OR REPLACE VIEW energy_analytics.v_transition_momentum_2005_2022 AS
WITH endpoints AS (
    SELECT
        e.entity_code,
        e.entity_name AS country_name,
        e.region_name,
        MAX(f.renewables_share_pct) FILTER (WHERE f.year = 2005) AS renewables_share_pct_start,
        MAX(f.renewables_share_pct) FILTER (WHERE f.year = 2022) AS renewables_share_pct_end,
        MAX(f.fossil_share_pct) FILTER (WHERE f.year = 2005) AS fossil_share_pct_start,
        MAX(f.fossil_share_pct) FILTER (WHERE f.year = 2022) AS fossil_share_pct_end,
        MAX(f.nuclear_share_pct) FILTER (WHERE f.year = 2005) AS nuclear_share_pct_start,
        MAX(f.nuclear_share_pct) FILTER (WHERE f.year = 2022) AS nuclear_share_pct_end,
        MAX(f.low_carbon_share_pct) FILTER (WHERE f.year = 2005) AS low_carbon_share_pct_start,
        MAX(f.low_carbon_share_pct) FILTER (WHERE f.year = 2022) AS low_carbon_share_pct_end,
        MAX(f.carbon_intensity_gco2_per_kwh) FILTER (WHERE f.year = 2005)
            AS carbon_intensity_gco2_per_kwh_start,
        MAX(f.carbon_intensity_gco2_per_kwh) FILTER (WHERE f.year = 2022)
            AS carbon_intensity_gco2_per_kwh_end,
        MAX(f.electricity_generation_twh) FILTER (WHERE f.year = 2005)
            AS electricity_generation_twh_start,
        MAX(f.electricity_generation_twh) FILTER (WHERE f.year = 2022)
            AS electricity_generation_twh_end
    FROM energy_core.dim_energy_entity AS e
    LEFT JOIN energy_core.fact_country_energy_year AS f
        ON f.entity_code = e.entity_code AND f.year IN (2005, 2022)
    WHERE e.entity_type = 'country'
    GROUP BY e.entity_code, e.entity_name, e.region_name
),
changes AS (
    SELECT
        endpoints.*,
        2005::SMALLINT AS start_year,
        2022::SMALLINT AS end_year,
        17::SMALLINT AS period_years,
        renewables_share_pct_end - renewables_share_pct_start
            AS renewables_share_pct_change,
        fossil_share_pct_end - fossil_share_pct_start AS fossil_share_pct_change,
        nuclear_share_pct_end - nuclear_share_pct_start AS nuclear_share_pct_change,
        low_carbon_share_pct_end - low_carbon_share_pct_start
            AS low_carbon_share_pct_change,
        carbon_intensity_gco2_per_kwh_end - carbon_intensity_gco2_per_kwh_start
            AS carbon_intensity_gco2_per_kwh_change,
        electricity_generation_twh_end - electricity_generation_twh_start
            AS electricity_generation_twh_change,
        (renewables_share_pct_end - renewables_share_pct_start) / 17.0
            AS renewable_transition_momentum_pp_per_year,
        renewables_share_pct_start IS NOT NULL AND renewables_share_pct_end IS NOT NULL
            AS has_comparable_endpoints
    FROM endpoints
)
SELECT
    changes.*,
    CASE WHEN has_comparable_endpoints THEN
        RANK() OVER (
            ORDER BY CASE WHEN has_comparable_endpoints
                THEN renewable_transition_momentum_pp_per_year END DESC NULLS LAST
        )
    END AS renewable_momentum_rank
FROM changes;

CREATE OR REPLACE VIEW energy_analytics.v_transition_latest AS
SELECT DISTINCT ON (f.entity_code)
    f.entity_code,
    e.entity_name,
    e.entity_type,
    e.region_name,
    f.year,
    f.electricity_generation_twh,
    f.renewables_share_pct,
    f.fossil_share_pct,
    f.nuclear_share_pct,
    f.low_carbon_share_pct,
    f.carbon_intensity_gco2_per_kwh
FROM energy_core.fact_country_energy_year AS f
JOIN energy_core.dim_energy_entity AS e USING (entity_code)
WHERE f.renewables_share_pct IS NOT NULL
ORDER BY f.entity_code, f.year DESC;

COMMIT;
