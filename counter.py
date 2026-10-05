import time
import signal
import sys
count = 0
def handle_exit(sig, frame):
   print(f"Stopped at count: {count}", flush=True)
   sys.exit(0)

signal.signal(signal.SIGTERM, handle_exit)
print("Counter starting...", flush=True)
while True:
   count += 1
   print(f"Count: {count}", flush=True)
   time.sleep(1)
