"""Event logger for capturing simulation events for Gantt chart visualization."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from contextlib import contextmanager
import simpy


@dataclass
class Event:
    """
    Represents a single simulation event with start/end times.

    Supports hierarchical event tracking for nested operations.

    Attributes:
        action: Name of the action (e.g., "Operator: Walk In", "Robot: MIG Weld")
        resource: Resource performing action (e.g., "Operator", "Robot", "Workstation")
        start_time: When action started (simulation time)
        end_time: When action ended (simulation time)
        cycle_num: Which production cycle this belongs to
        part_id: Identifier for the part being processed
        side: Which fixture or position the part is within the process ("A", "B", etc.)
        parent_id: ID of parent event for hierarchical tracking (None for top-level)
        level: Hierarchy depth (0 for top-level, 1 for child, 2 for grandchild, etc.)
        metadata: Additional context (operation name, part size, etc.)
    """
    action: str
    resource: str
    start_time: float
    end_time: Optional[float] = None
    cycle_num: int = 0
    part_id: str = ""
    side: str = ""
    parent_id: Optional[int] = None
    level: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Calculate event duration."""
        if self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    def complete(self, end_time: float):
        """Mark event as complete with end time."""
        self.end_time = end_time

    def is_top_level(self) -> bool:
        """Check if this is a top-level event (no parent)."""
        return self.parent_id is None

    def is_child_of(self, event_id: int) -> bool:
        """Check if this event is a child of the specified event."""
        return self.parent_id == event_id


class EventLogger:
    """
    Captures simulation events for Gantt chart visualization.

    Supports both manual start/end and context-managed logging with hierarchical events.

    Usage:
        logger = EventLogger(env)

        # Manual start/end
        event_id = logger.start_event(
            action="Operator: Load Part",
            resource="Operator",
            cycle_num=5,
            part_id="Part-123"
        )
        # ... simulation time passes ...
        logger.end_event(event_id)

        # Context-managed (recommended)
        with logger.log_event("Operator: Load Part", "Operator", cycle_num=5):
            # ... simulation time passes ...
            pass  # Event automatically completed

        # Hierarchical events
        with logger.log_event("Production Cycle", "Cell", cycle_num=1) as parent_id:
            with logger.log_event("Load Parts", "Operator", parent_id=parent_id):
                pass
            with logger.log_event("Weld", "Robot", parent_id=parent_id):
                pass
    """

    def __init__(self, env: simpy.Environment):
        """
        Initialize event logger.

        Args:
            env: SimPy environment (for current time)
        """
        self.env = env
        self.events: List[Event] = []
        self._active_events: Dict[int, Event] = {}
        self._next_id = 0
        self._event_stack: List[int] = []  # Stack for tracking nested events

    def start_event(
        self,
        action: str,
        resource: str,
        cycle_num: int = 0,
        part_id: str = "",
        side: str = "",
        parent_id: Optional[int] = None,
        **metadata
    ) -> int:
        """
        Start logging an event.

        Args:
            action: Description of action (e.g., "Operator: Walk In")
            resource: Which resource(s) (e.g., "Operator", "Robot")
            cycle_num: Production cycle number
            part_id: Part identifier
            side: Fixture or position within process ("A", "B", etc.)
            parent_id: ID of parent event for hierarchical tracking
            **metadata: Additional context

        Returns:
            Event ID for later completion
        """
        # Determine hierarchy level
        level = 0
        if parent_id is not None and parent_id in self._active_events:
            level = self._active_events[parent_id].level + 1

        event = Event(
            action=action,
            resource=resource,
            start_time=self.env.now,
            cycle_num=cycle_num,
            part_id=part_id,
            side=side,
            parent_id=parent_id,
            level=level,
            metadata=metadata
        )

        event_id = self._next_id
        self._next_id += 1

        self._active_events[event_id] = event
        return event_id

    def end_event(self, event_id: int):
        """
        Complete an event with current simulation time.

        Args:
            event_id: ID returned from start_event()
        """
        if event_id not in self._active_events:
            return

        event = self._active_events.pop(event_id)
        event.complete(self.env.now)
        self.events.append(event)

    @contextmanager
    def log_event(
        self,
        action: str,
        resource: str,
        cycle_num: int = 0,
        part_id: str = "",
        side: str = "",
        parent_id: Optional[int] = None,
        **metadata
    ):
        """
        Context manager for logging an event.

        Automatically starts and ends the event, ensuring proper cleanup.
        Returns the event_id which can be used as parent_id for nested events.

        Args:
            action: Description of action
            resource: Which resource(s)
            cycle_num: Production cycle number
            part_id: Part identifier
            side: Fixture or position
            parent_id: ID of parent event for hierarchy
            **metadata: Additional context

        Yields:
            Event ID that can be used as parent_id for child events

        Example:
            with logger.log_event("Load Parts", "Operator", cycle_num=1) as parent:
                with logger.log_event("Load Part 1", "Operator", parent_id=parent):
                    yield env.timeout(5)
        """
        # If no parent_id specified, check if we're nested in another log_event
        if parent_id is None and self._event_stack:
            parent_id = self._event_stack[-1]

        event_id = self.start_event(
            action=action,
            resource=resource,
            cycle_num=cycle_num,
            part_id=part_id,
            side=side,
            parent_id=parent_id,
            **metadata
        )

        # Push to stack for automatic parent tracking
        self._event_stack.append(event_id)

        try:
            yield event_id
        finally:
            # Pop from stack
            if self._event_stack and self._event_stack[-1] == event_id:
                self._event_stack.pop()
            # End the event
            self.end_event(event_id)

    def get_events(
        self,
        resource: Optional[str] = None,
        cycle_range: Optional[tuple] = None
    ) -> List[Event]:
        """
        Retrieve logged events with optional filtering.

        Args:
            resource: Filter by resource name
            cycle_range: Tuple of (min_cycle, max_cycle) inclusive

        Returns:
            List of matching events
        """
        filtered = self.events

        if resource:
            filtered = [e for e in filtered if e.resource == resource]

        if cycle_range:
            min_cycle, max_cycle = cycle_range
            filtered = [e for e in filtered if min_cycle <= e.cycle_num <= max_cycle]

        return filtered

    def get_cycle_range(self) -> tuple:
        """
        Get the range of cycle numbers in logged events.

        Returns:
            Tuple of (min_cycle, max_cycle)
        """
        if not self.events:
            return (0, 0)

        cycles = [e.cycle_num for e in self.events]
        return (min(cycles), max(cycles))

    def get_steady_state_cycles(
        self,
        skip_first: int = 2,
        skip_last: int = 2,
        num_cycles: int = 3
    ) -> tuple:
        """
        Identify steady-state cycles (middle of production run).

        Args:
            skip_first: Number of startup cycles to skip
            skip_last: Number of shutdown cycles to skip
            num_cycles: Number of steady-state cycles to return

        Returns:
            Tuple of (start_cycle, end_cycle) for steady state range
        """
        min_cycle, max_cycle = self.get_cycle_range()

        # Calculate steady-state window
        available_cycles = max_cycle - min_cycle + 1 - skip_first - skip_last

        if available_cycles < num_cycles:
            # Not enough cycles, return what we have
            start = min_cycle + skip_first
            end = max_cycle - skip_last
        else:
            # Take from middle
            start = min_cycle + skip_first
            end = start + num_cycles - 1

        return (start, end)

    def get_unique_actions(self) -> List[str]:
        """
        Get list of all unique actions (for Gantt chart Y-axis).

        Returns:
            Sorted list of unique action names
        """
        actions = set(e.action for e in self.events)
        return sorted(actions)

    def get_time_range(self, cycle_range: Optional[tuple] = None) -> tuple:
        """
        Get the time range for events.

        Args:
            cycle_range: Optional tuple of (min_cycle, max_cycle)

        Returns:
            Tuple of (start_time, end_time)
        """
        filtered = self.get_events(cycle_range=cycle_range)

        if not filtered:
            return (0.0, 0.0)

        start = min(e.start_time for e in filtered)
        end = max(e.end_time for e in filtered if e.end_time is not None)

        return (start, end)

    def get_child_events(self, parent_id: int) -> List[Event]:
        """
        Get all child events of a specific parent event.

        Args:
            parent_id: ID of the parent event

        Returns:
            List of child events
        """
        return [e for e in self.events if e.parent_id == parent_id]

    def get_top_level_events(self) -> List[Event]:
        """
        Get all top-level events (no parent).

        Returns:
            List of top-level events
        """
        return [e for e in self.events if e.is_top_level()]

    def get_event_tree(self, root_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get hierarchical event tree structure.

        Args:
            root_id: Root event ID (None for all top-level events)

        Returns:
            List of event dictionaries with nested 'children' lists
        """
        def build_tree(parent_id: Optional[int]) -> List[Dict[str, Any]]:
            children = [e for e in self.events if e.parent_id == parent_id]
            result = []
            for event in children:
                event_dict = {
                    'action': event.action,
                    'resource': event.resource,
                    'start_time': event.start_time,
                    'end_time': event.end_time,
                    'duration': event.duration,
                    'level': event.level,
                    'cycle_num': event.cycle_num,
                    'part_id': event.part_id,
                    'side': event.side,
                    'metadata': event.metadata,
                    'children': build_tree(self.events.index(event))
                }
                result.append(event_dict)
            return result

        if root_id is not None:
            # Build tree from specific root
            return build_tree(root_id)
        else:
            # Build tree from all top-level events
            return build_tree(None)

    def get_events_by_level(self, level: int) -> List[Event]:
        """
        Get all events at a specific hierarchy level.

        Args:
            level: Hierarchy level (0 = top-level, 1 = first child, etc.)

        Returns:
            List of events at the specified level
        """
        return [e for e in self.events if e.level == level]

    def clear(self):
        """Clear all logged events (for new simulation run)."""
        self.events.clear()
        self._active_events.clear()
        self._event_stack.clear()
        self._next_id = 0
