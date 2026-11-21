import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import threading

app = FastAPI()

# Our notebook: one entry per device, keyed by its id
monitors = {}


# Describes the JSON we expect in POST /monitors
class MonitorIn(BaseModel):
    id: str
    timeout: int
    alert_email: str


@app.post("/monitors", status_code=201)          # 201 = Created
def create_monitor(data: MonitorIn):
    # The id is already registered: refuse (409 = Conflict)
    if data.id in monitors:
        raise HTTPException(status_code=409, detail="Monitor already exists")

    # Save the monitor, with the time it will "die" if no heartbeat comes
    monitors[data.id] = {
        "timeout": data.timeout,
        "alert_email": data.alert_email,
        "expires_at": time.time() + data.timeout,   # now + timeout
        "status": "active",
    }
    return {"message": f"Monitor {data.id} created"}


@app.post("/monitors/{monitor_id}/heartbeat")    # {monitor_id} is the path parameter
def heartbeat(monitor_id: str):
    # Unknown id: 404 Not Found. We do NOT create a new one here
    if monitor_id not in monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")

    monitor = monitors[monitor_id]
    # Push the "death time" forward: now + the same timeout
    monitor["expires_at"] = time.time() + monitor["timeout"]
    monitor["status"] = "active"
    return {"message": "Heartbeat received"}

def check_monitors():
    while True:
        now = time.time()
        for monitor_id, monitor in list(monitors.items()):
            if monitor["status"] == "active" and now > monitor["expires_at"]:
                monitor["status"] = "down"
                print({"ALERT": f"Device {monitor_id} is down!", "time": now})
        time.sleep(1)

threading.Thread(target=check_monitors, daemon=True).start()