import sqlite3  # built-in Python library for working with SQLite databases
DB_PATH="photos.db"  # name of the database file; it will be created automatically

def get_connection():
    conn=sqlite3.connect(DB_PATH)  # open the database file (creates it if missing)
    conn.row_factory=sqlite3.Row
    return conn

def init_db():
    conn=get_connection() #Open the DB
    conn.execute(
    """
    CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- unique number for each photo, auto-increases
            path TEXT UNIQUE NOT NULL,             -- full file path; UNIQUE means no path is stored twice
            filename TEXT,                         -- just the file name, like IMG_001.jpg
            size_bytes INTEGER,                    -- file size in bytes
            modified_time REAL,                    -- last modified time (as a number)
            file_hash TEXT )
    """
    )
    conn.execute(  # the "manifest": a record of every file we move, so we can undo
        """
        CREATE TABLE IF NOT EXISTS moves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- unique number for each move
            original_path TEXT NOT NULL,           -- where the file was before we moved it
            new_path TEXT NOT NULL,                -- where it is now (inside _duplicates)
            moved_at TEXT,                         -- when we moved it
            undone INTEGER DEFAULT 0               -- 0 = still in quarantine, 1 = already restored
        )
        """
    )
    conn.commit()
    conn.close()



