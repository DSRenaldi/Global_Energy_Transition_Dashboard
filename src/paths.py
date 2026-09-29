"""Shared filesystem paths for the project."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference"
REPORT_DIR = ROOT_DIR / "reports" / "data_quality"
ANALYTICS_DIR = DATA_DIR / "analytics"
PHASE2_REPORT_DIR = ROOT_DIR / "reports" / "phase2"
PHASE3_REPORT_DIR = ROOT_DIR / "reports" / "phase3"
PHASE4_REPORT_DIR = ROOT_DIR / "reports" / "phase4"

RAW_DATA_FILE = RAW_DIR / "global_power_plant_database_v1_3_0.csv"
SOURCE_METADATA_FILE = RAW_DIR / "source_metadata.json"
FUEL_MAPPING_FILE = REFERENCE_DIR / "fuel_mapping.csv"
COUNTRY_OVERRIDES_FILE = REFERENCE_DIR / "country_overrides.csv"
FACT_POWER_PLANT_FILE = PROCESSED_DIR / "fact_power_plant.csv"
DIM_COUNTRY_FILE = PROCESSED_DIR / "dim_country.csv"
DIM_FUEL_FILE = PROCESSED_DIR / "dim_fuel.csv"
WORLD_BANK_COUNTRIES_FILE = RAW_DIR / "world_bank_countries.json"
WORLD_BANK_POPULATION_FILE = RAW_DIR / "world_bank_population_2020.json"
WORLD_BANK_METADATA_FILE = RAW_DIR / "world_bank_source_metadata.json"
OWID_ENERGY_FILE = RAW_DIR / "owid-energy-data.csv"
OWID_CODEBOOK_FILE = RAW_DIR / "owid-energy-codebook.csv"
OWID_METADATA_FILE = RAW_DIR / "owid_source_metadata.json"


def ensure_directories() -> None:
    """Create all generated-data directories when absent."""
    for directory in (
        RAW_DIR,
        INTERIM_DIR,
        PROCESSED_DIR,
        REFERENCE_DIR,
        REPORT_DIR,
        ANALYTICS_DIR,
        PHASE2_REPORT_DIR,
        PHASE3_REPORT_DIR,
        PHASE4_REPORT_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
