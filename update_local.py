"""
Local update: runs all scrapers including Selenium ones non-headless.
Designed to run on PC startup via Windows Task Scheduler.
"""
import subprocess
import sys
import time
import traceback
from pathlib import Path

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

    # Re-run NLP to update enriched CSV
    print("\n--- NLP ENRICHMENT ---")
    sys.stdout.flush()
    try:
        from nlp import run_pipeline
        run_pipeline()
    except Exception:
        print("  NLP FAILED:")
        traceback.print_exc()

    # Push to GitHub (triggers Vercel redeploy)
    print("\n--- GIT PUSH ---")
    sys.stdout.flush()
    try:
        repo_dir = Path(__file__).resolve().parent
        git = lambda *args: subprocess.run(
            ["git"] + list(args),
            cwd=repo_dir, capture_output=True, text=True, timeout=60,
        )
        git("add", "data/sondages_france.csv", "data/sondages_enriched.csv", "data/themes.json")
        status = git("diff", "--cached", "--stat")
        if status.stdout.strip():
            today = time.strftime("%Y-%m-%d")
            git("commit", "-m", f"Daily data update {today}")
            push = git("push")
            if push.returncode == 0:
                print("  Pushed to GitHub successfully")
            else:
                print(f"  Push failed: {push.stderr}")
        else:
            print("  No data changes to push")
    except Exception:
        print("  GIT PUSH FAILED:")
        traceback.print_exc()
    sys.stdout.flush()

    print("\n" + "=" * 50)
    print("  RESULTS")
    print("=" * 50)
    for name, result in results.items():
        print(f"  {name:25s} {result}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
