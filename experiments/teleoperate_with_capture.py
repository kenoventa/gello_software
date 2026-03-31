"""
Teleoperation with automatic pose capture.

Wraps run_env.py with automatic START/STOP pose capture.
Saves configs to ../config_pose/ folder with one session file per run.

Usage (replaces run_env.py):
    python teleoperate_with_capture.py --bimanual --agent=gello --use-relative-mode [other args]
    
Requires:
    - launch_nodes.py already running (same as before)
    - All same arguments as run_env.py work here too
"""

import json
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directory to path so we can import gello modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.pose_capture_helper import PoseCaptureManager


def create_session_id() -> str:
    """Create unique session ID from current timestamp."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_session_data(session_id: str, robot_type: str) -> Dict[str, Any]:
    """Create empty session data structure."""
    now = datetime.now(timezone.utc)
    return {
        "session_id": session_id,
        "robot_type": robot_type,
        "timestamp_start": now.isoformat(),
        "timestamp_start_unix": now.timestamp(),
        "timestamp_stop": None,
        "timestamp_stop_unix": None,
        "config_start": None,
        "config_stop": None,
    }


def save_session(session_data: Dict[str, Any], config_dir: str = "config_pose") -> str:
    """Save session to JSON file. Returns path to saved file."""
    config_path = Path(__file__).parent.parent / config_dir
    config_path.mkdir(parents=True, exist_ok=True)

    session_id = session_data["session_id"]
    file_path = config_path / f"session_{session_id}.json"

    with open(file_path, "w") as f:
        json.dump(session_data, f, indent=2)

    return str(file_path)


def capture_teleoperation_configs(
    robot_type: str = "bimanual_ur",
    bimanual: bool = True,
    hostname: str = "127.0.0.1",
    robot_port: int = 6001,
    gello_left_port: Optional[str] = None,
    gello_right_port: Optional[str] = None,
    gello_port: Optional[str] = None,
    use_relative_mode: bool = False,
    verbose: bool = False,
    save_pose: bool = False,
    to_degrees: bool = False,
) -> Dict[str, Any]:
    """Initialize manager and capture poses from all devices."""
    try:
        manager = PoseCaptureManager(config_dir="config_pose")
        pose_data = manager.capture_pose(
            robot_type=robot_type,
            robot_port=robot_port,
            hostname=hostname,
            gello_port=gello_port,
            gello_left_port=gello_left_port,
            gello_right_port=gello_right_port,
        )

        if pose_data is None:
            raise RuntimeError("Failed to capture pose")

        # Convert to config format (robot_left, robot_right, gello_left, gello_right)
        config = {
            "robot_left": pose_data.get("robot_left"),
            "robot_right": pose_data.get("robot_right"),
            "gello_left": pose_data.get("gello_left"),
            "gello_right": pose_data.get("gello_right"),
        }

        return config
    except Exception as e:
        print(f"\n❌ Failed to capture configuration: {e}")
        raise


def main():
    """Main function: Capture START → Run teleoperation → Capture STOP."""

    # Parse all command-line arguments for run_env.py
    # We'll extract what we need and pass the rest through
    argv = sys.argv[1:]

    # Extract pose capture relevant args
    robot_type = "bimanual_ur"
    bimanual = False
    hostname = "127.0.0.1"
    robot_port = 6001
    gello_port = None
    gello_left_port = None
    gello_right_port = None
    use_relative_mode = False
    verbose = False
    save_pose = False

    # Port mappings for UR arms
    UR_PORTS = {
        "right": "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0",
        "left": "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0",
    }

    # Flags to filter out from argv before passing to run_env.py
    flags_to_remove = set()

    # Simple argument parsing for our needs
    for i, arg in enumerate(argv):
        if arg == "--robot-type" and i + 1 < len(argv):
            robot_type = argv[i + 1]
        elif arg.startswith("--robot-type="):
            robot_type = arg.split("=")[1]
        elif arg == "--bimanual":
            bimanual = True
        elif arg == "--hostname" and i + 1 < len(argv):
            hostname = argv[i + 1]
        elif arg.startswith("--hostname="):
            hostname = arg.split("=")[1]
        elif arg == "--robot-port" and i + 1 < len(argv):
            robot_port = int(argv[i + 1])
        elif arg.startswith("--robot-port="):
            robot_port = int(arg.split("=")[1])
        elif arg == "--gello-port" and i + 1 < len(argv):
            gello_port = argv[i + 1]
        elif arg.startswith("--gello-port="):
            gello_port = arg.split("=")[1]
        elif arg == "--gello-left-port" and i + 1 < len(argv):
            gello_left_port = argv[i + 1]
        elif arg.startswith("--gello-left-port="):
            gello_left_port = arg.split("=")[1]
        elif arg == "--gello-right-port" and i + 1 < len(argv):
            gello_right_port = argv[i + 1]
        elif arg.startswith("--gello-right-port="):
            gello_right_port = arg.split("=")[1]
        elif arg == "--ur-left":
            gello_port = UR_PORTS["left"]
            flags_to_remove.add(i)
        elif arg == "--ur-right":
            gello_port = UR_PORTS["right"]
            flags_to_remove.add(i)
        elif arg == "--use-relative-mode":
            use_relative_mode = True
        elif arg == "--verbose":
            verbose = True
        elif arg == "-v":
            verbose = True
        elif arg == "--save-pose":
            save_pose = True

    # Filter out teleoperate-specific flags before passing to run_env.py
    argv_filtered = [
        arg
        for i, arg in enumerate(argv)
        if i not in flags_to_remove and arg != "--save-pose"
    ]

    # Add back gello_port to argv_filtered if it was set from --ur-left or --ur-right
    if gello_port is not None and "--gello-port" not in argv_filtered:
        # Check if gello_port was set from --ur-left/--ur-right (not from explicit --gello-port arg)
        has_explicit_gello_port = any("--gello-port" in arg for arg in argv)
        if not has_explicit_gello_port:
            argv_filtered.extend(["--gello-port", gello_port])

    # Infer robot type if bimanual
    if bimanual:
        robot_type = "bimanual_ur"

    print("\n" + "=" * 80)
    print("TELEOPERATION WITH AUTOMATIC POSE CAPTURE")
    print("=" * 80)

    # Create session
    session_id = create_session_id()
    session_data = create_session_data(session_id, robot_type)

    print(f"\n[1/3] Capturing START configuration...")
    print(f"      Session ID: {session_id}")
    print(f"      Robot type: {robot_type}")
    print(f"      GELLO ports:")
    if bimanual:
        print(
            f"        - Left:  {gello_left_port if gello_left_port else '(not provided)'}"
        )
        print(
            f"        - Right: {gello_right_port if gello_right_port else '(not provided)'}"
        )
    else:
        print(f"        - Single: {gello_port if gello_port else '(not provided)'}")

    try:
        # Capture START config
        config_start = capture_teleoperation_configs(
            robot_type=robot_type,
            bimanual=bimanual,
            hostname=hostname,
            robot_port=robot_port,
            gello_left_port=gello_left_port,
            gello_right_port=gello_right_port,
            gello_port=gello_port,
            use_relative_mode=use_relative_mode,
            verbose=verbose,
            to_degrees=True,
        )

        session_data["config_start"] = config_start

        if verbose:
            print(f"      ✓ START config captured")
            for device, joints in config_start.items():
                if joints:
                    print(f"        - {device}: {len(joints)} joints")
        else:
            print(f"      ✓ START config captured")

    except Exception as e:
        print(f"\n❌ Failed to capture START config: {e}")
        sys.exit(1)

    # Save session before starting teleoperation, only if we plan to save the pose
    if save_pose:
        session_file = save_session(session_data)
        print(f"      Session file: {session_file}")
    else:
        session_file = None

    print(f"\n[2/3] Starting teleoperation...")
    print(f"      Running: python run_env.py {' '.join(argv_filtered)}")
    print(f"      Press Ctrl+C to stop and capture STOP config\n")

    # Spawn run_env.py subprocess
    run_env_path = Path(__file__).parent / "run_env.py"
    process = subprocess.Popen(
        [sys.executable, str(run_env_path)] + argv_filtered,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    def handle_sigint(signum, frame):
        """Handle Ctrl+C gracefully."""
        print("\n\n[3/3] Teleoperation stopped by user")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    signal.signal(signal.SIGINT, handle_sigint)

    # Wait for subprocess to finish
    return_code = process.wait()

    if save_pose:
        # Capture STOP
        print(f"      Capturing STOP configuration...")
        try:
            config_stop = capture_teleoperation_configs(
                robot_type=robot_type,
                bimanual=bimanual,
                hostname=hostname,
                robot_port=robot_port,
                gello_port=gello_port,
                gello_left_port=gello_left_port,
                gello_right_port=gello_right_port,
                use_relative_mode=use_relative_mode,
                verbose=False,  # Keep quiet
                to_degrees=True,
            )

            session_data["config_stop"] = config_stop

            # Update timestamps
            now = datetime.now(timezone.utc)
            session_data["timestamp_stop"] = now.isoformat()
            session_data["timestamp_stop_unix"] = now.timestamp()

            if verbose:
                print(f"      ✓ STOP config captured")
                for device, joints in config_stop.items():
                    if joints:
                        print(f"        - {device}: {len(joints)} joints")
            else:
                print(f"      ✓ STOP config captured")

        except Exception as e:
            print(f"      ⚠ Failed to capture STOP config: {e}")
            print(f"      (You can capture it later if needed)")

        # Update session file with STOP config
        save_session(session_data)
    else:
        print(f"\n[3/3] Skipping STOP configuration capture (--save-pose not used)")

    print(f"\n" + "=" * 80)
    print(f"✓ TELEOPERATION COMPLETE")
    print("=" * 80)
    print(f"Session ID:     {session_id}")
    if session_file:
        print(f"Session file:   {session_file}")
    else:
        print(f"Session file:   (not saved, use --save-pose to enable)")
    print(f"Both configs saved in single file")
    print()

    sys.exit(return_code)


if __name__ == "__main__":
    main()
