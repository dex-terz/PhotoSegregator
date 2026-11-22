import sys
from core.db import init_db
from core.scanner import scan_folder
from core.hasher import hash_candidates
from core.quarantine import quarantine_duplicates, undo_all


def main():
    if len(sys.argv) < 2:  # we need at least one argument
        print("Usage:\n  python run_quarantine.py <folder>           (dry run)\n"
              "  python run_quarantine.py <folder> --apply    (really move files)\n"
              "  python run_quarantine.py --undo              (restore everything)")
        return

    init_db()  # make sure both tables exist

    if sys.argv[1] == "--undo":
        print(f"Restored {undo_all()} files. Run a scan again to re-add them to the database.")
        return

    folder = sys.argv[1]
    apply = "--apply" in sys.argv  # True only if the user typed --apply

    scan_folder(folder)    # refresh the list of photos
    hash_candidates()      # fingerprint any new same-size files

    result = quarantine_duplicates(folder, dry_run=not apply)

    if not apply:  # dry run: result is the plan
        print(f"DRY RUN: {len(result)} files would be moved\n")
        for item in result:
            print(f"KEEP : {item['keeper']}")
            print(f"MOVE : {item['source']}")
            print(f"   -> {item['destination']}\n")
    else:          # real run: result is a count
        print(f"Moved {result} files to _duplicates")


main()