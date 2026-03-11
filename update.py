"""
Incremental update: fetch new polls from all institutes, then re-merge.
Designed to run daily via GitHub Actions.
"""
import sys
import time
import traceback

from scrapers import elabe, bva, csa, ipsos, opinionway, harris

# Selenium-based scrapers — may fail in CI
SELENIUM_SCRAPERS = []
try:
    from scrapers import odoxa
    SELENIUM_SCRAPERS.append(("ODOXA", odoxa))
except ImportError:
    pass

try:
    from scrapers import ifop
    SELENIUM_SCRAPERS.append(("IFOP", ifop))
except ImportError:
    pass

SCRAPERS = [
    ("ELABE", elabe),
    ("BVA", bva),
    ("CSA", csa),
    ("IPSOS", ipsos),
    ("OPINION WAY", opinionway),
    ("HARRIS", harris),
]


def main():
    print("=" * 50)
    print("  DAILY UPDATE — Incremental scraping")
    print("=" * 50)
    sys.stdout.flush()

    results = {}

    for name, module in SCRAPERS + SELENIUM_SCRAPERS:
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

    # Re-merge all data
    print("\n--- MERGING ---")
    sys.stdout.flush()
    try:
        from merge import merge
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
