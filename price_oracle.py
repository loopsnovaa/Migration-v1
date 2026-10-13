import json
import os
import time
from datetime import datetime 

import psutil

class PriceOracle:
  def __init__(self, base_price=10.0):
    self.base_price = base_price
    self.history = []
    self.previous_net = psutil.net_io_counters()
    self.previous_time = time.time()
  def get_system_metrics(self):
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    current_net = psutil.net_io_counters()
    current_time = time.time()
    elapsed = current_time - self.previous_time
    bytes_sent = current_net.bytes_sent - self.previous_net.bytes_sent
    bytes_recv = current_net.bytes_recv - self.previous_net.bytes_recv
    total_bytes = bytes_sent + bytes_recv
    if elapsed > 0:
       network_mbps = (
         total_bytes * 8 / elapsed / 1_000_000
       )
    else:
       network_mbps = 0.0
    self.previous_net = current_net
    self.previous_time = current_time
    return {
       "cpu": round(cpu, 2),
       "ram": round(ram, 2),
       "network_mbps": round(network_mbps, 3)
    }
  
  def calculate_simulated_price(self, cpu, ram):
    utilization = (
         0.6 * (cpu / 100.0) + 0.4 * (ram / 100.0)
    )
    price = self.base_price * (
         1.0 + 0.9 * utilization
    )
    return round(price, 3)

  def generate_sample(self):
   metrics = self.get_system_metrics()
   price = self.calculate_simulated_price(
     metrics["cpu"],
     metrics["ram"]
   )
   sample = {
     "timestamp": datetime.now().isoformat(timespec="seconds"),
     "cpu": metrics["cpu"],
     "ram": metrics["ram"],
     "network_mbps": metrics["network_mbps"],
     "price": price
   }
   self.history.append(sample)
   return sample

  def save_history(self, filename="price_history.json"):
   directory = os.path.dirname(filename)
   if directory: 
     os.makedirs(directory, exist_ok=True)
   with open(filename, "w") as file:
     json.dump(
       self.history,
       file,
       indent=4
     )
def print_sample(sample):
   print("\n" + "=" * 60)
   print(f"Timestamp : {sample['timestamp']}")
   print(f"CPU       : {sample['cpu']:.2f}%")
   print(f"RAM       : {sample['ram']:.2f}%")
   print(f"Network   : {sample['network_mbps']:.3f} Mbps")
   print(f"Price     : ${sample['price']:.3f}/hour")
   print("=" * 60)

if __name__ == "__main__":
   oracle  = PriceOracle(
     base_price=10.0
   )
   print("starting price oracle")
   print("collecting real VM prices...")
   print("press ctrl+c to stop\n")
   try:
     while True:
        sample = oracle.generate_sample()
        print_sample(sample)
        oracle.save_history()
        time.sleep(2)
   except KeyboardInterrupt:
     oracle.save_history()
     print("\nOracle stopped")
     print(
       f"saved {len(oracle.history)} samples "
       f"to price_history.json"
     )

