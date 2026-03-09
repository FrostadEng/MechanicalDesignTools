from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, TYPE_CHECKING
import simpy

if TYPE_CHECKING:
    from ..robots.robot_arm import RobotArm
    from ..planning.parsers.dstv import DSTVFeature
    from ....entities.beam import BeamEntity

@dataclass
class TCP:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

class ManufacturingTool(ABC):
    def __init__(self, name: str, mass_kg: float, tcp_offset: List[float]):
        self.name = name
        self.mass_kg = mass_kg
        self.tcp = TCP(*tcp_offset)

    @abstractmethod
    def process_feature(self, env: simpy.Environment, robot: 'RobotArm', feature: 'DSTVFeature', beam: 'BeamEntity'):
        """
        The Tool orchestrates the Robot's motion for this feature.
        Now context-aware of the Beam material and thickness!
        """
        yield env.timeout(0)