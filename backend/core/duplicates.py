from core.db import get_connection  # our database helper


def find_duplicate_groups():
    conn = get_connection()  # open the database

    hash_rows = conn.execute(  # find fingerprints that appear more than once
        """
        SELECT file_hash, COUNT(*) AS n FROM photos
        WHERE file_hash IS NOT NULL      -- ignore photos we never hashed
        GROUP BY file_hash               -- group photos that share a fingerprint
        HAVING n > 1                     -- keep only groups with 2+ photos = duplicates
        """
    ).fetchall()

    groups = []  # will hold one list of files per duplicate group

    for hash_row in hash_rows:  # go through each duplicate fingerprint
        files = conn.execute(   # get all photos having this fingerprint
            "SELECT id, path, filename, size_bytes, modified_time FROM photos WHERE file_hash = ?",
            (hash_row["file_hash"],),  # the comma makes it a tuple, which SQLite requires
        ).fetchall()
        groups.append([dict(f) for f in files])  # turn each row into a normal dictionary and add the group

    conn.close()    # close the database
    return groups   # list of groups, each group is a list of identical files