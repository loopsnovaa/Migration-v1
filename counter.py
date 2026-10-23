import os
import signal
import time

STATE_FILE = "/state/count.txt"
count = 0

def load_count():
  try:
     with open(STATE_FILE, "r") as file:
       return int(file.read().strip())
  except (FileNotFoundError, ValueError):
     return 0

def save_count():
  temp_file = STATE_FILE + ".tmp"
  with open(temp_file, "w") as file:
    file.write(str(count))
    file.flush()
    os.fsync(file.fileno())
  os.replace(temp_file, STATE_FILE)

def handle_stop(signum, frame):
  save_count()
  print(f"Saved final count: {count}", flush=True)
  raise SystemExit(0)

signal.signal(signal.SIGTERM, handle_stop)
signal.signal(signal.SIGINT, handle_stop)

count = load_count()
print(f"Resuming from count: {count}", flush = True)

while True:
  count += 1
  print(f"Count: {count}", flush=True)
  save_count()
  time.sleep(1)


