"""
simulation/core/machines/subsystems/tooling/clamp.py

Reusable clamping logic for fixtures, grippers, and workholding systems.

This module provides a generic Clamp class that can be used across different
subsystems (push rods, fixtures, robots, etc.) for consistent clamping behavior.
"""

import simpy
from ....logging.logger import EventLogger


class Clamp:
    """
    Generic clamping mechanism for workholding and fixtures.

    Manages clamping/unclamping state and timing for any system that needs
    to secure workpieces (conveyors, robot grippers, fixtures, vises, etc.).

    Args:
        env: SimPy environment
        logger: Event logger for event tracking
        clamp_time: Time to engage clamp (seconds)
        unclamp_time: Time to release clamp (seconds, defaults to clamp_time)
        name: Identifier for this clamp (e.g., "PushRod", "Fixture1")

    Attributes:
        is_clamped: Current clamping state (True = clamped, False = unclamped)

    Example:
        >>> env = simpy.Environment()
        >>> logger = EventLogger(env)
        >>> clamp = Clamp(env, logger, clamp_time=1.5, name="PushRodGripper")
        >>>
        >>> def process(env, clamp):
        ...     yield env.process(clamp.clamp())
        ...     # ... do work with clamped part ...
        ...     yield env.process(clamp.unclamp())
    """

    def __init__(
        self,
        env: simpy.Environment,
        logger: EventLogger,
        clamp_time: float,
        unclamp_time: float = None,
        name: str = "Clamp"
    ):
        self.env = env
        self.logger = logger
        self.name = name

        # Timing parameters
        self.clamp_time = clamp_time
        self.unclamp_time = unclamp_time if unclamp_time is not None else clamp_time

        # State
        self.is_clamped = False

    def clamp(self):
        """
        Engage the clamp (SimPy process).

        If already clamped, this is a no-op (returns immediately).
        Otherwise, waits for clamp_time to complete the clamping action.

        Yields:
            SimPy timeout for clamp engagement

        Example:
            >>> yield env.process(clamp.clamp())
        """
        if not self.is_clamped:
            with self.logger.log_event("Clamp", self.name):
                yield self.env.timeout(self.clamp_time)
                self.is_clamped = True

    def unclamp(self):
        """
        Release the clamp (SimPy process).

        If already unclamped, this is a no-op (returns immediately).
        Otherwise, waits for unclamp_time to complete the unclamping action.

        Yields:
            SimPy timeout for clamp release

        Example:
            >>> yield env.process(clamp.unclamp())
        """
        if self.is_clamped:
            with self.logger.log_event("Unclamp", self.name):
                yield self.env.timeout(self.unclamp_time)
                self.is_clamped = False

    def ensure_clamped(self):
        """
        Ensure the clamp is engaged, clamping if necessary.

        Useful when you want to guarantee clamped state without
        knowing the current state.

        Yields:
            SimPy timeout if clamping is needed, otherwise returns immediately

        Example:
            >>> yield env.process(clamp.ensure_clamped())
            >>> # Now guaranteed to be clamped
        """
        if not self.is_clamped:
            yield self.env.process(self.clamp())

    def ensure_unclamped(self):
        """
        Ensure the clamp is released, unclamping if necessary.

        Useful when you want to guarantee unclamped state without
        knowing the current state.

        Yields:
            SimPy timeout if unclamping is needed, otherwise returns immediately

        Example:
            >>> yield env.process(clamp.ensure_unclamped())
            >>> # Now guaranteed to be unclamped
        """
        if self.is_clamped:
            yield self.env.process(self.unclamp())

    def check_clamped(self, require_clamped: bool = True):
        """
        Verify clamping state and raise error if incorrect.

        Useful for safety checks before operations that require specific
        clamping states (e.g., can't move part while unclamped).

        Args:
            require_clamped: If True, requires clamped state.
                           If False, requires unclamped state.

        Raises:
            RuntimeError: If clamping state doesn't match requirement

        Example:
            >>> clamp.check_clamped(require_clamped=True)
            >>> # Safe to proceed with operation requiring clamped part
        """
        if require_clamped and not self.is_clamped:
            raise RuntimeError(f"{self.name}: Operation requires clamped state!")
        elif not require_clamped and self.is_clamped:
            raise RuntimeError(f"{self.name}: Operation requires unclamped state!")

    def reset(self):
        """
        Reset clamp to initial unclamped state (without simulation time).

        Useful for resetting simulation state between runs or
        for initialization. Does NOT consume simulation time.

        Example:
            >>> clamp.reset()
            >>> assert clamp.is_clamped == False
        """
        self.is_clamped = False


class DualClamp:
    """
    Coordinated dual-clamp system for synchronized clamping operations.

    Useful for systems with primary/secondary clamps, or left/right clamps
    that need to operate together (e.g., dual-station fixtures, transfer systems).

    Args:
        clamp_a: First clamp instance
        clamp_b: Second clamp instance
        simultaneous: If True, both clamps operate in parallel (default).
                     If False, operates sequentially (A then B).

    Example:
        >>> clamp_left = Clamp(env, logger, 1.0, name="LeftClamp")
        >>> clamp_right = Clamp(env, logger, 1.0, name="RightClamp")
        >>> dual = DualClamp(clamp_left, clamp_right, simultaneous=True)
        >>>
        >>> # Clamps both simultaneously
        >>> yield env.process(dual.clamp_both())
    """

    def __init__(
        self,
        clamp_a: Clamp,
        clamp_b: Clamp,
        simultaneous: bool = True
    ):
        self.clamp_a = clamp_a
        self.clamp_b = clamp_b
        self.simultaneous = simultaneous
        self.env = clamp_a.env  # Assume both use same environment

    def clamp_both(self):
        """Engage both clamps (simultaneously or sequentially)."""
        if self.simultaneous:
            # Run both clamp operations in parallel
            yield self.env.process(self.clamp_a.clamp()) & self.env.process(self.clamp_b.clamp())
        else:
            # Run sequentially
            yield self.env.process(self.clamp_a.clamp())
            yield self.env.process(self.clamp_b.clamp())

    def unclamp_both(self):
        """Release both clamps (simultaneously or sequentially)."""
        if self.simultaneous:
            # Run both unclamp operations in parallel
            yield self.env.process(self.clamp_a.unclamp()) & self.env.process(self.clamp_b.unclamp())
        else:
            # Run sequentially
            yield self.env.process(self.clamp_a.unclamp())
            yield self.env.process(self.clamp_b.unclamp())

    @property
    def both_clamped(self) -> bool:
        """Check if both clamps are engaged."""
        return self.clamp_a.is_clamped and self.clamp_b.is_clamped

    @property
    def both_unclamped(self) -> bool:
        """Check if both clamps are released."""
        return not self.clamp_a.is_clamped and not self.clamp_b.is_clamped

    def reset(self):
        """Reset both clamps to unclamped state."""
        self.clamp_a.reset()
        self.clamp_b.reset()
