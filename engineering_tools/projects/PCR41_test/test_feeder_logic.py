import sys
from pathlib import Path

# Add project root to path to enable imports when run as script
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent.parent.parent
    sys.path.insert(0, str(project_root))

import simpy
from engineering_tools.simulation.core.logging.logger import EventLogger
from engineering_tools.simulation.core.machines.subsystems.conveyors.push_rod_feeder import LinearActuator
from engineering_tools.simulation.core.machines.subsystems.conveyors.cross_transfer import CrossTransfer, CrossTransferSpecs
from engineering_tools.simulation.core.machines.subsystems.conveyors.conveyor import ConveyorSpecs
from engineering_tools.simulation.core.machines.PCR41.indexer import Indexer
from engineering_tools.simulation.core.machines.subsystems.planning.parsers.dstv import DSTVParser

def test_full_sequence():
    env = simpy.Environment()
    logger = EventLogger(env)
    
    # 1. Setup Hardware
    # The Cross Transfer (Gatekeeper)
    xt_specs = CrossTransferSpecs() # Use defaults
    cross_transfer = CrossTransfer(env, logger, xt_specs, num_units=3) # Heavy duty!

    # The Feeder (Linear Axis)
    conveyor_specs = ConveyorSpecs(18000, 800, 150, 5000)
    push_rod = LinearActuator(env, logger, conveyor_specs, name="PushRod")

    # The Brain
    indexer = Indexer()
    
    # 2. Load Data
    parser = DSTVParser()
    beam = parser.parse(Path(__file__).parent / "sample_beam.nc1")
    plan = indexer.get_optimized_plan(beam)
    
    print(f"Plan generated: {len(plan)} stops required for {len(beam.features)} features.")

    # 3. Process
    def production_run():
        print(f"[{env.now:.2f}s] STARTING SIMULATION")
        
        # A. LOAD (Cross Transfer)
        print(f"[{env.now:.2f}s] Cross Transfer: Loading Beam...")
        yield env.process(cross_transfer.load_beam(beam_mass_kg=1500))
        
        # B. ACQUIRE (Push Rod)
        print(f"[{env.now:.2f}s] Push Rod: Clamping Beam...")
        yield env.process(push_rod.clamp.clamp())
        
        # C. PROCESS (Indexed Motion)
        for x_pos, features in plan:
            # 1. Move
            print(f"[{env.now:.2f}s] Push Rod: Indexing to X={x_pos:.1f}mm...")
            yield env.process(push_rod.move_to_position(x_pos, 1500))
            
            # 2. Cut
            print(f"[{env.now:.2f}s] Robot: Processing {len(features)} features at current station...")
            with logger.log_event("Process Group", "Robot", f"Cnt: {len(features)}"):
                 # Simulate Robot Work (1.0s per feature)
                 yield env.timeout(1.0 * len(features)) 

        # D. EJECT
        print(f"[{env.now:.2f}s] Push Rod: Unclamping/Ejecting...")
        yield env.process(push_rod.clamp.unclamp())

        # E. UNLOAD (Cross Transfer)
        print(f"[{env.now:.2f}s] Cross Transfer: Unloading Beam...")
        yield env.process(cross_transfer.load_beam(beam_mass_kg=1500))
        
        print(f"[{env.now:.2f}s] JOB COMPLETE")
        
    env.process(production_run())
    env.run()

if __name__ == "__main__":
    test_full_sequence()