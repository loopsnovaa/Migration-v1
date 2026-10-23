
import subprocess
import sys
import time
import os

BASE_DIR = "/home/loopsnova/migration-v1/checkpoints"
ITERATIONS = 3

SOURCE_CONTAINER = "counter-source-v2"
DESTINATION_CONTAINER = "counter-destination-v2"
STATE_VOLUME = "counter-state"


def run_command(command, check=True, capture=False):
    print("\nRunning:")
    print(" ".join(command), flush=True)

    result = subprocess.run(
        command,
        text=True,
        capture_output=capture
    )

    if check and result.returncode != 0:
        if capture:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}"
        )

    return result


def container_status(container):
    result = run_command(
        ["docker", "inspect", "-f", "{{.State.Status}}", container],
        capture=True
    )
    return result.stdout.strip()


def get_saved_count():
    # Read the shared volume after the source has stopped.
    result = run_command(
        [
            "docker", "run", "--rm",
            "-v", f"{STATE_VOLUME}:/state",
            "alpine",
            "sh", "-c", "cat /state/count.txt"
        ],
        capture=True
    )

    try:
        return int(result.stdout.strip())
    except ValueError:
        raise RuntimeError(
            "Could not read a valid count from the shared volume."
        )


def write_saved_count(count):
    run_command([
        "docker", "run", "--rm",
        "-v", f"{STATE_VOLUME}:/state",
        "alpine",
        "sh", "-c",
        f"printf '%s' '{count}' > /state/count.txt"
    ])

    actual_count = get_saved_count()

    if actual_count != count:
        raise RuntimeError(
            f"State write verification failed: expected {count}, "
            f"found {actual_count}"
        )

    print(f"Verified shared state: {actual_count}")



def pre_copy(iteration):
    print(
        f"\n============= PRE-COPY ROUND {iteration} =============",
        flush=True
    )

    if container_status(SOURCE_CONTAINER) != "running":
        raise RuntimeError("Source stopped during pre-copy.")

    # Observe the latest persisted state while source continues running.
    count = get_saved_count()
    print(f"Source is running. Latest persisted count: {count}")
    print("This round observes shared application state; "
          "it does not copy process memory.")

    time.sleep(2)


def stop_container_if_running(container):
    status = container_status(container)

    if status == "running":
        run_command(["docker", "stop", container])
    elif status != "exited":
        raise RuntimeError(
            f"{container} has unexpected status: {status}"
        )


def main():
    if len(sys.argv) != 1:
        print("Usage: python3 migration.py")
        sys.exit(1)

    os.makedirs(BASE_DIR, exist_ok=True)

    print("APPLICATION-LEVEL STATE HANDOFF")
    print(f"Source: {SOURCE_CONTAINER}")
    print(f"Destination: {DESTINATION_CONTAINER}")
    print(f"Shared volume: {STATE_VOLUME}")
    print(f"Pre-copy rounds: {ITERATIONS}")

    source_stopped_for_handoff = False

    try:
        # Confirm both containers exist.
        container_status(SOURCE_CONTAINER)
        container_status(DESTINATION_CONTAINER)

        # The destination must not update the shared state during pre-copy.
        stop_container_if_running(DESTINATION_CONTAINER)

        # Ensure the source is running before taking preliminary snapshots.
        if container_status(SOURCE_CONTAINER) != "running":
            run_command(["docker", "start", SOURCE_CONTAINER])

        for iteration in range(1, ITERATIONS + 1):
            pre_copy(iteration)

        print("\n============= FINAL STATE HANDOFF =============")

        # Stop source. Its SIGTERM handler saves the final count.
        run_command(["docker", "stop", SOURCE_CONTAINER])
        source_stopped_for_handoff = True

        print("Source stopped. Reading its final saved count...")
        expected_count = get_saved_count()
        print(f"VERIFICATION: final source count = {expected_count}")

        print("\n============= DESTINATION RESTORE =============")

        # Capture a timestamp so old Docker logs are not mistaken
        # for the startup log from this run.
        start_timestamp = int(time.time())

        run_command(["docker", "start", DESTINATION_CONTAINER])

        # Read only logs created since this startup.
        time.sleep(1)
        result = run_command(
            [
                "docker", "logs",
                "--since", str(start_timestamp),
                DESTINATION_CONTAINER
            ],
            capture=True
        )

        fresh_logs = result.stdout
        print("\nDestination startup logs:")
        print(fresh_logs if fresh_logs else "(No new logs returned)")

        expected_message = f"Resuming from count: {expected_count}"

        if expected_message not in fresh_logs:
            raise RuntimeError(
                "Destination startup count could not be verified. "
                f"Expected: {expected_message!r}. "
                "Source remains stopped; do not start both counters."
            )

        print("\n[MIGRATION VERIFIED]")
        print(f"Source final count: {expected_count}")
        print(f"Destination resumed from: {expected_count}")
        print("Only the destination should now be counting.")
        print(
            "Note: this is application-state handoff through a shared "
            "volume, not CRIU or process-memory migration."
        )

    except Exception as exc:
        print(f"\n[MIGRATION FAILED] {exc}", file=sys.stderr)

        # If destination did not successfully take over, avoid
        # leaving both counters active.
        try:
            if container_status(DESTINATION_CONTAINER) == "running":
                run_command(["docker", "stop", DESTINATION_CONTAINER])

            if source_stopped_for_handoff:
                print("Restarting source for recovery...")
                run_command(["docker", "start", SOURCE_CONTAINER])
        except Exception as recovery_error:
            print(
                f"Recovery also failed: {recovery_error}",
                file=sys.stderr
            )

        sys.exit(1)


if __name__ == "__main__":
    main()
