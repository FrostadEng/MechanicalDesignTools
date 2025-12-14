from dataclasses import dataclass
from mech_core.standards.fasteners import geometry, materials
from mech_core.standards.units import ureg, Q_

@dataclass
class Bolt:
    """A specific instance of a bolt (Geometry + Material)"""
    thread: geometry.MetricThread
    head: geometry.HexHead
    material: materials.BoltMaterial
    
    @property
    def proof_load(self) -> Q_:
        """Returns Force in Newtons"""
        return (self.thread.stress_area * self.material.proof_strength).to(ureg.newton)
    
    @property
    def shear_capacity(self) -> Q_:
        """
        Approximate Shear Yield.
        Distortion Energy Theory (Von Mises) says Shear Yield = 0.577 * Tensile Yield
        """
        return (0.577 * self.material.yield_strength * self.thread.stress_area).to(ureg.newton)

# --- FACTORY ---
def create_standard_bolt(size: str, grade: str) -> Bolt:
    """
    The easiest way to make a bolt.
    example: b = create_standard_bolt("M10", "8.8")
    """
    return Bolt(
        thread=geometry.get_metric_thread(size),
        head=geometry.get_hex_head(size),
        material=materials.get_iso_property_class(grade)
    )