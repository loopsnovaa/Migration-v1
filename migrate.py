import subprocess
import sys
import os
import shutil

BASE_DIR = "/home/loopsnova/migration-v1/checkpoints"
ITERATIONS = 3

def run_criu(command):
  print("\nRunning:")
  print(" ".join(command))
  result = subprocess.run(command)
  if result.returncode != 0:
    print("CRIU command failed.")
    sys.exit(1)

def clean_checkpoint():
  if os.path.exists(BASE_DIR):
    shutil.rmtree(BASE_DIR)
  os.makedirs(BASE_DIR)

def pre_dump(pid, iteration, previous_dir=None):
  current_dir = os.path.join(BASE_DIR, f"iter{iteration}")
  os.makedirs(current_dir)
  command = [
    "sudo",
    "criu",
    "pre-dump",
    "-t",
    str(pid),
    "-D",
    current_dir,
    "--shell-job",
    "--track-mem",
    "--log-file",
    os.path.join(current_dir, "predump.log"),
    "-v4"
  ]

  if previous_dir:
    command.extend([
      "--prev-images-dir",
      previous_dir
    ])
  print(f"\n=============PRE-DUMP {iteration}=============")
  run_criu(command)
  print(f"Pre-dump {iteration} completed")
  print(f"checkpoint stored at: {current_dir}")
  return current_dir

def final_dump(pid, previous_dir):
  final_dir = os.path.join(BASE_DIR, "final")
  os.makedirs(final_dir, exist_ok=True)
  print("\n=============FINAL DUMP===============")
  command = [
    "sudo",
    "criu",
    "dump",
    "-t",
    str(pid),
    "-D",
    final_dir,
    "--shell-job",
    "--track-mem",
    "--prev-images-dir",
    previous_dir,
    "--log-file",
    os.path.join(final_dir, "dump.log"),
    "-v4"
  ]
  run_criu(command)

  print("Final CRIU dump completed")
  print(f"Final checkpoint: {final_dir}")
  return final_dir  
def main():
  if len(sys.argv) != 2:
    print("Usage:")
    print("python3 migrate.py <PID>")
    sys.exit(1)
  pid = sys.argv[1]
  clean_checkpoint()
  
  print("ITERATIVE PRE COPY CONTROLLER")
  print(f"Target PID:{pid}")
  print(f"Iterations: {ITERATIONS}")
  previous_dir = None
  for iteration in range(1, ITERATIONS +1):
    previous_dir = pre_dump(
      pid,
      iteration,
      previous_dir
    )
    if iteration < ITERATIONS:
      print("\nApplication continues running...")
      subprocess.run(["sleep","3"])
  #final_dump(pid, previous_dir)
  print("PRE-COPY COMPLETE")
  print(f"Checkpoint are in: {BASE_DIR}")
  final_dir = final_dump(pid, previous_dir)
  print("\n[RESTORE] restoring checkpoint...")
  restore_cmd = [
    "sudo", "criu", "restore",
    "-D", final_dir,
    "--shell_job",
    "-d",
    "--log-file", os.path.join(final_dir, "restore.log"),
    "-v4"
  ]
  result = subprocess.run(restore_cmd)
  if result.returncode == 0:
    print("[SUCCESS} MIgration successful!")
    print("[INFO] restored process should continue from its saved count")
  else:
    print("[ERROR] MIgration restore failed")
    print(f"[INFO] check {os.path.join(final_dir, 'restore.log')}")

if __name__ == "__main__":
  main()

