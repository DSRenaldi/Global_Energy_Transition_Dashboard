"""Download World Bank country metadata and snapshot-aligned population data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from paths import (
    WORLD_BANK_COUNTRIES_FILE,
    WORLD_BANK_METADATA_FILE,
    WORLD_BANK_POPULATION_FILE,
    ensure_directories,
)


POPULATION_YEAR = 2020
COUNTRIES_URL = "https://api.worldbank.org/v2/country?format=json&per_page=400"
POPULATION_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL"
    f"?date={POPULATION_YEAR}&format=json&per_page=400"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "energy-transition-dashboard/1.0"})
    temporary_path: Path | None = None
    try:
        with urlopen(request, timeout=120) as response:
            with tempfile.NamedTemporaryFile(
                mode="wb", delete=False, dir=destination.parent, suffix=".download"
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                while chunk := response.read(1024 * 1024):
                    temporary_file.write(chunk)
        json.loads(temporary_path.read_text(encoding="utf-8"))
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def write_metadata() -> None:
    metadata = {
        "publisher": "World Bank",
        "api_version": "v2",
        "accessed_at_utc": datetime.now(timezone.utc).isoformat(),
        "country_metadata": {
            "url": COUNTRIES_URL,
            "local_file": WORLD_BANK_COUNTRIES_FILE.name,
            "sha256": sha256_file(WORLD_BANK_COUNTRIES_FILE),
            "size_bytes": WORLD_BANK_COUNTRIES_FILE.stat().st_size,
            "classification_note": "Region and income group reflect the API classification at access time.",
        },
        "population": {
            "indicator": "SP.POP.TOTL",
            "year": POPULATION_YEAR,
            "url": POPULATION_URL,
            "local_file": WORLD_BANK_POPULATION_FILE.name,
            "sha256": sha256_file(WORLD_BANK_POPULATION_FILE),
            "size_bytes": WORLD_BANK_POPULATION_FILE.stat().st_size,
        },
    }
    WORLD_BANK_METADATA_FILE.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def download(force: bool = False) -> None:
    ensure_directories()
    targets = [
        (COUNTRIES_URL, WORLD_BANK_COUNTRIES_FILE),
        (POPULATION_URL, WORLD_BANK_POPULATION_FILE),
    ]
    for url, destination in targets:
        if force or not destination.exists():
            download_file(url, destination)
            print(f"Diunduh: {destination}")
        else:
            json.loads(destination.read_text(encoding="utf-8"))
            print(f"Sudah tersedia: {destination}")
    write_metadata()
    print(f"Metadata sumber ditulis: {WORLD_BANK_METADATA_FILE}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Unduh ulang respons API.")
    return parser.parse_args()


if __name__ == "__main__":
    download(force=parse_args().force)

