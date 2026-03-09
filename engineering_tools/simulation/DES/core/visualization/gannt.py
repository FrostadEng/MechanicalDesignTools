from typing import Optional, Dict, Any
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# UPDATE: Pointing to your new logger location
from ..logging.logger import EventLogger

class GanttChart:
    """
    Generates manufacturing cycle Gantt charts from event logs.
    Shows all cell actions on Y-axis, time on X-axis.
    """

    # Color palette for cycles (12 distinct colors)
    CYCLE_COLORS = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', 
        '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', 
        '#bcbd22', '#17becf', '#aec7e8', '#ffbb78'
    ]

    def __init__(self, event_logger: EventLogger):
        self.logger = event_logger

    def generate(
        self,
        output_path: str,
        steady_state: bool = True,
        skip_first: int = 1, # Modified default for smaller batch tests
        skip_last: int = 1,
        num_cycles: int = 5,
        figsize: tuple = (16, 10),
        title: Optional[str] = None
    ):
        # Determine which cycles to show
        if steady_state:
            cycle_range = self.logger.get_steady_state_cycles(
                skip_first=skip_first,
                skip_last=skip_last,
                num_cycles=num_cycles
            )
        else:
            cycle_range = self.logger.get_cycle_range()

        # Get filtered events
        events = self.logger.get_events(cycle_range=cycle_range)

        if not events:
            print(f"No events found for cycle range {cycle_range}!")
            return

        # ---------------------------------------------------------
        # CRITICAL CHANGE FOR MACHINE UTILIZATION VIEW
        # We plot RESOURCES on Y-axis, not ACTIONS.
        # This lets you see if the Robot is busy vs. the Conveyor.
        # ---------------------------------------------------------
        resources = sorted(list(set(e.resource for e in events)))
        row_map = {res: i for i, res in enumerate(resources)}

        # Get time range for X-axis
        time_start, time_end = self.logger.get_time_range(cycle_range=cycle_range)

        # Create figure
        _, ax = plt.subplots(figsize=figsize)

        # Assign colors to cycles
        min_cycle, max_cycle = cycle_range
        cycle_colors = {}
        for i, cycle_num in enumerate(range(min_cycle, max_cycle + 1)):
            cycle_colors[cycle_num] = self.CYCLE_COLORS[i % len(self.CYCLE_COLORS)]

        # Plot bars for each event
        for event in events:
            if event.end_time is None:
                continue

            # Skip "Container" events (Level 0) if they just clutter the view, 
            # or keep them if you want to see the whole job bar. 
            # For detailed Gantt, usually Level 1+ is better.
            if event.level == 0: 
                alpha = 0.3 # Make parent bars transparent
            else:
                alpha = 0.9

            row = row_map[event.resource] # Y-Axis is Resource
            start = event.start_time - time_start
            duration = event.duration
            color = cycle_colors.get(event.cycle_num, '#cccccc')

            # Draw bar
            ax.barh(
                y=row,
                width=duration,
                left=start,
                height=0.6,
                color=color,
                edgecolor='black',
                linewidth=0.5,
                alpha=alpha
            )

            # Label the Action inside the bar (e.g., "Cut", "Rapid")
            if duration > (time_end - time_start) * 0.05:
                ax.text(
                    start + duration / 2,
                    row,
                    event.action, # Text is the Action Name
                    ha='center',
                    va='center',
                    fontsize=8,
                    color='white',
                    weight='bold'
                )

        # Configure Y-axis
        ax.set_yticks(range(len(resources)))
        ax.set_yticklabels(resources, fontsize=10, weight='bold')
        ax.set_ylim(-0.5, len(resources) - 0.5)

        # Configure X-axis
        ax.set_xlabel('Simulation Time (seconds)', fontsize=11, weight='bold')
        ax.set_xlim(0, time_end - time_start)

        # Title
        if title is None:
            title = f"Throughput Analysis - Cycles {min_cycle} to {max_cycle}"
        ax.set_title(title, fontsize=14, weight='bold', pad=20)

        # Legend
        legend_patches = [
            mpatches.Patch(color=cycle_colors[c], label=f'Cycle {c}') 
            for c in range(min_cycle, max_cycle + 1)
        ]
        ax.legend(handles=legend_patches, title='Beam Index', loc='upper right')

        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        print(f"Gantt chart saved to: {output_path}")

    def generate_summary_report(self, cycle_range: Optional[tuple] = None) -> Dict[str, Any]:
        """Generate summary statistics for the visualized cycles."""
        events = self.logger.get_events(cycle_range=cycle_range)
        if not events: return {}

        total_time = max(e.end_time for e in events if e.end_time) - \
                     min(e.start_time for e in events)

        # Utilization Logic
        resources = set(e.resource for e in events)
        utilization = {}
        for res in resources:
            # Sum duration of events for this resource
            # Filter to leaf nodes (level > 0) to avoid double counting parents
            res_events = [e for e in events if e.resource == res and e.level > 0]
            active_time = sum(e.duration for e in res_events)
            utilization[res] = (active_time / total_time) * 100

        min_cycle, max_cycle = cycle_range if cycle_range else self.logger.get_cycle_range()
        num_cycles = max_cycle - min_cycle + 1
        
        return {
            'total_time_sec': round(total_time, 2),
            'beams_processed': num_cycles,
            'sec_per_beam': round(total_time / num_cycles, 2) if num_cycles else 0,
            'utilization_pct': {k: round(v, 1) for k, v in utilization.items()}
        }