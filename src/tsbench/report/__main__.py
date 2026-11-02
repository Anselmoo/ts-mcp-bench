"""`tsbench report views ...`: the per-run views (see tsbench.report.views); `render` stays as an alias of `views`."""
from __future__ import annotations

import sys

from tsbench.report import views


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] in (["render"], ["views"]):
        argv = argv[1:]
    elif argv and argv[0] not in ("-h", "--help") and not argv[0].startswith("--"):
        print(f"tsbench report: unknown subcommand {argv[0]!r} (views, full, gallery, comparison, dashboard, "
              "literature, coverage, artifacts)", file=sys.stderr)
        return 2
    return views.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
