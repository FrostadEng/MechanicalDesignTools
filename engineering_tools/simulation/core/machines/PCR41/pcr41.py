import simpy
from engineering_tools.simulation.subsystems.motion.conveyor import RollerConveyor, ConveyorSpecs
from engineering_tools.simulation.subsystems.processing.robot_arm import SixAxisRobot
from engineering_tools.simulation.subsystems.processing.tool_head import PlasmaTorch, FiberLaser

class PCR41_Assembly:
    def __init__(self, env: simpy.Environment, config="plasma"):
        self.env = env
        
        # 1. Define Subsystems
        # Infeed is heavy duty
        infeed_specs = ConveyorSpecs(length_mm=12000, max_speed_mm_sec=500, accel_mm_sec2=200, max_load_kg=5000)
        self.infeed = RollerConveyor(env, infeed_specs, "Infeed")
        
        # Robot
        self.robot = SixAxisRobot(env, rapid_speed_mm_min=30000)
        
        # Tooling (Configurable!)
        if config == "laser":
            self.tool = FiberLaser(power_kw=4.0)
        else:
            self.tool = PlasmaTorch(amperage=300)

    def run_job(self, beam_entity):
        # 1. Fetch Physics from your Mech_Core
        # beam_entity has a .aisc_profile string (e.g. "W12X40")
        # You use your existing library to get the mass!
        mass_kg = beam_entity.get_total_mass() 
        
        print(f"[{self.env.now:.1f}s] Loading {beam_entity.name} ({mass_kg:.1f} kg)...")
        
        # 2. Simulate Infeed (Physics-aware!)
        # Heavy beams take longer to accelerate
        travel_time = self.infeed.transfer_time(distance_mm=12000, beam_mass_kg=mass_kg)
        yield self.env.timeout(travel_time)
        
        # 3. Simulate Cutting
        print(f"[{self.env.now:.1f}s] Robot processing...")
        yield from self.robot.execute_program(
            cut_length_mm=beam_entity.cut_path_length,
            rapid_dist_mm=beam_entity.rapid_path_length,
            tool_obj=self.tool
        )
        
        print(f"[{self.env.now:.1f}s] Complete.")