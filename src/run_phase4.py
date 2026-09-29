"""Run the complete Phase 4 validation and communication workflow."""

from generate_phase4_report import generate_phase4_report
from validate_phase4 import validate_phase4


def run_phase4() -> None:
    summary = validate_phase4()
    if summary["fail_count"]:
        raise RuntimeError("Fase 4 berhenti karena validation gate memiliki failure.")
    generate_phase4_report()
    print("Fase 4 selesai: validation gate dan executive communication tersedia.")


if __name__ == "__main__":
    run_phase4()
