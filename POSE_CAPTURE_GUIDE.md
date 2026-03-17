# Pose Capture System - Teleoperation Integration Guide

Automatic pose capture system for teleoperation start and stop configurations.

## Overview

This system provides two approaches for pose capture:

1. **Automatic with Teleoperation Wrapper** ⭐ (Recommended) - Automatically capture start/stop in one session file
2. **Manual Capture** - Record poses at any time for fine-grained control

## Storage Format - Single Session File

All poses are stored in `/config_pose/` folder in **one session file per teleoperation run**:

```json
{
  "session_id": "20260316_142345",
  "robot_type": "bimanual_ur",
  "timestamp_start": "2026-03-16T14:23:45.123456",
  "timestamp_start_unix": 1742217825.123456,
  "timestamp_stop": "2026-03-16T14:35:12.987654",
  "timestamp_stop_unix": 1742218512.987654,
  "config_start": {
    "robot_left": [-0.073, -1.547, 2.424, -0.838, -0.605, 1.254, 0.012],
    "robot_right": [0.012, -1.712, -1.809, 2.359, -1.871, -1.471, -0.660],
    "gello_left": [0.545, -1.580, 2.540, -0.831, -0.663, -1.574, 0.020],
    "gello_right": [-2.057, -1.914, 2.537, -2.171, -1.476, -0.632, 0.0]
  },
  "config_stop": {
    "robot_left": [-0.074, -1.548, 2.425, -0.839, -0.606, 1.255, 0.013],
    "robot_right": [0.013, -1.713, -1.810, 2.360, -1.872, -1.472, -0.661],
    "gello_left": [0.546, -1.581, 2.541, -0.832, -0.664, -1.575, 0.021],
    "gello_right": [-2.058, -1.915, 2.538, -2.172, -1.477, -0.633, 0.001]
  }
}
```

**Fields:**
- `session_id` - Unique ID (YYYYMMDD_HHMMSS format)
- `robot_type` - Type of robot used
- `timestamp_start` - ISO format timestamp when capture started
- `timestamp_start_unix` - Unix timestamp when capture started
- `timestamp_stop` - ISO format timestamp when capture ended
- `timestamp_stop_unix` - Unix timestamp when capture ended
- `config_start` - Starting configuration:
  - `robot_left` - Left robot joint positions (radians)
  - `robot_right` - Right robot joint positions (radians)
  - `gello_left` - Left GELLO joint positions (radians)
  - `gello_right` - Right GELLO joint positions (radians)
- `config_stop` - Final configuration (same structure as config_start)

## Usage

### Option 1: Automatic Capture with Teleoperation Wrapper (RECOMMENDED) ⭐

**This is the easiest and recommended way.** Run teleoperation with automatic start/stop capture in one session file.

#### Bimanual Setup

```bash
python3 scripts/run_with_pose_capture.py \
  --robot-ip-left=192.168.1.20 \
  --robot-ip-right=192.168.1.10 \
  --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
  --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0
```

#### Single-Arm Setup

```bash
python3 scripts/run_with_pose_capture.py \
  --single-arm \
  --robot-ip=192.168.1.20 \
  --gello-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0
```

**Workflow:**
1. ✓ Script automatically captures START config on startup
2. ✓ Run teleoperation as normal
3. ✓ Press Ctrl+C to stop
4. ✓ Script automatically captures STOP config
5. ✓ Both configs saved in one session file: `config_pose/session_YYYYMMDD_HHMMSS.json`

**Output:**
```
================================================================================
TELEOPERATION WITH AUTO POSE CAPTURE
================================================================================

[1/3] Capturing START configuration...
...
✓ START config captured
  Session ID: 20260316_142345
  File: session_20260316_142345.json

[2/3] Starting teleoperation...
...
Press Ctrl+C to stop teleoperation...

[3/3] Teleoperation stopped by user
...
✓ STOP config captured

================================================================================
✓ SESSION COMPLETE
================================================================================

Session ID: 20260316_142345
File: /path/to/config_pose/session_20260316_142345.json

Both START and STOP configs saved in: session_20260316_142345.json
```

### Option 2: Manual Capture (Fine-grained Control)

#### Create New Session with Start Config

```bash
python3 scripts/capture_pose.py \
  --robot=bimanual_ur \
  --robot-ip-left=192.168.1.20 \
  --robot-ip-right=192.168.1.10 \
  --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
  --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0 \
  --capture-type=start \
  --verbose
```

#### Update Existing Session with Stop Config

```bash
python3 scripts/capture_pose.py \
  --robot=bimanual_ur \
  --robot-ip-left=192.168.1.20 \
  --robot-ip-right=192.168.1.10 \
  --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
  --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0 \
  --capture-type=stop \
  --session-id=20260316_142345 \
  --verbose
```

## Viewing Saved Poses

To view all saved sessions:

```bash
# List all sessions (brief)
python3 scripts/list_poses.py

# List with full details
python3 scripts/list_poses.py --verbose
```

Output (brief):
```
================================================================================
SAVED POSES IN: /home/kevin/kevin/gello_software/config_pose
Total files: 2
================================================================================

File                                     Time
--------------------------------------------------------------------------------
session_20260316_142345.json             2026-03-16 14:23:45 - 14:35:12
session_20260316_151823.json             2026-03-16 15:18:23 - 15:29:45

================================================================================
TIP: Use --verbose to see full pose details
================================================================================
```

With `--verbose`:

```bash
python3 scripts/list_poses.py --verbose
```

Will display each session with detailed information from start and stop configs.

## Analyzing Session Data

### View entire session

```bash
cat config_pose/session_20260316_142345.json | jq '.'
```

### View only start config

```bash
cat config_pose/session_20260316_142345.json | jq '.config_start'
```

### View only stop config

```bash
cat config_pose/session_20260316_142345.json | jq '.config_stop'
```

### Compare start vs stop (see changes)

```bash
# Show difference between start and stop
python3 << 'EOF'
import json
import numpy as np

with open('config_pose/session_20260316_142345.json') as f:
    session = json.load(f)

print("Joint Movement Summary:")
print("=" * 80)

for side in ['left', 'right']:
    robot_key = f'robot_{side}'
    gello_key = f'gello_{side}'
    
    if session['config_start'].get(robot_key):
        start = np.array(session['config_start'][robot_key])
        stop = np.array(session['config_stop'][robot_key])
        diff = stop - start
        diff_deg = np.rad2deg(diff)
        
        print(f"\nRobot {side.upper()}:")
        print(f"  Movement (rad): {[f'{d:.4f}' for d in diff]}")
        print(f"  Movement (deg): {[f'{d:.2f}°' for d in diff_deg]}")
        
    if session['config_start'].get(gello_key):
        start = np.array(session['config_start'][gello_key])
        stop = np.array(session['config_stop'][gello_key])
        diff = stop - start
        diff_deg = np.rad2deg(diff)
        
        print(f"\nGELLO {side.upper()}:")
        print(f"  Movement (rad): {[f'{d:.4f}' for d in diff]}")
        print(f"  Movement (deg): {[f'{d:.2f}°' for d in diff_deg]}")

print("\n" + "=" * 80)
EOF
```

This shows exactly how much each joint moved during the session.

## Example Workflow

### Session 1: Teleoperation with Auto Capture

```bash
# 1. Move robots and GELLO to safe starting position
# 2. Run teleoperation with auto capture (everything is automatic!)
python3 scripts/run_with_pose_capture.py \
  --robot-ip-left=192.168.1.20 \
  --robot-ip-right=192.168.1.10 \
  --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
  --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0

# Automatic captures:
# 3. START config captured on startup
# 4. Teleoperate normally (5-10 minutes or more)
# 5. Press Ctrl+C to stop
# 6. STOP config automatically captured

# Result: config_pose/session_20260316_142345.json
#         (1 file with START and STOP config)
```

### Session 2: Review Captured Data

```bash
# Check what happened in last session
python3 scripts/list_poses.py

# View details
cat config_pose/session_20260316_142345.json | jq '.'

# Or view with list_poses
python3 scripts/list_poses.py --verbose
```

### Session 3: Multi-Session Comparison

```bash
# Track multiple sessions
python3 scripts/list_poses.py --verbose

# Output will show all sessions with start/stop timestamps
```

## Folder Structure

```
gello_software/
├── config_pose/                    # Folder for all sessions
│   ├── session_20260316_142345.json    # 1 complete session (start + stop)
│   ├── session_20260316_151823.json    # 1 complete session (start + stop)
│   └── session_20260316_165412.json    # 1 complete session (start + stop)
├── scripts/
│   ├── pose_capture_helper.py      # Core capture functionality
│   ├── capture_pose.py             # Manual capture (start/stop in one script)
│   ├── list_poses.py               # View all sessions
│   ├── run_with_pose_capture.py    # RECOMMENDED: Auto capture wrapper
│   ├── capture_start.py            # (deprecated - use capture_pose.py)
│   └── capture_stop.py             # (deprecated - use capture_pose.py)
└── experiments/
    ├── launch_nodes.py
    └── run_env.py
```

**Key Point:** Each teleoperation session = 1 JSON file!
- File name: `session_YYYYMMDD_HHMMSS.json`
- Contains: START config + STOP config
- Timestamps: session start and stop times

## Parameters

### run_with_pose_capture.py

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--single-arm` | `False` | Use single-arm configuration instead of bimanual |
| `--robot-ip` | `192.168.1.20` | IP for single robot |
| `--robot-ip-left` | `192.168.1.20` | IP for left robot |
| `--robot-ip-right` | `192.168.1.10` | IP for right robot |
| `--gello-port` | - | Serial port for single GELLO |
| `--gello-left-port` | - | Serial port for left GELLO |
| `--gello-right-port` | - | Serial port for right GELLO |
| `--use-relative-mode` | `True` | Enable relative mode for safer teleoperation |
| `--agent` | `gello` | Agent type: `gello`, `quest`, `spacemouse` |
| `--config-dir` | `config_pose` | Directory to save captured poses |
| `--verbose` | `False` | Print detailed output |

### capture_pose.py

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--robot` | `ur` | Robot type: `ur`, `xarm`, `bimanual_ur` |
| `--robot-ip` | `192.168.1.20` | IP for robot |
| `--robot-ip-left` | `192.168.1.20` | IP for left robot |
| `--robot-ip-right` | `192.168.1.10` | IP for right robot |
| `--gello-port` | - | Serial port for GELLO |
| `--gello-left-port` | - | Serial port for left GELLO |
| `--gello-right-port` | - | Serial port for right GELLO |
| `--capture-type` | `start` | `start` for new session or `stop` to update |
| `--session-id` | - | Session ID for updating existing session (required for stop) |
| `--config-dir` | `config_pose` | Directory to save poses |
| `--verbose` | `False` | Print detailed output |

### list_poses.py

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--config-dir` | `config_pose` | Directory containing saved poses |
| `--verbose` | `False` | Show full pose details |

## Finding Your GELLO Serial Ports

To find your GELLO device serial ports, run:

```bash
ls -la /dev/serial/by-id/
```

You'll see output like:
```
usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 -> ../../ttyUSB0
usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0 -> ../../ttyUSB1
```

Use the full path (e.g., `/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0`) as the port argument.

## Integration with Existing Code

These scripts **do not modify** existing teleoperation code. They:
- Only read robot/GELLO state with `get_joint_state()` at the beginning and end
- Wrapper `run_with_pose_capture.py` runs `experiments/run_env.py` as a subprocess
- Save data to separate folder `config_pose/`
- Can be used as a drop-in replacement for `run_env.py`

So 100% safe to integrate without worrying about breaking existing workflow!

**Before (manual):**
```bash
python3 experiments/run_env.py --bimanual --agent=gello --use-relative-mode
```

**Now (with auto capture):**
```bash
python3 scripts/run_with_pose_capture.py --robot-ip-left=... --robot-ip-right=...
```

Same teleoperation experience, but with automatic pose capture! 🎯

## Advanced: Saving Multiple Calibrations

You can save different calibrations for different scenarios:

```bash
# Tight workspace calibration
python3 scripts/run_with_pose_capture.py ... # saves session_20260316_142345.json

# Normal workspace calibration  
python3 scripts/run_with_pose_capture.py ... # saves session_20260316_151823.json

# Then you have history of all sessions
python3 scripts/list_poses.py --verbose
```

## Troubleshooting

### "Connection refused" for robot

- Ensure robot nodes are running (start `launch_nodes.py`)
- Check that robot IPs are correct
- Try pinging robot IP: `ping 192.168.1.20`

### "Port not found" for GELLO

- Check serial ports with `ls /dev/serial/by-id/`
- Ensure USB cable is connected
- Try reconnecting USB cable
- Verify port path was copied correctly

### Poses not captured

- If using `run_with_pose_capture.py`, check that permissions are okay on config_pose folder
- Check that robot connections are stable
- Try reducing update rate if there are communication issues

## Notes

- ✓ Scripts do not modify existing code
- ✓ Use only existing APIs (`get_joint_state()`, etc.)
- ✓ Safe for production use
- ✓ All poses include timestamps for tracking
- ✓ Simple JSON format, easy to parse and analyze
- ✓ One file per session makes tracking simple

Happy teleoperation! 🚀
