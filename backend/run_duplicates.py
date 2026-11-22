import sys                                    # to read the folder path from the terminal
from core.db import init_db                   # database setup
from core.scanner import scan_folder          # step 1: find photos
from core.hasher import hash_candidates       # step 2: fingerprint likely duplicates
from core.duplicates import find_duplicate_groups  # step 3: group identical fingerprints


def main():
    if len(sys.argv) < 2:  # need a folder path
        print("Usage: python run_duplicates.py <folder_path>")
        return

    init_db()                          # make sure the table exists
    found = scan_folder(sys.argv[1])   # scan the folder
    print(f"Scanned {found} photos")

    hashed = hash_candidates()         # hash only the photos that share a size
    print(f"Hashed {hashed} photos (same-size candidates only)")

    groups = find_duplicate_groups()   # build the duplicate groups
    print(f"Found {len(groups)} duplicate groups\n")

    for i, group in enumerate(groups, start=1):  # enumerate gives us 1, 2, 3... along with each group
        print(f"Group {i}:")
        for f in group:                          # print every file in this group
            print(f"   {f['path']}  ({f['size_bytes']} bytes)")


main()  # run when the script starts