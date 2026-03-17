# Teleoperation + Pose Capture - Integrated Guide

Simple integration of pose capture into your existing teleoperation workflow.

## Quick Start (Your Exact Workflow)

### Terminal 1: Start the robot server (same as before)

```bash
python experiments/launch_nodes.py --robot=bimanual_ur
```

### Terminal 2: Run teleoperation with automatic pose capture (NEW - replaces run_env.py)

**Old way (no capture):**
```bash
python experiments/run_env.py --bimanual --agent=gello --use-relative-mode
```

**New way (with automatic pose capture):**
```bash
python experiments/teleoperate_with_capture.py --bimanual --agent=gello --use-relative-mode
```

**That's it!** Everything you do is EXACTLY the same, but pose capture happens automatically.

## What Happens Automatically

1. **Script starts** → Captures START configuration (robot + GELLO positions)
2. **Teleoperation runs** → You control the robot normally
3. **Press Ctrl+C** → Captures STOP configuration (final robot + GELLO positions)
4. **Result** → Single session file saved to `config_pose/session_YYYYMMDD_HHMMSS.json`

**Example:**
```bash
$ python experiments/teleoperate_with_capture.py --bimanual --agent=gello --use-relative-mode

================================================================================
TELEOPERATION WITH AUTOMATIC POSE CAPTURE
================================================================================

[1/3] Capturing START configuration...
      Session ID: 20260316_175245
      ✓ START config captured

[2/3] Starting teleoperation...
      Running: python run_env.py --bimanual --agent=gello --use-relative-mode
      Press Ctrl+C to stop and capture STOP config

<teleoperation runs...>

^C
[3/3] Teleoperation stopped by user
      Capturing STOP configuration...
      ✓ STOP config captured

================================================================================
✓ TELEOPERATION COMPLETE
================================================================================
Session ID:     20260316_175245
Session file:   config_pose/session_20260316_175245.json
Both configs saved in single file
```

## All Arguments Work the Same

Every argument you use with `run_env.py` works with `teleoperate_with_capture.py`:

```bash
# These all work:
python experiments/teleoperate_with_capture.py --bimanual --agent=gello --use-relative-mode

python experiments/teleoperate_with_capture.py --bimanual --agent=quest --use-relative-mode

python experiments/teleoperate_with_capture.py --single-arm --agent=gello

python experiments/teleoperate_with_capture.py --bimanual --agent=gello --use-relative-mode --verbose

# With custom GELLO ports:
python experiments/teleoperate_with_capture.py --bimanual --agent=gello \
  --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
  --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0
```

## View Saved Sessions

```bash
# List all sessions
python scripts/list_poses.py

# View full details
python scripts/list_poses.py --verbose
```

## Manual Capture (If Needed)

For fine-grained control over when to capture:

```bash
# Capture START when ready
python scripts/capture_pose.py --capture-type=start --bimanual --agent=gello ...

# Do whatever you want...

# Capture STOP when ready
python scripts/capture_pose.py --capture-type=stop --session-id=XXXXXXXXX --bimanual --agent=gello ...
```

## Session File Format

Each session is one JSON file:

```json
{
  "session_id": "20260316_175245",
  "robot_type": "bimanual_ur",
  "timestamp_start": "2026-03-16T17:52:45.123456",
  "timestamp_start_unix": 1742265165.123456,
  "timestamp_stop": "2026-03-16T17:53:12.987654",
  "timestamp_stop_unix": 1742265192.987654,
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

Location: `config_pose/session_YYYYMMDD_HHMMSS.json`

## Files

**New:**
- `experiments/teleoperate_with_capture.py` - 🆕 Use this instead of run_env.py (integrated auto-capture)

**Utilities (if needed):**
- `scripts/list_poses.py` - View all saved sessions
- `scripts/capture_pose.py` - Manual start/stop capture (for special cases)
- `scripts/pose_capture_helper.py` - Core capture library

**Old:** (removed)
- ~~scripts/capture_start.py~~ - Deprecated (merged into capture_pose.py)
- ~~scripts/capture_stop.py~~ - Deprecated (merged into capture_pose.py)
- ~~scripts/run_with_pose_capture.py~~ - Replaced by teleoperate_with_capture.py

## Key Points

✅ **Automatic** - No extra steps, happens transparently
✅ **Single file per session** - START + STOP in one .json
✅ **Same workflow** - Just use `teleoperate_with_capture.py` instead of `run_env.py`
✅ **All arguments work** - Everything you'd pass to `run_env.py` works here
✅ **Timestamps included** - See exactly when capture happened
✅ **Non-invasive** - Doesn't modify existing robot code
✅ **One command difference** - Just change `run_env.py` → `teleoperate_with_capture.py`

---

**That's it! Happy teleoperation! 🚀**
