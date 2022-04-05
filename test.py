import ShellyPy
import time
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("--ip", default="10.20.0.11", help="IP of the switch")
args = parser.parse_args()

device = ShellyPy.Shelly(args.ip)

turn_on = False
while True:
    print("turning switch on" if turn_on else "turning switch off")
    device.relay(0, turn=turn_on)
    turn_on = not turn_on
    time.sleep(2)
