"""Build and validate all Phase 3 historical transition assets."""

from build_phase3 import build_phase3
from validate_phase3 import validate_phase3


if __name__ == "__main__":
    build_phase3()
    validate_phase3()

