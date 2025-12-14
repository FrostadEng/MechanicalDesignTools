import simpy

class SixAxisRobot:
    def __init__(self, env: simpy.Environment, rapid_speed_mm_min: float):
        self.env = env
        self.rapid_speed = rapid_speed_mm_min
        self.arm_resource = simpy.Resource(env, capacity=1)

    def execute_program(self, cut_length_mm: float, rapid_dist_mm: float, tool_obj):
        """
        Composes the cycle time from motion + tool physics.
        tool_obj could be a PlasmaTorch or FiberLaser instance.
        """
        with self.arm_resource.request() as req:
            yield req
            
            # 1. Rapid Moves (Air time)
            rapid_time_min = rapid_dist_mm / self.rapid_speed
            yield self.env.timeout(rapid_time_min * 60)
            
            # 2. Process Moves (Cutting)
            # Ask the TOOL how fast it can cut this material
            # (The robot can move fast, but the process might be slow)
            process_speed = tool_obj.get_speed_mm_min() 
            cut_time_min = cut_length_mm / process_speed
            yield self.env.timeout(cut_time_min * 60)