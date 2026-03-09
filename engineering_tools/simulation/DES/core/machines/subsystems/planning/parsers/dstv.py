import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Literal

@dataclass
class DSTVFeature:
    """
    Represents a single machine operation extracted from the NC1 file.
    """
    feature_type: Literal["HOLE", "CUT", "MARK"]
    face: Literal["v", "o", "u", "h"] # Front, Top, Bottom, Rear
    x_pos: float        # Position along the beam (mm)
    y_pos: float        # Position on the face (mm)
    diameter: float = 0.0     # For holes
    path_length: float = 0.0  # For cuts/scribing
    
    @property
    def rapid_penalty_mm(self) -> float:
        """
        Estimated additional travel for the robot to execute this.
        e.g. A 200mm circular cut requires 200mm of motion.
        """
        return self.path_length if self.path_length > 0 else (math.pi * self.diameter)

@dataclass
class DSTVData:
    """
    The raw data payload extracted from the .nc1 file.
    """
    filename: str
    profile_code: str  # e.g., "W12x40"
    material_grade: str # e.g., "A992"
    length_mm: float
    features: List[DSTVFeature] = field(default_factory=list)
    
    # Aggregates for quick simulation
    total_cut_path_mm: float = 0.0
    total_holes: int = 0
    
    def get_features_in_window(self, start_x: float, end_x: float) -> List[DSTVFeature]:
        """Returns all features located within a specific X-window."""
        return [f for f in self.features if start_x <= f.x_pos <= end_x]

class DSTVParser:
    """
    Reads standard DSTV (.nc1) files.
    Focuses on extraction of Motion and Process data.
    """
    def __init__(self):
        pass

    def parse(self, filepath: Path) -> DSTVData:
        if not filepath.exists():
            raise FileNotFoundError(f"DSTV file not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [line.strip() for line in f.readlines()]

        # --- 1. HEADER PARSING ---
        # ST block is strictly positional in the standard
        try:
            # Line index 0 is 'ST'
            profile_code = lines[1]
            material_grade = lines[2]
            # Line 4: Length, Height, FlangeWidth, WebThk, FlangeThk, Radius, Weight, PaintSurf
            dimensions = lines[4].split()
            length_mm = float(dimensions[0])
        except (IndexError, ValueError):
            raise ValueError(f"File {filepath.name} has a corrupt DSTV Header.")

        parsed_data = DSTVData(
            filename=filepath.name,
            profile_code=profile_code,
            material_grade=material_grade,
            length_mm=length_mm
        )

        # --- 2. BLOCK PARSING ---
        # We scan for block headers (BO, AK, IK, SI, etc.)
        i = 0
        current_face = "v" # Default to front/web if undefined
        
        while i < len(lines):
            line = lines[i]
            
            # Detect Block Headers (2 chars, Uppercase)
            if len(line) == 2 and line.isalpha() and line.isupper():
                block_type = line
                
                # The line immediately after a block header usually defines the FACE
                # Standard faces: v, o, u, h. 
                # Exception: ST and EN blocks do not have face lines.
                if block_type not in ['ST', 'EN'] and (i + 1) < len(lines):
                    potential_face = lines[i+1].lower()
                    if potential_face in ['v', 'o', 'u', 'h']:
                        current_face = potential_face
                        i += 1 # Advance past the face line
                
                i += 1
                
                # --- INNER BLOCK LOOP ---
                # Consume lines until we hit the next block or EOF
                while i < len(lines):
                    sub_line = lines[i]
                    
                    # Check if we hit a new block header
                    if len(sub_line) == 2 and sub_line.isalpha() and sub_line.isupper():
                        i -= 1 # Back up so the outer loop catches it
                        break
                    
                    # PROCESS THE BLOCK DATA
                    if block_type == 'BO': # BO = Holes (Bohrung)
                        self._parse_hole(sub_line, current_face, parsed_data)
                        
                    elif block_type in ['AK', 'IK']: # AK/IK = Contours (Copes)
                        # Contours are multi-line. We need to collect vertices.
                        # This is a simplified logic that grabs the first point as the location
                        # and sums the distances.
                        vertices = self._collect_contour_vertices(lines, i)
                        if vertices:
                            self._parse_contour(vertices, block_type, current_face, parsed_data)
                            # Advance i by len(vertices) - 1 because we consumed them
                            i += (len(vertices) - 1)
                    
                    i += 1
                continue
            
            i += 1

        return parsed_data

    def _parse_hole(self, line: str, face: str, data: DSTVData):
        """Helper to parse a single BO line."""
        parts = line.split()
        if len(parts) < 3: return
        
        try:
            # DSTV Standard: X_Pos, Y_Pos, Diameter, ...
            x = float(parts[0])
            y = float(parts[1])
            dia = float(parts[2])
            
            feat = DSTVFeature(
                feature_type="HOLE",
                face=face,
                x_pos=x,
                y_pos=y,
                diameter=dia,
                path_length=(math.pi * dia) # Circumference
            )
            data.features.append(feat)
            data.total_holes += 1
            data.total_cut_path_mm += feat.path_length
        except ValueError:
            pass # Skip malformed lines

    def _collect_contour_vertices(self, all_lines: List[str], start_index: int) -> List[tuple]:
        """Reads ahead to gather all X,Y points for a contour."""
        vertices = []
        idx = start_index
        while idx < len(all_lines):
            line = all_lines[idx]
            # Stop if we hit a block header
            if len(line) == 2 and line.isalpha(): 
                break
            
            parts = line.split()
            if len(parts) >= 2:
                try:
                    # DSTV Contour: X, Y, Radius...
                    x = float(parts[0])
                    y = float(parts[1])
                    vertices.append((x,y))
                except ValueError:
                    pass
            idx += 1
        return vertices

    def _parse_contour(self, vertices: List[tuple], type_str: str, face: str, data: DSTVData):
        """Calculates path length and centroid for a contour."""
        if not vertices: return