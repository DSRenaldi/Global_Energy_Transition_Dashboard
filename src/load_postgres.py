"""Create and load the project PostgreSQL database through the native psql client."""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from paths import ANALYTICS_DIR, PHASE2_REPORT_DIR, ROOT_DIR


DEFAULT_DATABASE = "energy_transition"
DOTENV_FILE = ROOT_DIR / ".env"
TABLE_FILES = [
    ("energy_core.dim_country", ANALYTICS_DIR / "dim_country.csv"),
    ("energy_core.dim_fuel", ANALYTICS_DIR / "dim_fuel.csv"),
    ("energy_core.dim_age_band", ANALYTICS_DIR / "dim_age_band.csv"),
    ("energy_core.fact_power_plant", ANALYTICS_DIR / "fact_power_plant.csv"),
]


def load_dotenv(path: Path = DOTENV_FILE) -> None:
    """Load simple KEY=VALUE entries without overriding existing environment variables."""
    if not path.exists():
        return
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Format .env tidak valid pada baris {line_number}.")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith(('"', "'")) and value.endswith(value[0]) and len(value) >= 2:
            value = value[1:-1]
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"Nama variable .env tidak valid pada baris {line_number}: {key}")
        os.environ.setdefault(key, value)


def find_psql() -> Path:
    executable = shutil.which("psql")
    if executable:
        return Path(executable)

    candidates = glob.glob("C:/Program Files/PostgreSQL/*/bin/psql.exe")
    if not candidates:
        raise FileNotFoundError("psql tidak ditemukan. Tambahkan PostgreSQL bin ke PATH.")

    def version_key(path: str) -> tuple[int, ...]:
        version = Path(path).parents[1].name
        return tuple(int(part) for part in re.findall(r"\d+", version)) or (0,)

    return Path(max(candidates, key=version_key))


def connection_args(args: argparse.Namespace, database: str) -> list[str]:
    command = [
        str(args.psql),
        "-X",
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        args.host,
        "-p",
        str(args.port),
        "-d",
        database,
    ]
    if args.user:
        command.extend(["-U", args.user])
    if args.no_password:
        command.append("-w")
    return command


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT_DIR,
        check=True,
        text=True,
        capture_output=capture,
    )


def validate_database_name(database: str) -> None:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,62}", database):
        raise ValueError("Nama database hanya boleh berisi huruf, angka, dan underscore.")


def create_database_if_needed(args: argparse.Namespace) -> None:
    validate_database_name(args.database)
    query = f"SELECT 1 FROM pg_database WHERE datname = '{args.database}';"
    result = run(
        connection_args(args, args.maintenance_database) + ["-A", "-t", "-c", query],
        capture=True,
    )
    if result.stdout.strip() != "1":
        run(
            connection_args(args, args.maintenance_database)
            + ["-c", f'CREATE DATABASE "{args.database}" ENCODING \'UTF8\';']
        )
        print(f"Database dibuat: {args.database}")
    else:
        print(f"Database sudah tersedia: {args.database}")


def load_table(args: argparse.Namespace, table: str, csv_path: Path) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"File load tidak ditemukan: {csv_path}")
    psql_path = csv_path.resolve().as_posix().replace("'", "''")
    copy_command = (
        f"\\copy {table} FROM '{psql_path}' "
        "WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8')"
    )
    run(connection_args(args, args.database) + ["-c", copy_command])
    print(f"Loaded {table} <- {csv_path.name}")


def load_postgres(args: argparse.Namespace) -> None:
    if args.dry_run:
        print(f"psql: {args.psql}")
        print(f"target: {args.host}:{args.port}/{args.database}")
        for table, csv_path in TABLE_FILES:
            print(f"load: {table} <- {csv_path}")
        return

    if not args.skip_create_database:
        create_database_if_needed(args)

    run(
        connection_args(args, args.database)
        + ["-f", str(ROOT_DIR / "sql" / "01_create_schema.sql")]
    )
    for table, csv_path in TABLE_FILES:
        load_table(args, table, csv_path)
    run(
        connection_args(args, args.database)
        + ["-f", str(ROOT_DIR / "sql" / "02_create_views.sql")]
    )
    run(connection_args(args, args.database) + ["-c", "ANALYZE;"])
    run(
        connection_args(args, args.database)
        + ["-f", str(ROOT_DIR / "sql" / "03_quality_checks.sql")]
    )
    status = {
        "loaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": args.host,
        "port": args.port,
        "database": args.database,
        "user": args.user,
        "schemas": ["energy_core", "energy_analytics"],
        "postgresql_validation": "completed",
    }
    PHASE2_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (PHASE2_REPORT_DIR / "postgresql_load_status.json").write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("PostgreSQL model selesai dimuat dan diperiksa.")


def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PGPORT", "5432")))
    parser.add_argument("--user", default=os.getenv("PGUSER"))
    parser.add_argument("--database", default=os.getenv("PGDATABASE", DEFAULT_DATABASE))
    parser.add_argument(
        "--maintenance-database",
        default=os.getenv("PGMAINTENANCE_DATABASE", "postgres"),
    )
    parser.add_argument("--skip-create-database", action="store_true")
    parser.add_argument("--no-password", action="store_true", help="Gagal cepat jika kredensial belum tersedia.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--psql", type=Path, default=find_psql())
    return parser.parse_args()


if __name__ == "__main__":
    load_postgres(parse_args())
