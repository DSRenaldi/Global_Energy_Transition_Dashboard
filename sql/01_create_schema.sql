BEGIN;

DROP SCHEMA IF EXISTS energy_analytics CASCADE;
DROP SCHEMA IF EXISTS energy_core CASCADE;

CREATE SCHEMA energy_core;
CREATE SCHEMA energy_analytics;

CREATE TABLE energy_core.dim_country (
    country_iso3 CHAR(3) PRIMARY KEY,
    country_name TEXT NOT NULL,
    source_country_code CHAR(3) NOT NULL,
    source_country_name TEXT NOT NULL,
    mapping_method TEXT NOT NULL,
    mapping_note TEXT,
    is_iso3_format BOOLEAN NOT NULL,
    world_bank_country_name TEXT,
    region_code TEXT,
    region_name TEXT NOT NULL,
    income_group_code TEXT,
    income_group_name TEXT NOT NULL,
    capital_city TEXT,
    population BIGINT,
    population_year SMALLINT,
    world_bank_match_status TEXT NOT NULL,
    CONSTRAINT chk_country_mapping_status
        CHECK (world_bank_match_status IN ('matched', 'unmatched')),
    CONSTRAINT chk_population_positive
        CHECK (population IS NULL OR population > 0)
);

CREATE TABLE energy_core.dim_fuel (
    primary_fuel TEXT NOT NULL UNIQUE,
    fuel_key TEXT PRIMARY KEY,
    fuel_group TEXT NOT NULL,
    is_fossil BOOLEAN NOT NULL,
    is_renewable BOOLEAN NOT NULL,
    is_nuclear BOOLEAN NOT NULL,
    is_low_carbon BOOLEAN NOT NULL,
    CONSTRAINT chk_fuel_group
        CHECK (fuel_group IN ('Fossil', 'Renewable', 'Nuclear', 'Other / Unknown'))
);

CREATE TABLE energy_core.dim_age_band (
    age_band TEXT PRIMARY KEY,
    age_band_sort SMALLINT NOT NULL UNIQUE,
    lower_bound NUMERIC,
    upper_bound NUMERIC,
    CONSTRAINT chk_age_bounds
        CHECK (
            age_band = 'Unknown'
            OR (lower_bound >= 0 AND (upper_bound IS NULL OR upper_bound > lower_bound))
        )
);

CREATE TABLE energy_core.fact_power_plant (
    plant_id TEXT PRIMARY KEY,
    plant_name TEXT NOT NULL,
    country_iso3 CHAR(3) NOT NULL REFERENCES energy_core.dim_country(country_iso3),
    fuel_key TEXT NOT NULL REFERENCES energy_core.dim_fuel(fuel_key),
    capacity_mw NUMERIC(20, 6) NOT NULL CHECK (capacity_mw > 0),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    commissioning_year NUMERIC(8, 3),
    commissioning_decade SMALLINT,
    plant_age_years NUMERIC(8, 3),
    age_band TEXT NOT NULL REFERENCES energy_core.dim_age_band(age_band),
    age_band_sort SMALLINT NOT NULL,
    is_fossil_over_30 BOOLEAN NOT NULL,
    is_coal_under_15 BOOLEAN NOT NULL,
    owner TEXT,
    source_name TEXT,
    source_url TEXT,
    capacity_data_year SMALLINT,
    dq_capacity_issue TEXT NOT NULL,
    dq_coordinate_issue TEXT NOT NULL,
    dq_commissioning_issue TEXT NOT NULL,
    dq_has_blocking_issue BOOLEAN NOT NULL,
    CONSTRAINT chk_latitude CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    CONSTRAINT chk_longitude CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
    CONSTRAINT chk_plant_age CHECK (plant_age_years IS NULL OR plant_age_years >= 0),
    CONSTRAINT chk_age_band_sort CHECK (age_band_sort BETWEEN 1 AND 5)
);

CREATE INDEX idx_fact_country ON energy_core.fact_power_plant(country_iso3);
CREATE INDEX idx_fact_fuel ON energy_core.fact_power_plant(fuel_key);
CREATE INDEX idx_fact_age_band ON energy_core.fact_power_plant(age_band_sort);
CREATE INDEX idx_fact_coordinates ON energy_core.fact_power_plant(latitude, longitude);

COMMENT ON SCHEMA energy_core IS 'Clean star-schema tables for the Global Energy Transition Dashboard.';
COMMENT ON SCHEMA energy_analytics IS 'PostgreSQL views for dashboard KPIs and asset analysis.';
COMMENT ON COLUMN energy_core.fact_power_plant.plant_age_years IS
    'Indicative age calculated as 2020 minus commissioning_year; null when commissioning year is unavailable.';

COMMIT;

