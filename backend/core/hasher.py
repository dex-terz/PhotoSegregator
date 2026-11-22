import hashlib                      # built-in library that makes fingerprints (hashes) of data
from core.db import get_connection  # our database helper

CHUNK_SIZE = 1024 * 1024  # read files 1 MB at a time, so a huge file never fills up memory


def compute_hash(file_path):
    sha = hashlib.sha256()  # create an empty SHA-256 fingerprint maker

    with open(file_path, "rb") as f:  # open the file in "rb" mode = read raw bytes; "with" closes it automatically
        while True:                        # keep looping until we reach the end of the file
            chunk = f.read(CHUNK_SIZE)     # read the next 1 MB piece
            if not chunk:                  # an empty piece means we reached the end
                break                      # leave the loop
            sha.update(chunk)              # feed this piece into the fingerprint maker

    return sha.hexdigest()  # final fingerprint as a text string (same bytes always give the same text)


def hash_candidates():
    conn = get_connection()  # open the database

    rows = conn.execute(  # find photos that need hashing
        """
        SELECT id, path FROM photos
        WHERE file_hash IS NULL                  -- only photos we haven't hashed yet
        AND size_bytes IN (                      -- AND whose size is shared by at least 2 photos
            SELECT size_bytes FROM photos
            GROUP BY size_bytes                  -- put photos with the same size into groups
            HAVING COUNT(*) > 1                  -- keep only groups that have more than 1 photo
        )
        """
    ).fetchall()  # fetchall gives us every matching row as a list

    hashed = 0  # counter for how many files we hashed

    for row in rows:  # go through each candidate photo
        try:
            file_hash = compute_hash(row["path"])  # calculate its fingerprint
        except OSError:                            # file locked, deleted, or unreadable (OSError covers these)
            print(f"Could not read: {row['path']}")  # tell the user, but don't crash
            continue                               # move on to the next photo

        conn.execute(
            "UPDATE photos SET file_hash = ? WHERE id = ?",  # save the fingerprint on that photo's row
            (file_hash, row["id"]),                          # values for the two ? marks
        )
        hashed += 1  # one more done

    conn.commit()  # save all updates at once
    conn.close()   # close the database
    return hashed  # tell the caller how many we hashed