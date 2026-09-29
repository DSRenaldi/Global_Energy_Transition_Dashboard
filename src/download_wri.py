"""Download and verify the pinned WRI Global Power Plant Database snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from paths import RAW_DATA_FILE, SOURCE_METADATA_FILE, ensure_directories


DATASET_VERSION = "1.3.0"
SOURCE_COMMIT = "7a91cfbb2a4e272597acbc00506d61fc1ec73b3d"
SOURCE_URL = (
    "https://raw.githubusercontent.com/wri/global-power-plant-database/"
    f"{SOURCE_COMMIT}/output_database/global_power_plant_database.csv"
)
SOURCE_PAGE = "https://github.com/wri/global-power-plant-database"
EXPECTED_SHA256 = "4b1f93e0fd93664f18684d9b05d0a52ed9658c6a8cf0d21ff2520791379ba7fc"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_metadata(path: Path, sha256: str) -> None:
    metadata = {
        "dataset_name": "Global Power Plant Database",
        "publisher": "World Resources Institute",
        "dataset_version": DATASET_VERSION,
        "source_page": SOURCE_PAGE,
        "download_url": SOURCE_URL,
        "source_commit": SOURCE_COMMIT,
        "license": "CC BY 4.0",
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "local_file": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": sha256,
        "maintenance_note": (
            "WRI states that the repository is not currently maintained and that "
            "version 1.3.0 is the final published database version."
        ),
    }
    SOURCE_METADATA_FILE.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def download(force: bool = False) -> None:
    ensure_directories()

    if RAW_DATA_FILE.exists() and not force:
        actual_hash = sha256_file(RAW_DATA_FILE)
        if actual_hash != EXPECTED_SHA256:
            raise RuntimeError(
                "File mentah sudah ada tetapi checksum tidak sesuai. "
                "Hapus file secara manual atau jalankan dengan --force setelah diperiksa."
            )
        if not SOURCE_METADATA_FILE.exists():
            write_metadata(RAW_DATA_FILE, actual_hash)
        print(f"Snapshot sudah tersedia dan valid: {RAW_DATA_FILE}")
        print(f"SHA-256: {actual_hash}")
        return

    request = Request(SOURCE_URL, headers={"User-Agent": "energy-transition-dashboard/1.0"})
    temporary_path: Path | None = None
    try:
        with urlopen(request, timeout=120) as response:
            with tempfile.NamedTemporaryFile(
                mode="wb", delete=False, dir=RAW_DATA_FILE.parent, suffix=".download"
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                while chunk := response.read(1024 * 1024):
                    temporary_file.write(chunk)

        actual_hash = sha256_file(temporary_path)
        if actual_hash != EXPECTED_SHA256:
            raise RuntimeError(
                f"Checksum snapshot tidak sesuai: {actual_hash}; expected {EXPECTED_SHA256}."
            )

        os.replace(temporary_path, RAW_DATA_FILE)
        temporary_path = None
        write_metadata(RAW_DATA_FILE, actual_hash)
        print(f"Snapshot berhasil diunduh: {RAW_DATA_FILE}")
        print(f"SHA-256: {actual_hash}")
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Unduh ulang snapshot yang sudah ada.")
    return parser.parse_args()


if __name__ == "__main__":
    download(force=parse_args().force)

