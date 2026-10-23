
import subprocess
import sys
import time
import os

BASE_DIR = "/home/loopsnova/migration-v1/checkpoints"
ITERATIONS = 3

SOURCE_CONTAINER = "counter-source-v2"
DESTINATION_CONTAINER = "counter-destination-v2"
STATE_VOLUME = "counter-state"


def run_command(command, capture=False, check=True):
    print("\nRunning:", " ".join(command), flush=True)

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
        f"printf '%s\\n' '{count}' > /state/count.txt"
    ])

    actual = get_saved_count()
    if actual != count:
        raise RuntimeError(
            f"State verification failed: expected {count}, got {actual}"
        )

    print(f"Verified final state in shared volume: {actual}")


def pre_copy(iteration):
    print(
        f"\n============= PRE-COPY ROUND {iteration} =============",
        flush=True
    )

    if container_status(SOURCE_CONTAINER) != "running":
        raise RuntimeError("Source is not running during pre-copy.")

    count = get_saved_count()
    print(f"Latest persisted application count: {count}")
    print("This is an application-state observation, not memory pre-copy.")
    time.sleep(2)


def stop_if_running(container):
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

    source_stopped = False
    destination_started = False

    try:
        # Validate both containers exist.
        container_status(SOURCE_CONTAINER)
        container_status(DESTINATION_CONTAINER)

        # Keep destination inactive while source is running.
        stop_if_running(DESTINATION_CONTAINER)

        if container_status(SOURCE_CONTAINER) != "running":
            run_command(["docker", "start", SOURCE_CONTAINER])

        # Preliminary rounds: source continues counting.
        for iteration in range(1, ITERATIONS + 1):
            pre_copy(iteration)

        print("\n============= FINAL STATE HANDOFF =============")

        # Stop source so its SIGTERM handler saves the final count.
        run_command(["docker", "stop", SOURCE_CONTAINER])
        source_stopped = True

        expected_count = get_saved_count()
        print(f"Source final saved count: {expected_count}")

        # Explicitly persist and verify the handoff value.
        write_saved_count(expected_count)

        print("\n============= DESTINATION RESTORE =============")

        # Remove ambiguity from previous logs by recording a timestamp.
        start_timestamp = time.time()

        run_command(["docker", "start", DESTINATION_CONTAINER])
        destination_started = True

        # Wait briefly for the process to emit its startup message.
        time.sleep(2)

        result = run_command(
            [
                "docker", "logs",
                "--since", str(start_timestamp),
                DESTINATION_CONTAINER
            ],
            capture=True
        )

        fresh_logs = result.stdout
        print("\nDestination logs from this startup:")
        print(fresh_logs if fresh_logs else "(No new stdout logs returned)")

        expected_message = f"Resuming from count: {expected_count}"

        if expected_message not in fresh_logs:
            raise RuntimeError(
                f"Could not verify destination startup count. "
                f"Expected exact message: {expected_message!r}"
            )

        print("\n[MIGRATION VERIFIED]")
        print(f"Source final count: {expected_count}")
        print(f"Destination resumed from: {expected_count}")
        print("Destination is now the active counter.")
        print(
            "This is application-state handoff using a shared Docker "
            "volume. It is not CRIU or process-memory migration."
        )

    except Exception as exc:
        print(f"\n[MIGRATION FAILED] {exc}", file=sys.stderr)

        # Avoid leaving both counters active after a failed handoff.
        try:
            if destination_started:
                stop_if_running(DESTINATION_CONTAINER)

            if source_stopped:
                print("Restoring source service for recovery...")
                if container_status(SOURCE_CONTAINER) != "running":
                    run_command(["docker", "start", SOURCE_CONTAINER])
        except Exception as recovery_error:
            print(f"Recovery failed: {recovery_error}", file=sys.stderr)

        sys.exit(1)


if __name__ == "__main__":
    main()
