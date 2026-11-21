import json
import threading
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

app = FastAPI()

monitors = {}



@app.get("/health")
def health():
    return {"status": "ok", "monitors": len(monitors)}


class MonitorIn(BaseModel):
    id: str
    timeout: int = Field(gt=0)
    alert_email: EmailStr


@app.post("/monitors", status_code=201)
def create_monitor(data: MonitorIn):
    if data.id in monitors:
        raise HTTPException(status_code=409, detail="Monitor already exists")

    monitors[data.id] = {
        "timeout": data.timeout,
        "alert_email": data.alert_email,
        "expires_at": time.time() + data.timeout,
        "status": "active",
    }
    return {"message": f"Monitor {data.id} created"}


@app.post("/monitors/{monitor_id}/heartbeat")
def heartbeat(monitor_id: str):
    if monitor_id not in monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")

    monitor = monitors[monitor_id]
    # reset the countdown (also un-pauses a paused monitor)
    monitor["expires_at"] = time.time() + monitor["timeout"]
    monitor["status"] = "active"
    return {"message": "Heartbeat received"}


@app.post("/monitors/{monitor_id}/pause")
def pause(monitor_id: str):
    if monitor_id not in monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")

    monitors[monitor_id]["status"] = "paused"
    return {"message": f"Monitor {monitor_id} is paused"}


@app.get("/monitors/{monitor_id}")
def get_monitor(monitor_id: str):
    if monitor_id not in monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")

    monitor = monitors[monitor_id]

    if monitor["status"] == "active":
        seconds_left = max(0, round(monitor["expires_at"] - time.time()))
    else:
        seconds_left = None

    return {
        "id": monitor_id,
        "status": monitor["status"],
        "timeout": monitor["timeout"],
        "seconds_left": seconds_left,
    }


def check_monitors():
    while True:
        now = time.time()
        for monitor_id, monitor in list(monitors.items()):
            if monitor["status"] == "active" and now > monitor["expires_at"]:
                monitor["status"] = "down"
                print(json.dumps({"ALERT": f"Device {monitor_id} is down!", "time": now}), flush=True)
        time.sleep(1)


threading.Thread(target=check_monitors, daemon=True).start()