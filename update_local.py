"""
Local update: runs all scrapers including Selenium ones non-headless.
Designed to run on PC startup via Windows Task Scheduler.
"""
import sys
import time
import traceback

from scrapers import elabe, bva, csa, ipsos, opinionway, harris, odoxa, ifop
from merge import merge

SCRAPERS = [
    ("ELABE", elabe),
    ("BVA", bva),
    ("CSA", csa),
    ("IPSOS", ipsos),
    ("OPINION WAY", opinionway),
    ("HARRIS", harris),
    ("ODOXA", odoxa),
]


def main():
    print("=" * 50)
    print("  LOCAL UPDATE — Incremental scraping")
    print("=" * 50)
    sys.stdout.flush()

    results = {}

    for name, module in SCRAPERS:
        print(f"\n--- {name} ---")
        sys.stdout.flush()
        try:
            result = module.update()
            results[name] = result
        except Exception:
            print(f"  [{name}] FAILED:")
            traceback.print_exc()
            results[name] = "FAILED"
        time.sleep(2)

    # IFOP separately — non-headless to avoid captcha
    print("\n--- IFOP (non-headless) ---")
    sys.stdout.flush()
    try:
        result = ifop.update(max_pages=10, headless=False)
        results["IFOP"] = result
    except Exception:
        print("  [IFOP] FAILED:")
        traceback.print_exc()
        results["IFOP"] = "FAILED"

    # Re-merge
    print("\n--- MERGING ---")
    sys.stdout.flush()
    try:
        merge()
    except Exception:
        print("  MERGE FAILED:")
        traceback.print_exc()

    print("\n" + "=" * 50)
    print("  RESULTS")
    print("=" * 50)
    for name, result in results.items():
        print(f"  {name:25s} {result}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
