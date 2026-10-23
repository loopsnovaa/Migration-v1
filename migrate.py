```python
import subprocess
import sys
import os
import time

BASE_DIR = "/home/loopsnova/migration-v1/checkpoints"
ITERATIONS = 3

SOURCE_CONTAINER = "counter-source-v2"
DESTINATION_CONTAINER = "counter-destination-v2"
STATE_VOLUME = "counter-state"


def run_command(command):
    print("\nRunning:")
    print(" ".join(command))

    result = subprocess.run(command)

    if result.returncode != 0:
        print("Command failed.")
        sys.exit(1)

    return result


def clean_checkpoint():
    os.makedirs(BASE_DIR, exist_ok=True)


def pre_dump(iteration, previous_dir=None):
    print(f"\n============= PRE-COPY ROUND {iteration} =============")
    print(f"Round {iteration}: Source container continues running.")
    print(f"Round {iteration}: Counter state is saved in volume '{STATE_VOLUME}'.")
    time.sleep(1)

    print(f"Round {iteration} completed.")
    return STATE_VOLUME


def final_dump(previous_dir):
    print("\n============= FINAL STATE HANDOFF =============")

    print("Stopping source container...")
    run_command(["docker", "stop", SOURCE_CONTAINER])

    print("Source container stopped.")
    print("Final counter state is preserved in the shared volume.")

    return STATE_VOLUME


def main():
    if len(sys.argv) != 1:
        print("Usage:")
        print("python3 migration.py")
        sys.exit(1)

    clean_checkpoint()

    print("APPLICATION-LEVEL MIGRATION")
    print(f"Source: {SOURCE_CONTAINER}")
    print(f"Destination: {DESTINATION_CONTAINER}")
    print(f"Iterations: {ITERATIONS}")

    # Ensure the destination is stopped before migration.
    destination_status = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Status}}",
         DESTINATION_CONTAINER],
        capture_output=True,
        text=True
    )

    if destination_status.returncode != 0:
        print(f"Destination container not found: {DESTINATION_CONTAINER}")
        sys.exit(1)

    if destination_status.stdout.strip() == "running":
        run_command(["docker", "stop", DESTINATION_CONTAINER])

    # Ensure the source is running.
    source_status = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Status}}",
         SOURCE_CONTAINER],
        capture_output=True,
        text=True
    )

    if source_status.returncode != 0:
        print(f"Source container not found: {SOURCE_CONTAINER}")
        sys.exit(1)

    if source_status.stdout.strip() != "running":
        run_command(["docker", "start", SOURCE_CONTAINER])

    previous_dir = None

    for iteration in range(1, ITERATIONS + 1):
        previous_dir = pre_dump(iteration, previous_dir)

    final_dir = final_dump(previous_dir)

    print("\n============= DESTINATION RESTORE =============")
    print("Starting destination container...")

    run_command(["docker", "start", DESTINATION_CONTAINER])

    time.sleep(2)

    print("\nDestination container logs:")
    run_command([
        "docker", "logs", "--tail", "10",
        DESTINATION_CONTAINER
    ])

    print("\n[MIGRATION COMPLETE]")
    print("Application state was handed over using the shared Docker volume.")
    print("The three pre-copy rounds above are demonstration print statements.")
    print("No CRIU checkpointing or process-memory migration was performed.")


if __name__ == "__main__":
    main()
```
