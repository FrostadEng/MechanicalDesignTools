"""
mech_core/standards/materials/inventory.py
Material stock and thickness availability management.
"""
from pathlib import Path
import json
from ..units import ureg, Q_

class MaterialStockManager:
    """
    Singleton manager for material stock/thickness availability.
    Handles lazy loading of thickness database and provides inventory queries.
    """

    _instance = None
    _database = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_database(self):
        """Lazy load the thickness database from JSON"""
        if self._database is None:
            json_path = Path(__file__).parent / "data" / "standard_thicknesses.json"
            with open(json_path, 'r') as f:
                self._database = json.load(f)
        return self._database

    def get_plate_thickness(
        self,
        required: Q_,
        system: str = "metric"
    ) -> Q_:
        """
        Get next available plate thickness >= required.

        Args:
            required: Minimum thickness needed
            system: "metric" or "imperial"

        Returns:
            Next standard plate thickness (with units)

        Example:
            >>> from mech_core.standards.materials import stock
            >>> stock.get_plate_thickness(4.36 * ureg.mm)
            <Quantity(5.0, 'millimeter')>
        """
        return self._get_standard_thickness(required, "plate", system)

    def get_sheet_thickness(
        self,
        required: Q_,
        system: str = "metric"
    ) -> Q_:
        """
        Get next available sheet thickness >= required.

        Args:
            required: Minimum thickness needed
            system: "metric" or "imperial"

        Returns:
            Next standard sheet thickness (with units)

        Example:
            >>> from mech_core.standards.materials import stock
            >>> stock.get_sheet_thickness(1.3 * ureg.mm)
            <Quantity(1.5, 'millimeter')>
        """
        return self._get_standard_thickness(required, "sheet", system)

    def _get_standard_thickness(
        self,
        required: Q_,
        category: str,
        system: str
    ) -> Q_:
        """Internal method to find next standard thickness"""
        db = self._load_database()

        if category not in db:
            raise ValueError(f"Unknown category '{category}'. Use: {list(db.keys())}")

        # Determine unit and standards list
        if system == "metric":
            standards = db[category]["metric_mm"]
            unit = ureg.mm
        elif system == "imperial":
            standards = db[category]["imperial_inch"]
            unit = ureg.inch
        else:
            raise ValueError(f"Unknown system '{system}'. Use 'metric' or 'imperial'")

        # Convert required to target unit
        req_value = required.to(unit).magnitude

        # Find next size up
        for std_thickness in sorted(standards):
            if std_thickness >= req_value:
                return std_thickness * unit

        # If nothing found, use largest available (with warning)
        max_thickness = max(standards)
        print(f"[WARNING] Required {required:.2f~} exceeds max standard {max_thickness}{unit:~}. Using max.")
        return max_thickness * unit

    def check_availability(
        self,
        material_name: str,
        category: str = "plate"
    ) -> bool:
        """
        Check if material is available in category.

        Args:
            material_name: Material designation (e.g., "ASTM A36")
            category: "plate" or "sheet"

        Returns:
            True if material is listed

        Example:
            >>> from mech_core.standards.materials import stock
            >>> stock.check_availability("ASTM A36", "plate")
            True
            >>> stock.check_availability("AR500", "sheet")
            False
        """
        db = self._load_database()

        if category not in db:
            return False

        return material_name in db[category]["materials"]

    def list_thicknesses(
        self,
        category: str = "plate",
        system: str = "metric"
    ) -> list[Q_]:
        """
        Get all available thicknesses for a category.

        Args:
            category: "plate" or "sheet"
            system: "metric" or "imperial"

        Returns:
            Sorted list of thicknesses with units

        Example:
            >>> from mech_core.standards.materials import stock
            >>> stock.list_thicknesses("plate", "metric")
            [<Quantity(3.0, 'mm')>, <Quantity(4.0, 'mm')>, ...]
        """
        db = self._load_database()

        if system == "metric":
            standards = db[category]["metric_mm"]
            unit = ureg.mm
        else:
            standards = db[category]["imperial_inch"]
            unit = ureg.inch

        return [t * unit for t in sorted(standards)]

# Create singleton instance
stock = MaterialStockManager()
