"""Run all scrapers and merge results."""
import sys
import time
import traceback
from scrapers import ifop, elabe, bva, odoxa, ipsos, opinionway, harris, csa
from merge import merge

SCRAPERS = [
    ("IFOP", ifop.scrape),
    ("ELABE", elabe.scrape),
    ("BVA", bva.scrape),
    ("CSA", csa.scrape),
    ("Harris Interactive", harris.scrape),
    ("OpinionWay", opinionway.scrape),
    ("IPSOS", ipsos.scrape),
    ("ODOXA", odoxa.scrape),
]


def main():
    results = {}
    failed = []

    for name, scrape_fn in SCRAPERS:
        print(f"\n{'='*60}")
        print(f"  SCRAPING: {name}")
        print(f"{'='*60}")
        start = time.time()
        try:
            df = scrape_fn()
            elapsed = time.time() - start
            count = len(df) if df is not None else 0
            results[name] = count
            print(f"  -> {name}: {count} polls in {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  -> {name} FAILED after {elapsed:.1f}s: {e}")
            traceback.print_exc()
            failed.append(name)

    print(f"\n{'='*60}")
    print("  MERGING ALL RESULTS")
    print(f"{'='*60}")
    merge()

    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    for name, count in results.items():
        print(f"  {name:25s} {count:>6} polls")
    if failed:
        print(f"\n  FAILED: {', '.join(failed)}")


if __name__ == "__main__":
    main()
