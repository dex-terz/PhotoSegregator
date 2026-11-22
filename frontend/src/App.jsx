import { useState, useEffect } from "react";  // useState = remembers data; useEffect = runs code when something changes

const API = "http://127.0.0.1:8000";  // where our FastAPI server lives

export default function App() {
  const [folder, setFolder] = useState("");                // the folder path typed by the user
  const [status, setStatus] = useState({ state: "idle" }); // latest scan status from the server
  const [groups, setGroups] = useState([]);                // duplicate groups to show

  async function startScan() {  // runs when the Scan button is clicked
    const res = await fetch(`${API}/scan`, {                    // send a POST request to /scan
      method: "POST",
      headers: { "Content-Type": "application/json" },          // tell the server we're sending JSON
      body: JSON.stringify({ folder }),                         // turn {folder: "..."} into JSON text
    });
    if (!res.ok) {                                              // the server said no (e.g. 409 already running)
      const err = await res.json();
      alert(err.detail);                                        // show the server's message
      return;
    }
    setStatus({ state: "running", phase: "scanning" });         // switch the UI into "running" mode
  }

  useEffect(() => {  // while a scan is running, ask the server for status every second
    if (status.state !== "running") return;                     // not running, so do nothing
    const timer = setInterval(async () => {
      const res = await fetch(`${API}/scan/status`);
      setStatus(await res.json());                              // save the new status
    }, 1000);                                                   // 1000 ms = 1 second
    return () => clearInterval(timer);                          // cleanup: stop the timer when status changes
  }, [status.state]);                                           // re-run only when the state word changes

  useEffect(() => {  // when the scan finishes, fetch the duplicate groups
    if (status.state !== "finished") return;
    fetch(`${API}/duplicates`)
      .then((r) => r.json())
      .then((d) => setGroups(d.groups));
  }, [status.state]);

  return (
    <div style={{ padding: 20, fontFamily: "sans-serif" }}>
      <h1>Photo Organizer</h1>

      <input
        value={folder}                                          // the box always shows our saved text
        onChange={(e) => setFolder(e.target.value)}             // update the saved text on every keystroke
        placeholder="E:/Agents/Photo-Segregator/test_photos"
        style={{ width: 400 }}
      />
      <button onClick={startScan} disabled={status.state === "running"}>
        Scan
      </button>

      <p>Status: {status.state} {status.phase}</p>
      {status.state === "error" && <p style={{ color: "red" }}>{status.message}</p>}
      {status.state === "finished" && <p>Found {groups.length} duplicate groups</p>}

      {groups.map((g, i) => (                                   // draw one box per duplicate group
        <div key={i} style={{ border: "1px solid #ccc", padding: 10, margin: "10px 0" }}>
          <h3>Group {i + 1}</h3>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {g.files.map((f) => (                               // draw every file inside the group
              <div key={f.id} style={{ width: 160 }}>
                <img src={`${API}/thumbnail/${f.id}`} width={150} alt={f.filename} />
                <div style={{ fontSize: 12 }}>
                  {f.filename} {f.id === g.keeper_id && "✅ keep"}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}