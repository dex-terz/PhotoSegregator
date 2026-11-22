import shutil                       # built-in library for moving files
from datetime import datetime       # to record when each move happened
from pathlib import Path            # easy path handling
from core.db import get_connection
from core.duplicates import find_duplicate_groups
from core.keeper import pick_keeper

QUARANTINE_NAME = "_duplicates"  # folder name where unwanted copies go (the scanner skips this name)


def unique_destination(folder, filename, taken):
    # taken = names we've already planned in this run (they don't exist on disk yet in a dry run)
    original = Path(filename)                    # lets us split "photo.jpg" into "photo" and ".jpg"
    dest = folder / filename                     # first try: the same name D:/Photos/photo.jpg
    counter = 1                                  # for photo_1, photo_2, ...
    while dest.exists() or dest in taken:        # name already used on disk or planned?
        dest = folder / f"{original.stem}_{counter}{original.suffix}"  # try photo_1.jpg, then photo_2.jpg...
        counter += 1                             # next number if this one is taken too
    taken.add(dest)                              # remember we've used this name
    return dest
# suppose we want to save photo.jpg, but a file with that name already exists. The function automatically tries:
# - photo.jpg
# - photo_1.jpg
# - photo_2.jpg
# - photo_3.jpg

def quarantine_duplicates(root_folder, preferred_ids=None, dry_run=True):
    quarantine = Path(root_folder).resolve() / QUARANTINE_NAME  # the _duplicates folder inside the scanned folder
    groups = find_duplicate_groups()  # all groups of identical files
    taken = set()                     # names planned so far
    plan = []                         # list of moves we intend to make

    for group in groups: 
        keeper = pick_keeper(group, preferred_ids)        # decide which file stays
        for f in group:                                   # look at every file in the group
            if f["id"] == keeper["id"]:                   # this one is the keeper
                continue                                  # leave it alone
            dest = unique_destination(quarantine, f["filename"], taken)  # safe name inside _duplicates
            plan.append({
                "id": f["id"],
                "source": f["path"],
                "destination": str(dest),
                "keeper": keeper["path"],
            })

    if dry_run:      # dry run = only show the plan, touch nothing
        return plan

    quarantine.mkdir(exist_ok=True)  # create _duplicates if it doesn't exist (no error if it does)
    conn = get_connection()
    moved = 0                        # counter of files actually moved

    for item in plan:
        try:
            shutil.move(item["source"], item["destination"])  # the actual move
        except OSError as e:                                  # locked, missing, no permission, etc.
            print(f"Could not move {item['source']}: {e}")    # report it but keep going
            continue

        conn.execute(  # write the move into the manifest so we can undo it
            "INSERT INTO moves (original_path, new_path, moved_at) VALUES (?, ?, ?)",
            (item["source"], item["destination"], datetime.now().isoformat()),
        )
        conn.execute("DELETE FROM photos WHERE id = ?", (item["id"],))  # it's no longer in its old place
        conn.commit()  # save after EVERY move, so the manifest always matches what's on disk
        moved += 1

    conn.close()
    return moved


def undo_all():
    conn = get_connection()
    rows = conn.execute(  # all moves not yet undone, newest first
        "SELECT id, original_path, new_path FROM moves WHERE undone = 0 ORDER BY id DESC"
    ).fetchall()

    restored = 0
    for row in rows:
        original = Path(row["original_path"])  # where the file used to be

        if original.exists():  # something already sits there, so don't overwrite it
            print(f"Skipped (a file already exists there): {original}")
            continue

        original.parent.mkdir(parents=True, exist_ok=True)  # recreate the folder if it was removed
        try:
            shutil.move(row["new_path"], str(original))     # move it back
        except OSError as e:
            print(f"Could not restore {original}: {e}")
            continue

        conn.execute("UPDATE moves SET undone = 1 WHERE id = ?", (row["id"],))  # mark as restored
        conn.commit()
        restored += 1

    conn.close()
    return restored