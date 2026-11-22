from pathlib import Path  # modern, easy way to work with file paths
from core.db import get_connection

# Only files ending with these extensions count as photos.
# A set makes checking "is it in here?" very fast.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".gif", ".bmp", ".webp", ".tiff", ".dng"}

def scan_folder(root_folder):
    root = Path(root_folder).resolve()  # turn the text path into a Path object# .resolve() turns "..\test_photos" into the full path like E:\Agents\...

    if not root.is_dir():  # check that the folder really exists
        raise ValueError(f"Not a valid folder: {root_folder}")  # stop with a clear error message

    conn = get_connection()  # open the database
    count = 0                # counter for how many photos we found
    seen = set()  # remembers every photo path we really found on disk this time
    for file_path in root.rglob("*"):  # rglob("*") walks through ALL files in ALL subfolders
        if not file_path.is_file():    # skip it if it's a folder, not a file
            continue                   # "continue" jumps to the next item in the loop

        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:  # get extension (.JPG -> .jpg), check if it's a photo
            continue                                          # not a photo, so skip it

        if "_duplicates" in file_path.parts:  # .parts splits the path into its folder names
            continue                          # skip our own quarantine folder, we don't want to scan it again
        seen.add(str(file_path))  # note down: this file really exists right no
        stats = file_path.stat()  # ask the operating system for info about the file (size, times, etc.)

        conn.execute(  # save this photo in the database
            """
            INSERT INTO photos (path, filename, size_bytes, modified_time)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                filename = excluded.filename,
                file_hash = CASE                                   -- decide what to do with the old fingerprint
                    WHEN photos.size_bytes != excluded.size_bytes  -- if the size changed...
                      OR photos.modified_time != excluded.modified_time  -- ...or the modified time changed
                    THEN NULL                                      -- the file changed, so throw away the old hash
                    ELSE photos.file_hash                          -- otherwise keep it
                END,
                size_bytes = excluded.size_bytes,
                modified_time = excluded.modified_time
            """,
            (str(file_path), file_path.name, stats.st_size, stats.st_mtime),  # the values that replace the ? marks, in order
        )
        count += 1  # one more photo found
    
    
    old_rows = conn.execute("SELECT id, path FROM photos").fetchall()  # everything the database remembers
    for row in old_rows:  # check each remembered file
        in_this_folder = Path(row["path"]).is_relative_to(root)  # does it belong to the folder we just scanned?
        if in_this_folder and row["path"] not in seen:  # it belongs here, but we did NOT find it on disk
            conn.execute("DELETE FROM photos WHERE id = ?", (row["id"],))  # forget it: it's gone
    conn.commit()  # save everything to the database in one go (faster than saving each time)
    conn.close()   # close the connection
    return count   # tell the caller how many photos we found