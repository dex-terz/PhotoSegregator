import sys                                  # It allows your Python program to interact with the Python runtime and system environment.
from core.scanner import scan_folder        # our scanner
from core.db import init_db,get_connection

def main():
    if len(sys.argv) < 2:  # sys.argv is the list of words typed in the terminal; we need the folder path
        print("Usage: python run_scan.py <folder_path>")  # show how to use the script
        return                                            # stop here

    folder = sys.argv[1]  # the second word typed is the folder path

    init_db()                  # make sure the table exists before we use it
    found = scan_folder(folder)  # run the scanner and get the count
    print(f"Scanned {found} photos")

    conn = get_connection()  # open the database again to read the results
    rows = conn.execute("SELECT COUNT(*) AS total, SUM(size_bytes) AS total_size FROM photos").fetchone()  # count rows and add up sizes
    total_mb = (rows["total_size"] or 0) / (1024 * 1024)  # bytes -> MB; "or 0" handles an empty database
    print(f"In database: {rows['total']} photos, {total_mb:.2f} MB")  # .2f means 2 decimal places
    conn.close()
    
main()  # run the main function when the script starts