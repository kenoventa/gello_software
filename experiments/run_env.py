import glob
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import tyro

from gello.env import RobotEnv
from gello.robots.robot import PrintRobot
from gello.utils.launch_utils import instantiate_from_dict
from gello.zmq_core.robot_node import ZMQClientRobot


def print_color(*args, color=None, attrs=(), **kwargs):
    import termcolor

    if len(args) > 0:
        args = tuple(termcolor.colored(arg, color=color, attrs=attrs) for arg in args)
    print(*args, **kwargs)


@dataclass
class Args:
    agent: str = "none"
    robot_port: int = 6001
    wrist_camera_port: int = 5000
    base_camera_port: int = 5001
    hostname: str = "127.0.0.1"
    robot_type: str = None  # only needed for quest agent or spacemouse agent
    hz: int = 100
    start_joints: Optional[Tuple[float, ...]] = None

    gello_port: Optional[str] = None
    gello_left_port: Optional[str] = None
    """Override default left GELLO port for bimanual setup"""
    gello_right_port: Optional[str] = None
    """Override default right GELLO port for bimanual setup"""
    mock: bool = False
    use_save_interface: bool = False
    data_dir: str = "~/bc_data"
    bimanual: bool = False
    verbose: bool = False
    use_relative_mode: bool = False
    """Enable relative mode for safer teleoperation. Instead of commanding absolute
    joint positions, the robot will follow relative motions from its starting pose.
    This is safer when the robot cannot reach the leader's initial configuration."""

    def __post_init__(self):
        if self.start_joints is not None:
            self.start_joints = np.array(self.start_joints)


def main(args):
    if args.mock:
        robot_client = PrintRobot(8, dont_print=True)
        camera_clients = {}
    else:
        camera_clients = {
            # you can optionally add camera nodes here for imitation learning purposes
            # "wrist": ZMQClientCamera(port=args.wrist_camera_port, host=args.hostname),
            # "base": ZMQClientCamera(port=args.base_camera_port, host=args.hostname),
        }
        robot_client = ZMQClientRobot(port=args.robot_port, host=args.hostname)
    env = RobotEnv(robot_client, control_rate_hz=args.hz, camera_dict=camera_clients)

    agent_cfg = {}
    if args.bimanual:
        if args.agent == "gello":
            # dynamixel control box port map (to distinguish left and right gello)
            # Use --gello-left-port and --gello-right-port to override defaults
            # Defaults are for UR bimanual setup
            right = (
                args.gello_right_port
                or "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0"
            )
            left = (
                args.gello_left_port
                or "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0"
            )
            agent_left_cfg = {
                "_target_": "gello.agents.gello_agent.GelloAgent",
                "port": left,
            }
            agent_right_cfg = {
                "_target_": "gello.agents.gello_agent.GelloAgent",
                "port": right,
            }

            # Wrap with RelativeAgent for each arm if relative_mode is enabled
            if args.use_relative_mode:
                agent_left_cfg = {
                    "_target_": "gello.agents.relative_agent.RelativeAgent",
                    "leader_agent": agent_left_cfg,
                }
                agent_right_cfg = {
                    "_target_": "gello.agents.relative_agent.RelativeAgent",
                    "leader_agent": agent_right_cfg,
                }

            agent_cfg = {
                "_target_": "gello.agents.agent.BimanualAgent",
                "agent_left": agent_left_cfg,
                "agent_right": agent_right_cfg,
            }
        elif args.agent == "quest":
            agent_cfg = {
                "_target_": "gello.agents.agent.BimanualAgent",
                "agent_left": {
                    "_target_": "gello.agents.quest_agent.SingleArmQuestAgent",
                    "robot_type": args.robot_type,
                    "which_hand": "l",
                },
                "agent_right": {
                    "_target_": "gello.agents.quest_agent.SingleArmQuestAgent",
                    "robot_type": args.robot_type,
                    "which_hand": "r",
                },
            }
        elif args.agent == "spacemouse":
            left_path = "/dev/hidraw0"
            right_path = "/dev/hidraw1"
            agent_cfg = {
                "_target_": "gello.agents.agent.BimanualAgent",
                "agent_left": {
                    "_target_": "gello.agents.spacemouse_agent.SpacemouseAgent",
                    "robot_type": args.robot_type,
                    "device_path": left_path,
                    "verbose": args.verbose,
                },
                "agent_right": {
                    "_target_": "gello.agents.spacemouse_agent.SpacemouseAgent",
                    "robot_type": args.robot_type,
                    "device_path": right_path,
                    "verbose": args.verbose,
                    "invert_button": True,
                },
            }
        else:
            raise ValueError(f"Invalid agent name for bimanual: {args.agent}")

        # System setup specific. This reset configuration works well on our setup. If you are mounting the robot
        # differently, you need a separate reset joint configuration.
        # NOTE: Bimanual reset is disabled in relative mode because:
        # 1. RelativeAgent captures initial poses from current position
        # 2. Forcing reset can interfere with relative mode initialization
        # 3. Each arm should maintain its current safe position as reference
        if not args.use_relative_mode:
            reset_joints_left = np.deg2rad([0, -90, -90, -90, 90, 0, 0])
            reset_joints_right = np.deg2rad([0, -90, 90, -90, -90, 0, 0])
            reset_joints = np.concatenate([reset_joints_left, reset_joints_right])
            curr_joints = np.array(env.get_obs()["joint_positions"])
            max_delta = (np.abs(curr_joints - reset_joints)).max()
            steps = min(int(max_delta / 0.01), 100)

            for jnt in np.linspace(curr_joints, reset_joints, steps):
                env.step(jnt)
        else:
            print("Relative mode activated: Skipping bimanual reset phase.")
            print("RelativeAgent will capture current positions as initial reference.")
    else:
        if args.agent == "gello":
            gello_port = args.gello_port
            if gello_port is None:
                usb_ports = glob.glob("/dev/serial/by-id/*")
                print(f"Found {len(usb_ports)} ports")
                if len(usb_ports) > 0:
                    gello_port = usb_ports[0]
                    print(f"using port {gello_port}")
                else:
                    raise ValueError(
                        "No gello port found, please specify one or plug in gello"
                    )
            agent_cfg = {
                "_target_": "gello.agents.gello_agent.GelloAgent",
                "port": gello_port,
                "start_joints": None,  # Disable auto-offset adjustment; use calibrated offsets directly
            }

            # Wrap with RelativeAgent if relative_mode is enabled
            if args.use_relative_mode:
                print("using relative mode for safer teleoperation")
                agent_cfg = {
                    "_target_": "gello.agents.relative_agent.RelativeAgent",
                    "leader_agent": agent_cfg,
                }

            if args.start_joints is None:
                reset_joints = np.deg2rad(
                    [-90, -90, 90, -90, -90, 0]
                    ##### THIS IS START JOINTS OF THE ROBOT ######
                )  # Change this to your own reset joints
            else:
                reset_joints = np.array(args.start_joints)

            curr_joints = np.array(env.get_obs()["joint_positions"])
            if reset_joints.shape == curr_joints.shape:
                max_delta_per_step = (
                    0.0002  # Speed limit for startup (slower, more safe)
                )
                max_distance = (np.abs(curr_joints - reset_joints)).max()
                steps = max(
                    int(max_distance / max_delta_per_step), 25
                )  # Ensure smooth movement

                for jnt in np.linspace(curr_joints, reset_joints, steps):
                    env.step(jnt)
                    time.sleep(0.001)
        elif args.agent == "quest":
            agent_cfg = {
                "_target_": "gello.agents.quest_agent.SingleArmQuestAgent",
                "robot_type": args.robot_type,
                "which_hand": "l",
            }
        elif args.agent == "spacemouse":
            agent_cfg = {
                "_target_": "gello.agents.spacemouse_agent.SpacemouseAgent",
                "robot_type": args.robot_type,
                "verbose": args.verbose,
            }
        elif args.agent == "dummy" or args.agent == "none":
            agent_cfg = {
                "_target_": "gello.agents.agent.DummyAgent",
                "num_dofs": robot_client.num_dofs(),
            }
        elif args.agent == "policy":
            raise NotImplementedError("add your imitation policy here if there is one")
        else:
            raise ValueError("Invalid agent name")

    agent = instantiate_from_dict(agent_cfg)
    # going to start position
    print("Going to start position")
    start_pos = agent.act(env.get_obs())
    print(f"Start position (GELLO current) in radians: {start_pos}")
    print(f"Start position in degrees: {np.rad2deg(start_pos)}")
    obs = env.get_obs()
    joints = np.array(obs["joint_positions"])

    # If agent has more DOFs than robot (e.g., agent has gripper but robot doesn't),
    # only use the arm joint positions
    if len(start_pos) > len(joints):
        start_pos = start_pos[: len(joints)]

    abs_deltas = np.abs(start_pos - joints)
    id_max_joint_delta = np.argmax(abs_deltas)

    print(f"\nDelta between GELLO and UR (radians): {abs_deltas}")
    print(f"Delta between GELLO and UR (degrees): {np.rad2deg(abs_deltas)}")
    print(
        f"Max delta: {abs_deltas[id_max_joint_delta]:.4f} rad ({np.rad2deg(abs_deltas[id_max_joint_delta]):.2f}°) at joint {id_max_joint_delta}\n"
    )

    max_joint_delta = 1.0
    if abs_deltas[id_max_joint_delta] > max_joint_delta:
        id_mask = abs_deltas > max_joint_delta
        print("WARNING: Large joint position differences detected:")
        print()
        ids = np.arange(len(id_mask))[id_mask]
        for i, delta, joint, current_j in zip(
            ids,
            abs_deltas[id_mask],
            start_pos[id_mask],
            joints[id_mask],
        ):
            print(
                f"joint[{i}]: \t delta: {delta:4.3f} , leader: \t{joint:4.3f} , follower: \t{current_j:4.3f}"
            )
        print("\nProceeding anyway...\n")

    print(f"Start pos: {len(start_pos)}", f"Joints: {len(joints)}")
    print(f"UR current position in radians: {joints}")
    print(f"UR current position in degrees: {np.rad2deg(joints)}")
    assert len(start_pos) == len(
        joints
    ), f"agent output dim = {len(start_pos)}, but env dim = {len(joints)}"

    max_delta = 0.005  # speed up if too slow, down if too fast or unstable
    for _ in range(25):
        obs = env.get_obs()
        command_joints = agent.act(obs)
        current_joints = np.array(obs["joint_positions"])
        # If agent has more DOFs than robot (e.g., agent has gripper but robot doesn't),
        # only use the arm joint positions
        if len(command_joints) > len(current_joints):
            command_joints = command_joints[: len(current_joints)]
        delta = command_joints - current_joints
        max_joint_delta = np.abs(delta).max()
        if max_joint_delta > max_delta:
            delta = delta / max_joint_delta * max_delta
        env.step(current_joints + delta)

    obs = env.get_obs()
    joints = np.array(obs["joint_positions"])
    action = agent.act(obs)
    # If agent has more DOFs than robot (e.g., agent has gripper but robot doesn't),
    # only use the arm joint positions
    if len(action) > len(joints):
        action = action[: len(joints)]
    if (action - joints > 0.7).any():
        print("Action is too big")

        # print which joints are too big
        joint_index = np.where(action - joints > 0.8)
        for j in joint_index:
            print(
                f"Joint [{j}], leader: {action[j]}, follower: {joints[j]}, diff: {action[j] - joints[j]}"
            )
        exit()

    from gello.utils.control_utils import SaveInterface, run_control_loop

    save_interface = None
    if args.use_save_interface:
        save_interface = SaveInterface(
            data_dir=args.data_dir, agent_name=args.agent, expand_user=True
        )

    run_control_loop(env, agent, save_interface, use_colors=True)


if __name__ == "__main__":
    main(tyro.cli(Args))
