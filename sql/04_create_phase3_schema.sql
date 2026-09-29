BEGIN;

DROP TABLE IF EXISTS energy_core.fact_country_energy_year CASCADE;
DROP TABLE IF EXISTS energy_core.dim_energy_entity CASCADE;

CREATE TABLE energy_core.dim_energy_entity (
    entity_code TEXT PRIMARY KEY,
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('country', 'world')),
    country_iso3 CHAR(3) REFERENCES energy_core.dim_country(country_iso3),
    source_entity_name TEXT NOT NULL,
    region_name TEXT NOT NULL,
    income_group_name TEXT NOT NULL,
    CONSTRAINT chk_entity_country_key CHECK (
        (entity_type = 'country' AND country_iso3 IS NOT NULL)
        OR (entity_type = 'world' AND country_iso3 IS NULL)
    )
);

CREATE TABLE energy_core.fact_country_energy_year (
    entity_code TEXT NOT NULL REFERENCES energy_core.dim_energy_entity(entity_code),
    year SMALLINT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    data_type TEXT NOT NULL CHECK (data_type = 'compiled'),
    has_complete_key_mix BOOLEAN NOT NULL,
    population BIGINT CHECK (population IS NULL OR population >= 0),
    electricity_generation_twh DOUBLE PRECISION,
    electricity_demand_twh DOUBLE PRECISION,
    fossil_electricity_twh DOUBLE PRECISION,
    renewables_electricity_twh DOUBLE PRECISION,
    nuclear_electricity_twh DOUBLE PRECISION,
    low_carbon_electricity_twh DOUBLE PRECISION,
    coal_electricity_twh DOUBLE PRECISION,
    gas_electricity_twh DOUBLE PRECISION,
    oil_electricity_twh DOUBLE PRECISION,
    hydro_electricity_twh DOUBLE PRECISION,
    solar_electricity_twh DOUBLE PRECISION,
    wind_electricity_twh DOUBLE PRECISION,
    biofuel_electricity_twh DOUBLE PRECISION,
    other_renewable_electricity_twh DOUBLE PRECISION,
    fossil_share_pct DOUBLE PRECISION,
    renewables_share_pct DOUBLE PRECISION,
    nuclear_share_pct DOUBLE PRECISION,
    low_carbon_share_pct DOUBLE PRECISION,
    coal_share_pct DOUBLE PRECISION,
    gas_share_pct DOUBLE PRECISION,
    oil_share_pct DOUBLE PRECISION,
    hydro_share_pct DOUBLE PRECISION,
    solar_share_pct DOUBLE PRECISION,
    wind_share_pct DOUBLE PRECISION,
    biofuel_share_pct DOUBLE PRECISION,
    other_renewables_share_pct DOUBLE PRECISION,
    carbon_intensity_gco2_per_kwh DOUBLE PRECISION,
    greenhouse_gas_emissions_mtco2e DOUBLE PRECISION,
    electricity_generation_per_capita_kwh DOUBLE PRECISION,
    PRIMARY KEY (entity_code, year)
);

CREATE INDEX idx_energy_year ON energy_core.fact_country_energy_year(year);
CREATE INDEX idx_energy_entity_year ON energy_core.fact_country_energy_year(entity_code, year);

COMMENT ON TABLE energy_core.fact_country_energy_year IS
    'Country-year electricity mix compiled from the pinned OWID Energy Data snapshot.';
COMMENT ON COLUMN energy_core.fact_country_energy_year.data_type IS
    'OWID combines multiple upstream sources; rows are labelled compiled rather than reported or estimated.';

COMMIT;

