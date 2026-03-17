# Pose Capture System - Quick Start Guide

## 🎯 Auto Capture: Start + Stop in 1 File

When you run teleoperation with this wrapper, the system **automatically**:
1. ✓ Capture starting config when teleoperation begins
2. ✓ Run teleoperation normally
3. ✓ Capture final config when Ctrl+C (stop)
4. ✓ Save BOTH in **1 JSON file** with session ID

## 🚀 Usage (Recommended Way)

### Bimanual Setup

```bash
python3 scripts/run_with_pose_capture.py \
  --robot-ip-left=192.168.1.20 \
  --robot-ip-right=192.168.1.10 \
  --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
  --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0
```

### Single-Arm Setup

```bash
python3 scripts/run_with_pose_capture.py \
  --single-arm \
  --robot-ip=192.168.1.20 \
  --gello-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0
```

## 📁 Output: Single Session File

All poses are saved in **1 file**: `config_pose/session_YYYYMMDD_HHMMSS.json`

**Format:**
```json
{
  "session_id": "20260316_142345",
  "robot_type": "bimanual_ur",
  "timestamp_start": "2026-03-16T14:23:45.123456",
  "timestamp_start_unix": 1742217825.123456,
  "timestamp_stop": "2026-03-16T14:35:12.987654",
  "timestamp_stop_unix": 1742218512.987654,
  "config_start": {
    "robot_left": [-0.073, -1.547, 2.424, ...],
    "robot_right": [0.012, -1.712, -1.809, ...],
    "gello_left": [0.545, -1.580, 2.540, ...],
    "gello_right": [-2.057, -1.914, 2.537, ...]
  },
  "config_stop": {
    "robot_left": [-0.074, -1.548, 2.425, ...],
    "robot_right": [0.013, -1.713, -1.810, ...],
    "gello_left": [0.546, -1.581, 2.541, ...],
    "gello_right": [-2.058, -1.915, 2.538, ...]
  }
}
```

## ⚙️ Workflow

1. **Setup robots/GELLO** in safe position
2. **Run wrapper script:**
   ```bash
   python3 scripts/run_with_pose_capture.py \
     --robot-ip-left=192.168.1.20 \
     --robot-ip-right=192.168.1.10 \
     --gello-left-port=... \
     --gello-right-port=...
   ```
3. **Script automatically captures START config** ✓
4. **Teleoperate normally** - teleoperation runs as usual
5. **Press Ctrl+C** to stop
6. **Script automatically captures STOP config** ✓
7. **View results:**
   ```bash
   cat config_pose/session_20260316_142345.json
   ```

## 🔍 Analyze Session Data

Open the JSON file and compare `config_start` vs `config_stop`:

```bash
# View entire session
cat config_pose/session_20260316_142345.json | jq '.'

# View only start config
cat config_pose/session_20260316_142345.json | jq '.config_start'

# View only stop config
cat config_pose/session_20260316_142345.json | jq '.config_stop'
```

## 💡 Single File = 1 Complete Session

Every time you run `run_with_pose_capture.py`:
- **1 JSON file** is created with name `session_YYYYMMDD_HHMMSS.json`
- **START config** automatically captured at startup
- **STOP config** automatically captured at Ctrl+C
- **Both** saved in the same file

This makes session tracking much simpler - one file = one complete session with before/after data!

## 🛠️ Manual Capture (if needed)

If you want to capture poses manually at any time:

```bash
# Capture and create new session
python3 scripts/capture_pose.py --robot=bimanual_ur --capture-type=start ...

# Capture stop config for existing session  
python3 scripts/capture_pose.py --robot=bimanual_ur \
  --capture-type=stop \
  --session-id=20260316_142345 ...
```

But for most use cases, **just use `run_with_pose_capture.py`** - everything is automatic! 🎯

## 📚 Full Documentation

For complete information: [POSE_CAPTURE_GUIDE.md](POSE_CAPTURE_GUIDE.md)
