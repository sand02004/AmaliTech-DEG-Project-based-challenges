import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import threading
import json 

app = FastAPI()

monitors = {}


# Describes the JSON we expect in POST /monitors
class MonitorIn(BaseModel):
    id: str
    timeout: int
    alert_email: str


@app.post("/monitors", status_code=201)          
def create_monitor(data: MonitorIn):
   
    if data.id in monitors:
        raise HTTPException(status_code=409, detail="Monitor already exists")

    # Save the monitor, with the time it will "die" if no heartbeat comes
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
    # Push the "death time" forward: now + the same timeout
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
                print({"ALERT": f"Device {monitor_id} is down!", "time": now})
        time.sleep(1)

    print(json.dumps({"ALERT": f"Device {monitor_id} is down!", "time": now}))

threading.Thread(target=check_monitors, daemon=True).start()