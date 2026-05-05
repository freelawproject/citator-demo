"""Build script — transforms inference outputs into Eleventy-consumable JSON.

Currently a no-op stub. Real implementation lands in issue #4
(mock fixtures + minimal build_data.py).
"""

from pathlib import Path

OUT_DIR = Path(__file__).parent.parent / "_data" / "opinions"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"build_data.py — stub. Output dir: {OUT_DIR}")


if __name__ == "__main__":
    main()
