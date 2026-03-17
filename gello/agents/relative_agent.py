"""Relative teleoperation agent for safer motion control.

This agent wraps another agent (typically GelloAgent) and implements relative
control mode. Instead of commanding absolute joint positions (which can cause
the robot to move toward unsafe configurations), it:

1. Captures the initial pose of the leader (GELLO) and follower (UR)
2. Computes the delta between current and initial leader pose
3. Applies this delta to the follower's initial pose

This ensures the follower only moves relative to its starting position and
won't attempt to reach inaccessible absolute configurations.
"""

from typing import Any, Dict, Optional

import numpy as np

from gello.agents.agent import Agent


class RelativeAgent(Agent):
    """Wraps an agent to provide relative control mode.

    Typical usage:
        # Absolute mode (original behavior)
        gello_agent = GelloAgent(port="/dev/ttyUSB0")

        # Relative mode (safe for constrained workspaces)
        gello_agent = GelloAgent(port="/dev/ttyUSB0")
        relative_agent = RelativeAgent(gello_agent)

    The initial poses are captured on the first call to act().
    """

    def __init__(self, leader_agent: Agent):
        """Initialize the relative agent.

        Args:
            leader_agent: The underlying agent that provides leader positions.
                         Typically a GelloAgent.
        """
        self.leader_agent = leader_agent
        self._leader_initial_pos: Optional[np.ndarray] = None
        self._follower_initial_pos: Optional[np.ndarray] = None
        self._is_initialized = False

    def act(self, obs: Dict[str, Any]) -> np.ndarray:
        """Compute relative action based on leader and follower poses.

        First call will initialize the reference poses. Subsequent calls
        compute and return: follower_initial + (leader_current - leader_initial)

        Args:
            obs: Observation containing 'joint_positions' (follower current state)

        Returns:
            Target joint positions for the follower (relative to initial pose)
        """
        # Get the current leader position from the wrapped agent
        leader_current = self.leader_agent.act(obs)

        # Extract current follower position from observation
        follower_current = np.array(obs["joint_positions"])

        # Initialize on first call
        if not self._is_initialized:
            self._leader_initial_pos = leader_current.copy()
            self._follower_initial_pos = follower_current.copy()
            self._is_initialized = True

            print("\n" + "=" * 70)
            print("RELATIVE MODE INITIALIZED")
            print("=" * 70)
            print(f"Leader (GELLO) initial position (rad):")
            print(
                f"  {[f'{x:.4f}' for x in self._leader_initial_pos[:6]]}"
            )  # First 6 DOFs
            print(f"Follower (UR) initial position (rad):")
            print(f"  {[f'{x:.4f}' for x in self._follower_initial_pos[:6]]}")
            print(f"Follower (UR) initial position (deg):")
            print(
                f"  {[f'{np.rad2deg(x):.2f}°' for x in self._follower_initial_pos[:6]]}"
            )
            print("=" * 70)
            print("Relative mode: Robot will follow GELLO's relative motions")
            print("=" * 70 + "\n")

        # Compute the delta: how much the leader has moved from initial position
        leader_delta = leader_current - self._leader_initial_pos

        # Apply this delta to the follower's initial position
        follower_target = self._follower_initial_pos + leader_delta

        return follower_target

    def reset(self) -> None:
        """Reset the internal state (useful for restarting teleoperation)."""
        self._leader_initial_pos = None
        self._follower_initial_pos = None
        self._is_initialized = False
