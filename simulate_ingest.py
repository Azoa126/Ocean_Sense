import requests
import time
import random
from datetime import datetime

# URL of your running FastAPI backend
URL = "http://127.0.0.1:8000/ingest"

def fake_point(id_):
    lat = 12 + random.random() * 2   # example latitude range
    lon = 76 + random.random() * 2   # example longitude range
    payload = {
        "id": id_,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "lat": lat,
        "lon": lon,
        "speed": random.random() * 2,
        "heading": random.random() * 360,
        "extra": {"note": "simulated"}
    }
    return payload

if __name__ == "__main__":
    ids = ["tag-A", "tag-B", "tag-C"]
    while True:
        for id_ in ids:
            r = requests.post(URL, json=fake_point(id_))
            print(r.status_code, r.text)
        time.sleep(2)  # send updates every 2 seconds
