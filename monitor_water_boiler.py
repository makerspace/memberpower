from argparse import ArgumentParser
from datetime import datetime
from time import sleep, perf_counter

from requests import post
from requests.auth import HTTPBasicAuth
import sqlite3

parser = ArgumentParser()
parser.add_argument("--ip", default="10.20.0.11")
parser.add_argument("--password")
parser.add_argument("--db", default="metrics.db")
args = parser.parse_args()

#
# To test:
# - connects to wifi if wifi reboots?
# - connects to wifi if wifi is unavailable when it boots and comes online later
# - is it up and available long term?
#


class Db:
    
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            timestamp datetime,
            latency float,
            delta float,
            enabled integer,
            power float,
            total float
        )""")
        self.db.commit()

    def insert(self, timestamp, latency, delta, enabled, power, total):
        self.db.execute(
            "INSERT INTO metrics (timestamp, latency, delta, enabled, power, total) VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, latency, delta, enabled, power, total),
        )
        self.db.commit()


class Shelly:
    
    def __init__(self, ip="10.22.0.11", username="admin", password=""):
        self.url = f"http://{ip}"
        self.auth = HTTPBasicAuth(username, password)

    def post(self, path):
        response = post(f"{self.url}{path}", auth=self.auth, timeout=2)
        if not response.ok:
            raise Exception(str(response))
        return response.json()

    def power(self, enabled=False):
        return self.post(f"/relay/0?turn={'on' if enabled else 'off'}")
    
    def reboot(self):
        return self.post("/reboot")

    def metrics(self):
        start = perf_counter()
        status = self.post("/status")
        return (
            datetime.utcnow(),
            perf_counter() - start, status["meters"][0]["power"],
            status["meters"][0]["total"],
            status["relays"][0]["ison"],
        )


db = Db(args.db)
device = Shelly(args.ip, "admin", args.password)

last = None
while True:
    try:
        timestamp, latency, power, total, enabled = device.metrics()
        delta = (timestamp - (last or timestamp)).total_seconds()
        db.insert(timestamp, latency, delta, enabled, power, total)
        print(f"{timestamp.isoformat()} {latency=} {delta=} {enabled=} {power=} {total=}")
        last = timestamp
    except Exception as e:
        print(f"failed to fetch {e}")
        
    sleep(1)