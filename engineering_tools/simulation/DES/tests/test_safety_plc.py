"""
Unit tests for SafetyPLC event-based handshaking.

Tests verify:
- Initial state is correct (both resources available)
- Robot blocks when feeder is moving
- Feeder blocks when robot is in window
- No deadlock occurs during alternating access
"""

import pytest
import simpy
from ..core.logging.logger import EventLogger
from ..core.machines.subsystems.logic.safety_plc import SafetyPLC, RobotState, FeederState


def test_initial_state():
    """Verify PLC starts with both resources available."""
    env = simpy.Environment()
    logger = EventLogger(env)
    plc = SafetyPLC(env, logger)

    assert plc.robot_state == RobotState.HOME
    assert plc.feeder_state == FeederState.IDLE
    assert plc.robot_is_home.triggered
    assert plc.feeder_is_idle.triggered


def test_robot_waits_for_feeder():
    """Robot should block until feeder is idle."""
    env = simpy.Environment()
    logger = EventLogger(env)
    plc = SafetyPLC(env, logger)

    # Simulate feeder moving (clear the idle event)
    plc.feeder_is_idle = env.event()
    plc.feeder_state = FeederState.MOVING

    robot_entered = False

    def robot_process():
        nonlocal robot_entered
        yield from plc.request_robot_entry()
        robot_entered = True

    def feeder_process():
        yield env.timeout(5.0)  # Feeder moves for 5 seconds
        plc.release_feeder_move()

    env.process(robot_process())
    env.process(feeder_process())

    # Run for 3 seconds - robot should still be waiting
    env.run(until=3.0)
    assert not robot_entered, "Robot should be blocked by feeder"

    # Run until completion - robot should now have entered
    env.run(until=10.0)
    assert robot_entered, "Robot should have entered after feeder stopped"


def test_feeder_waits_for_robot():
    """Feeder should block until robot is home."""
    env = simpy.Environment()
    logger = EventLogger(env)
    plc = SafetyPLC(env, logger)

    # Simulate robot in window (clear the home event)
    plc.robot_is_home = env.event()
    plc.robot_state = RobotState.IN_WINDOW

    feeder_moved = False

    def feeder_process():
        nonlocal feeder_moved
        yield from plc.request_feeder_move()
        feeder_moved = True

    def robot_process():
        yield env.timeout(3.0)  # Robot works for 3 seconds
        plc.release_robot_entry()

    env.process(feeder_process())
    env.process(robot_process())

    # Run for 1 second - feeder should still be waiting
    env.run(until=1.0)
    assert not feeder_moved, "Feeder should be blocked by robot"

    # Run until completion - feeder should now have moved
    env.run(until=10.0)
    assert feeder_moved, "Feeder should have moved after robot returned home"


def test_no_deadlock():
    """Verify alternating access works correctly without deadlock."""
    env = simpy.Environment()
    logger = EventLogger(env)
    plc = SafetyPLC(env, logger)

    robot_cycles = 0
    feeder_cycles = 0

    def robot_process():
        nonlocal robot_cycles
        for _ in range(3):
            yield from plc.request_robot_entry()
            yield env.timeout(2.0)  # Robot works for 2 seconds
            plc.release_robot_entry()
            robot_cycles += 1

    def feeder_process():
        nonlocal feeder_cycles
        for _ in range(3):
            yield from plc.request_feeder_move()
            yield env.timeout(1.0)  # Feeder moves for 1 second
            plc.release_feeder_move()
            feeder_cycles += 1

    env.process(robot_process())
    env.process(feeder_process())
    env.run(until=30.0)

    # Both should complete all cycles without deadlock
    assert robot_cycles == 3, f"Robot completed {robot_cycles}/3 cycles"
    assert feeder_cycles == 3, f"Feeder completed {feeder_cycles}/3 cycles"


def test_robot_state_enforcement():
    """Robot must be HOME before requesting entry."""
    env = simpy.Environment()
    logger = EventLogger(env)
    plc = SafetyPLC(env, logger)

    # Set robot to invalid state
    plc.robot_state = RobotState.IN_WINDOW

    def robot_process():
        yield from plc.request_robot_entry()

    with pytest.raises(RuntimeError, match="Robot must be HOME"):
        env.process(robot_process())
        env.run()


def test_feeder_state_enforcement():
    """Feeder must be IDLE before requesting move."""
    env = simpy.Environment()
    logger = EventLogger(env)
    plc = SafetyPLC(env, logger)

    # Set feeder to invalid state
    plc.feeder_state = FeederState.MOVING

    def feeder_process():
        yield from plc.request_feeder_move()

    with pytest.raises(RuntimeError, match="Feeder must be IDLE"):
        env.process(feeder_process())
        env.run()


def test_idempotent_release():
    """Release methods should be safe to call multiple times."""
    env = simpy.Environment()
    logger = EventLogger(env)
    plc = SafetyPLC(env, logger)

    # Enter robot into window
    def robot_process():
        yield from plc.request_robot_entry()

    env.process(robot_process())
    env.run(until=1.0)

    # Release multiple times should not raise error
    plc.release_robot_entry()
    plc.release_robot_entry()
    plc.release_robot_entry()

    assert plc.robot_state == RobotState.HOME


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
