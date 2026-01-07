# Engineering Stack (Context7 Profile)

These are the **Approved Libraries**. The Builder (Claude) has access to their documentation via Context7.
**Constraint:** Prioritize these libraries over custom logic.

## 🏭 Simulation & Robotics (Active Agents)
- **simpy**: Process-based Discrete Event Simulation (DES). *Use for: Queues, resources, process timing.*
- **genesis**: Embodied AI / Physics engine. *Use for: Robotics simulation, photo-realistic rendering.*
- **ardupilot**: Vehicle autopilot. *Use for: Drone/Rover control logic.*
- **ros2**: Robot Operating System interfaces.

## 📐 Structural, Thermal & Fluids (Physics)
- **pint**: Unit handling. **MANDATORY**: All physical quantities must use Pint.
- **jwock82/pynite**: 3D Structural FEA (Elastic). *Use for: Beam/Frame analysis.*
- **calebbell/fluids**: Fluid dynamics. *Use for: Pressure drop, friction, piping.*
- **calebbell/thermo**: Thermodynamics/Phase Equilibrium.
- **pymodbus**: Industrial communication.

## 🧮 Optimization & Mathematics
- **google/or-tools**: Combinatorial optimization. *Use for: Routing, scheduling, constraint programming.*
- **pyomo**: Algebraic modeling for optimization.
- **scikit-portfolio**: Portfolio/Hyperparameter optimization.
- **numpy / scipy**: Scientific computing and spatial algorithms.
- **sympy**: Symbolic math (Calculus/Algebra).
- **numba**: JIT compiler. *Use for: Speeding up heavy loops.*

## 🧊 Geometry, CAD & Meshing
- **cadquery**: Code-based parametric 3D CAD.
- **freecad**: Parametric 3D modeler.
- **shapely**: 2D planar geometry analysis.
- **pyvista**: 3D plotting/mesh analysis (VTK interface).
- **trimesh / pymesh / meshio**: Mesh loading, processing, and conversion.

## 📊 Data & Visualization
- **pandas / xarray**: Labelled data and Multi-dimensional arrays.
- **matplotlib / seaborn**: Static plotting.
- **streamlit**: Interactive web apps/dashboards.
- **openpyxl**: Excel interaction.

## 🛠 Utilities & Infrastructure
- **pydantic**: Data validation and schema definition.
- **sqlalchemy**: Database toolkit.
- **yaml**: Config file parsing.
- **pyinstaller**: Packaging apps.
- **pyscript**: Running Python in browser.

## 🧪 Testing & Quality
- **pytest**: Core test framework.
- **hypothesis**: Property-based testing. *Use for: Finding edge cases in physics logic.*
- **flake8**: Style enforcement.

## 🖨 Manufacturing (Hardware Specific)
- **bambu_lab**: API for Bambu Lab printers.