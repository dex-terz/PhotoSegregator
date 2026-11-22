import re  # built-in library for matching patterns in text

# Matches names like "photo - Copy.jpg", "photo (1).jpg", "Copy of photo.jpg".
# re.IGNORECASE means "COPY" and "copy" both match.
COPY_PATTERN = re.compile(r"(- copy|\(\d+\)|^copy of)", re.IGNORECASE)


def looks_like_copy(filename):
    return COPY_PATTERN.search(filename) is not None  # True if the name has a copy-like pattern


def pick_keeper(group, preferred_ids=None):
    # group = list of identical files (each is a dictionary)
    # preferred_ids = ids the user chose to keep (comes from the UI later)

    if preferred_ids:                 # if the user made a choice...
        for f in group:               # ...look through the files in this group
            if f["id"] in preferred_ids:  # if this file is one the user picked
                return f              # the user's choice always wins

    # No user choice, so use the default rule. min() returns the file with the smallest "key".
    # Python compares the tuple left to right, and moves to the next item only on a tie:
    #   1. oldest modified time first
    #   2. then names WITHOUT "copy" in them (False sorts before True)
    #   3. then shorter filename
    #   4. then the path text, so the result is always the same
    return min(
        group,
        key=lambda f: (
            f["modified_time"],
            looks_like_copy(f["filename"]),
            len(f["filename"]),
            f["path"],
        ),
    )