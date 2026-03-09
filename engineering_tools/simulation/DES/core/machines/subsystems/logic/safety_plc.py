"""
SafetyPLC - Event-Based Handshake for Robot/Feeder Coordination

Prevents deadlock between Robot and Feeder using simpy.Event objects
instead of simpy.Resource. This implements a deterministic PLC-like
handshake protocol.

Key Design:
- Uses simpy.Event (one-shot signals) NOT simpy.Resource (queuing)
- Events must be recreated after each use
- Initial state has both events pre-triggered to allow first operation
"""

from enum import Enum
import simpy
from ....logging.logger import EventLogger


class RobotState(Enum):
    """Robot operating states"""
    HOME = "HOME"
    MOVING_TO_SAFE = "MOVING_TO_SAFE"
    IN_WINDOW = "IN_WINDOW"
    FAULT = "FAULT"


class FeederState(Enum):
    """Feeder operating states"""
    IDLE = "IDLE"
    MOVING = "MOVING"
    LOCKED = "LOCKED"


class SafetyPLC:
    """
    Safety interlock controller using event-based handshaking.

    Prevents concurrent motion of Robot and Feeder to avoid collisions.
    Uses explicit event signaling rather than resource queuing to prevent
    deadlock scenarios.

    Protocol:
    - Robot requests entry -> waits for feeder_is_idle event
    - Robot releases entry -> signals robot_is_home event
    - Feeder requests move -> waits for robot_is_home event
    - Feeder releases move -> signals feeder_is_idle event
    """

    def __init__(self, env: simpy.Environment, logger: EventLogger):
        """
        Initialize the SafetyPLC.

        Args:
            env: SimPy environment
            logger: Event logger for tracking interlock behavior
        """
        self.env = env
        self.logger = logger

        # State tracking
        self.robot_state = RobotState.HOME
        self.feeder_state = FeederState.IDLE

        # Handshake events (recreated after each use)
        # Initial state: both events are pre-triggered
        self.robot_is_home = env.event()
        self.robot_is_home.succeed()  # Robot starts at home

        self.feeder_is_idle = env.event()
        self.feeder_is_idle.succeed()  # Feeder starts idle

    def request_robot_entry(self):
        """
        Robot requests permission to enter processing window.
        Blocks until feeder is idle.

        Yields:
            SimPy event that resolves when feeder is idle

        Raises:
            RuntimeError: If robot is not in HOME state
        """
        if self.robot_state != RobotState.HOME:
            raise RuntimeError(
                f"Robot must be HOME before requesting entry. "
                f"Current state: {self.robot_state}"
            )

        # Wait for feeder to be idle
        if not self.feeder_is_idle.triggered:
            with self.logger.log_event("Interlock", "SafetyPLC", "Robot waiting for Feeder"):
                yield self.feeder_is_idle

        # Grant access
        self.robot_state = RobotState.IN_WINDOW

        # Create new event for next cycle
        self.feeder_is_idle = self.env.event()

    def release_robot_entry(self):
        """
        Robot signals it has returned to safe home position.
        Signals to feeder that it's safe to move.

        This method is idempotent - calling it multiple times is safe.
        """
        if self.robot_state not in [RobotState.IN_WINDOW, RobotState.MOVING_TO_SAFE]:
            # Allow idempotent calls (robot might call this multiple times)
            return

        # Update state
        self.robot_state = RobotState.HOME

        # Signal to feeder that robot is home
        if not self.robot_is_home.triggered:
            self.robot_is_home.succeed()

        # Create new event for next cycle
        self.robot_is_home = self.env.event()

    def request_feeder_move(self):
        """
        Feeder requests permission to index (move beam).
        Blocks until robot is home.

        Yields:
            SimPy event that resolves when robot is home

        Raises:
            RuntimeError: If feeder is not in IDLE state
        """
        if self.feeder_state != FeederState.IDLE:
            raise RuntimeError(
                f"Feeder must be IDLE before requesting move. "
                f"Current state: {self.feeder_state}"
            )

        # Wait for robot to be home
        if not self.robot_is_home.triggered:
            with self.logger.log_event("Interlock", "SafetyPLC", "Feeder waiting for Robot"):
                yield self.robot_is_home

        # Grant access
        self.feeder_state = FeederState.MOVING

        # Create new event for next cycle
        self.robot_is_home = self.env.event()

    def release_feeder_move(self):
        """
        Feeder signals it has stopped moving.
        Signals to robot that it's safe to enter window.

        This method is idempotent - calling it multiple times is safe.
        """
        if self.feeder_state != FeederState.MOVING:
            # Allow idempotent calls
            return

        # Update state
        self.feeder_state = FeederState.IDLE

        # Signal to robot that feeder is idle
        if not self.feeder_is_idle.triggered:
            self.feeder_is_idle.succeed()

        # Create new event for next cycle
        self.feeder_is_idle = self.env.event()
