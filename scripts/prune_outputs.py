"""Delete output/report files older than the retention window (default 21 days).

Usage (run from the repo root in CI):
    python scripts/prune_outputs.py "output/*.md" "reports/*.md" "digest/*" "raw/*"

Dates are parsed from file/directory names in either YYYY-MM-DD or YYYY-Www form.
Files whose parsed date is older than the window are removed so the git history
and workspace keep only the last ~3 weeks of generated reports.
"""
from __future__ import annotations

import re
import shutil
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

DATE_RE = re.compile(r"(20\d{2})[-_.](\d{2})[-_.](\d{2})")
WEEK_RE = re.compile(r"(20\d{2})-W(\d{1,2})", re.IGNORECASE)
RETAIN_DAYS = 21


def _date_from_name(name: str) -> date | None:
    match = DATE_RE.search(name)
    if match:
        year, month, day = (int(group) for group in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    match = WEEK_RE.search(name)
    if match:
        year, week = int(match.group(1)), int(match.group(2))
        if 1 <= week <= 53:
            try:
                jan4 = date(year, 1, 4)
                return jan4 + timedelta(weeks=week - jan4.isocalendar()[1])
            except ValueError:
                return None
    return None


def main(argv: list[str] | None = None) -> int:
    patterns = argv if argv is not None else sys.argv[1:]
    if not patterns:
        print("usage: prune_outputs.py <glob ...>", file=sys.stderr)
        return 2
    cutoff = datetime.now(UTC).date() - timedelta(days=RETAIN_DAYS)
    removed = 0
    for pattern in patterns:
        for path in Path(".").glob(pattern):
            stamp = _date_from_name(path.name)
            if stamp is not None and stamp < cutoff:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                removed += 1
                print(f"pruned: {path}")
    print(f"pruned {removed} entries older than {RETAIN_DAYS} days")
    return 0


if __name__ == "__main__":
    sys.exit(main())
