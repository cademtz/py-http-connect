from threading import Thread
from client import Client
import traceback
import argparse
import asyncio
import time
import sys

RETRY_SECONDS = 5

parser = argparse.ArgumentParser()
parser.add_argument('-sh', '--src-host', type=str, help='Address of master server, the source of requests')
parser.add_argument('-sp', '--src-port', type=int, help='Port of master server to connect to')
parser.add_argument('-dp', '--dst-port', type=int, help='Local port, destination for HTTP requests from master server')

args = parser.parse_args(sys.argv[1:])

event_loop = asyncio.new_event_loop()
def event_loop_exec():
    asyncio.set_event_loop(event_loop)
    event_loop.run_forever()
Thread(target=event_loop_exec, daemon=True).start()

while True:
    try:
        with Client(args.dst_port) as client:
            client.connect((args.src_host, args.src_port))
            print('Connected')
            client.read_loop()
    except Exception as e:
        print(f'Exception {e}')
        print(traceback.format_exc())
        print(f'Retrying connection in {RETRY_SECONDS}s')
        time.sleep(RETRY_SECONDS)