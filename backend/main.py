from fastapi import FastAPI, BackgroundTasks, HTTPException  # FastAPI = the web framework; BackgroundTasks = run work after replying
from fastapi.middleware.cors import CORSMiddleware           # lets our React page (a different port) call this server
from pydantic import BaseModel                               # describes and checks the shape of incoming JSON
from core.db import init_db                                  # our database setup
from core.scanner import scan_folder                         # step 1: find photos
from core.hasher import hash_candidates                      # step 2: fingerprint likely duplicates
from core.duplicates import find_duplicate_groups            # step 3: group identical files
import io                                  # lets us build a file in memory instead of on disk
from fastapi.responses import Response     # lets us send raw image bytes back
from PIL import Image, ImageOps            # Pillow: opens and resizes images
from core.db import get_connection         # (you may already have this imported; don't add it twice)
from core.keeper import pick_keeper        # our keeper rule
app = FastAPI()  # create the web app

app.add_middleware(
    CORSMiddleware,                              # without this, the browser blocks React from calling us
    allow_origins=["http://localhost:5173"],     # only allow our React dev server (Vite uses port 5173)
    allow_methods=["*"],                         # allow GET, POST, etc.
    allow_headers=["*"],                         # allow any request headers
)

init_db()  # make sure the database tables exist when the server starts

# A simple shared notice board that the scan job writes to and the status endpoint reads from.
# Fine for one user on one PC. A real multi-user app would need something stronger.
status = {"state": "idle", "phase": "", "message": "", "scanned": 0, "hashed": 0}


class ScanRequest(BaseModel):  # describes the JSON the UI must send to /scan
    folder: str                # the folder path, as text


def run_scan_job(folder):  # the slow work; it runs in the background
    try:
        status.update(state="running", phase="scanning", message="", scanned=0, hashed=0)  # update several keys at once
        status["scanned"] = scan_folder(folder)    # find photos; save how many we found

        status["phase"] = "hashing"                # tell the UI we moved to the next phase
        status["hashed"] = hash_candidates()       # fingerprint the same-size files; save how many

        status.update(state="finished", phase="done")  # all done
    except Exception as e:                         # if anything crashes...
        status.update(state="error", message=str(e))   # ...tell the UI what went wrong, instead of dying silently


@app.post("/scan")  # runs when the UI sends POST to /scan
def start_scan(req: ScanRequest, background_tasks: BackgroundTasks):  # FastAPI fills "req" from the JSON body
    if status["state"] == "running":  # don't allow two scans at once
        raise HTTPException(status_code=409, detail="A scan is already running")  # 409 = "conflict"
    background_tasks.add_task(run_scan_job, req.folder)  # schedule the slow job to run AFTER we reply
    return {"started": True}                              # reply immediately, so the browser never waits


@app.get("/scan/status")  # the UI calls this every second or so
def scan_status():
    return status  # FastAPI turns the dictionary into JSON automatically


@app.get("/duplicates")
def list_duplicates():
    groups = find_duplicate_groups()  # all groups of identical files
    result = []                       # the list we'll send to the UI
    for g in groups:
        keeper = pick_keeper(g)       # the default keeper from our rule
        result.append({"keeper_id": keeper["id"], "files": g})  # send the files AND the suggested keeper
    return {"count": len(result), "groups": result}


@app.get("/thumbnail/{photo_id}")  # {photo_id} is a variable part of the URL
def thumbnail(photo_id: int):      # FastAPI converts it to a number for us
    conn = get_connection()
    row = conn.execute("SELECT path FROM photos WHERE id = ?", (photo_id,)).fetchone()  # look up the path by id
    conn.close()
    if row is None:  # no such photo in the database
        raise HTTPException(status_code=404, detail="Photo not found")  # 404 = "not found"

    try:
        img = Image.open(row["path"])        # open the original photo
        img = ImageOps.exif_transpose(img)   # fix phone photos that would otherwise show sideways
        img.thumbnail((300, 300))            # shrink to fit inside 300x300, keeping the shape
        img = img.convert("RGB")             # JPEG can't store transparency, so convert to plain colors
        buf = io.BytesIO()                   # an in-memory "file"
        img.save(buf, "JPEG", quality=80)    # write the small JPEG into it
        return Response(content=buf.getvalue(), media_type="image/jpeg")  # send the bytes as an image
    except Exception:  # DNG, HEIC without a plugin, corrupt files...
        raise HTTPException(status_code=415, detail="Cannot make a thumbnail for this file type")

# TODO (your task): write POST /apply and POST /undo below.
# Hint: reuse quarantine_duplicates() and undo_all() from core/quarantine.py.