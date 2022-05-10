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
parser.add_argument("--on", action="store_true")
parser.add_argument("--off", action="store_true")
args = parser.parse_args()

#
# To test:
# - connects to wifi if wifi reboots?
# - connects to wifi if wifi is unavailable when it boots and comes online later
# - is it up and available long term?
#
# Results
# - power reading have a couple of seconds latency (noticeable from 0 to power)
# - first test run in db, ended 2022-05-08
# - second test run in db, 2022-05-10, reconnect test to the rebooted device, it reconnected
# - third test run in db, 2022-05-10, reconnect test to the rebooted device (but wifi down when booted), it reconnected
# - after 10 days the wlan connection died and did not reconnect, came back after unplugging and plugging the device,
#   it continued to be on
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
        self.url = "http://" + ip
        self.auth = HTTPBasicAuth(username, password)

    def post(self, path):
        response = post(self.url + path, auth=self.auth, timeout=2)
        if not response.ok:
            raise Exception(str(response))
        return response.json()

    def power(self, enabled=False):
        return self.post("/relay/0?turn=" + ('on' if enabled else 'off'))
    
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


device = Shelly(args.ip, "admin", args.password)

if args.on:
    device.power(enabled=True)
    exit(0)

if args.off:
    device.power(enabled=False)
    exit(0)


db = Db(args.db)


last = None
while True:
    try:
        timestamp, latency, power, total, enabled = device.metrics()
        delta = (timestamp - (last or timestamp)).total_seconds()
        db.insert(timestamp, latency, delta, enabled, power, total)
        print(
            "%s latency=%f delta=%f enabled=%s power=%f total=%f" %
            (timestamp.isoformat(), latency, delta, enabled, power, total)
        )
        last = timestamp
    except Exception as e:
        print("failed to fetch", str(e))
        
    sleep(1)
