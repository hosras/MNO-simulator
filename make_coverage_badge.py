"""Generate a coverage badge SVG from the current coverage data.

Reads .coverage (created by `coverage run`) and writes a small SVG
badge to .github/coverage.svg.

Usage:
    coverage run --source=. -m pytest --run-slow -q
    python make_coverage_badge.py
"""

import sys
from pathlib import Path

try:
    import coverage
except ImportError as e:
    raise SystemExit("coverage is required: pip install coverage") from e


ROOT = Path(__file__).resolve().parent
OUT = ROOT / ".github" / "coverage.svg"


def coverage_color(pct: float) -> str:
    """Return a hex color for a given coverage percentage."""
    if pct >= 90:
        return "#4c1"  # bright green
    if pct >= 80:
        return "#97ca00"  # yellow-green
    if pct >= 70:
        return "#dfb317"  # yellow
    if pct >= 60:
        return "#fe7d37"  # orange
    if pct >= 50:
        return "#e05d44"  # red-orange
    return "#cb2431"  # red


def render_svg(pct: float) -> str:
    """Return the SVG badge markup."""
    color = coverage_color(pct)
    label = "coverage"
    value = f"{pct:.0f}%"

    # Approximate text widths (Helvetica ~6px/char at 11px font-size)
    label_w = 62
    value_w = 46
    total_w = label_w + value_w

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="20" role="img" aria-label="{label}: {value}">
  <title>{label}: {value}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_w}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="20" fill="#555"/>
    <rect x="{label_w}" width="{value_w}" height="20" fill="{color}"/>
    <rect width="{total_w}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle"
     font-family="Verdana,Geneva,DejaVu Sans,sans-serif"
     text-rendering="geometricPrecision" font-size="11">
    <text aria-hidden="true" x="{label_w // 2}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_w // 2}" y="14">{label}</text>
    <text aria-hidden="true" x="{label_w + value_w // 2}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{label_w + value_w // 2}" y="14">{value}</text>
  </g>
</svg>
"""


def main():
    if not (ROOT / ".coverage").exists():
        raise SystemExit(
            "No .coverage file found. Run:\n" "    coverage run --source=. -m pytest --run-slow -q"
        )

    cov = coverage.Coverage()
    cov.load()
    pct = cov.report(show_missing=False, file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render_svg(pct), encoding="utf-8")
    print(f"[OK]  wrote {OUT}  ({pct:.1f}% coverage)")


if __name__ == "__main__":
    main()
