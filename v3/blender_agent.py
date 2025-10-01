"""Core agent class"""

from schemas import ObjectCreation, CurveCreation, SurfaceCreation, ObjectDeletion, ObjectManipulation, ActionRequest, MaterialProperties
from openai import OpenAI
import subprocess
import tempfile
import time
import math
from typing import Optional

class SchemaBlenderAgent:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.blender_path = "/Applications/Blender.app/Contents/MacOS/Blender"
        self.used_names = set()  # Track used object names throughout a session; we want object names to be unique throughout a session for better tracking of events in the past
        self.objects_registry = []  # Track created objects for listing/deletion
        
        # Create session identifier for unique file names
        self.session_id = int(time.time())
        self.session_blend_file = f"result_{self.session_id}.blend"
        self.session_render_file = f"result_render_{self.session_id}.png"
        
        print(f"Session ID: {self.session_id}")
        print(f"Scene file: {self.session_blend_file}")
        print(f"Render file: {self.session_render_file}")
        
        # Common colors
        self.color_presets = {
            "red": (1.0, 0.0, 0.0),
            "green": (0.0, 1.0, 0.0),
            "blue": (0.0, 0.0, 1.0),
            "yellow": (1.0, 1.0, 0.0),
            "purple": (1.0, 0.0, 1.0),
            "cyan": (0.0, 1.0, 1.0),
            "white": (1.0, 1.0, 1.0),
            "black": (0.0, 0.0, 0.0),
            "gray": (0.5, 0.5, 0.5),
            "grey": (0.5, 0.5, 0.5)
        }
    
    def add_to_registry(self, name: str):
        """Add object to registry"""
        if name not in self.objects_registry:
            self.objects_registry.append(name)
            
    def remove_from_registry(self, name: str):
        """Remove object from registry"""
        if name in self.objects_registry:
            self.objects_registry.remove(name)
            
    def clear_registry(self):
        """Clear all objects from registry"""
        self.objects_registry.clear()
        
    def list_objects_from_registry(self):
        """List objects from local registry"""
        if self.objects_registry:
            print(f"\nAvailable objects in current session:")
            for i, name in enumerate(self.objects_registry, 1):
                print(f"  {i}. {name}")
            return self.objects_registry
        else:
            print("\nNo objects in the current session")
            return []
    
    def generate_unique_name(self, base_name: str) -> str:
        """Generate a unique name by adding numbers if needed"""
        if base_name not in self.used_names:
            return base_name
        
        counter = 1
        while f"{base_name}_{counter}" in self.used_names:
            counter += 1
        return f"{base_name}_{counter}"
    
    def validate_name(self, requested_name: str) -> str:
        """Validate and potentially modify the requested name to ensure uniqueness"""
        if requested_name in self.used_names:
            unique_name = self.generate_unique_name(requested_name)
            print(f"Note: Name '{requested_name}' already exists. Using '{unique_name}' instead.")
            return unique_name
        return requested_name
    
    def parse_user_request(self, user_input: str) -> ActionRequest:
        """Parse user input using structured output for all action types"""
        
        # Include color presets and current objects in the system prompt
        color_info = ", ".join([f"{name}: {rgb}" for name, rgb in self.color_presets.items()])
        current_objects = ", ".join(self.objects_registry) if self.objects_registry else "none"
        
        system_prompt = f"""You are a 3D Blender modeling assistant. Parse user requests and determine the action type.

CURRENT OBJECTS IN SCENE: {current_objects}

SUPPORTED ACTIONS:
1. CREATE: "create", "make", "add" + object type (cube/sphere/cylinder)
2. CREATE_CURVE: "create curve", "make curve", "bezier curve", "curved path" + control points
3. CREATE_SURFACE: "create surface", "make surface", "extrude curve", "revolve curve", "create plane"
4. LIST: "list", "show", "what objects" 
5. DELETE: "delete", "remove" + object name OR "delete all"
6. MANIPULATE: "move", "scale", "rotate" + object name + parameters
7. VIEW: "view", "show scene", "open blender", "display scene"
8. HELP: "help", "guide", "what can I do", "instructions"

FOR CREATE ACTIONS:
- object_type: Must be exactly "cube", "sphere", or "cylinder"
- name: Generate a descriptive name if not provided that is not already used
- location: Use coordinates if mentioned, default (0,0,0)
- size: Default 1.0 if not specified
- color: Convert color names to RGB. Example colors are: {color_info}
- material: Optional material type - "metallic", "glass", "emission", "plastic", "rough" with properties:
  * metallic: 0.0-1.0 (0=non-metal, 1=pure metal)
  * roughness: 0.0-1.0 (0=mirror, 1=completely rough)
  * emission_strength: 0+ (glow intensity)
  * transparency: 0.0-1.0 (0=opaque, 1=transparent)

FOR CREATE_CURVE ACTIONS:
- curve_type: "bezier", "nurbs", or "poly" (poly for simple straight-line segments)
- name: Generate descriptive curve name if not provided
- control_points: Extract coordinates from user input, minimum 2 points required. For "spiral" curves, use empty list [] to generate automatically
- extrude_depth: For 3D curves, default 0.0
- bevel_depth: For rounded edges, default 0.0
- resolution: Smoothness (1-64), default 12
- dimensions: "2D" or "3D", default "3D"
- color: IMPORTANT - Convert color names to RGB values using these presets: {color_info}
- material: Same material options as objects

FOR CREATE_SURFACE ACTIONS:
- surface_type: "extrude", "revolve", "plane", or "grid"
- name: Generate descriptive surface name if not provided
- base_curve: Required for "extrude" and "revolve" types, must match existing curve
- extrude_distance: For extrude surfaces, default 1.0
- revolve_axis: X, Y, or Z axis for revolving, default "Z"
- width/height: For plane/grid surfaces, default 2.0
- subdivisions: For grid surfaces, default 1
- color: Convert color names to RGB using presets: {color_info}
- material: Same material options as objects

FOR DELETE ACTIONS:
- action: "delete_specific" for named object, "delete_all" for all objects
- object_name: Required for delete_specific, must match existing object

FOR MANIPULATE ACTIONS:
- manipulation_type: "move", "scale", or "rotate"
- object_name: Required, must match existing object
- MOVE: move_x, move_y, move_z (relative offsets, default 1 if not specified)
- SCALE: scale_uniform OR scale_x/scale_y/scale_z (scale factors, default 2.0 if not specified)
- ROTATE: rotate_x, rotate_y, rotate_z (degrees, default 90 degrees if not specified)

Examples:
- "create red bezier curve from (0,0,0) to (2,2,2) to (4,0,0)" -> control_points=[[0,0,0], [2,2,2], [4,0,0]], color_r=1.0, color_g=0.0, color_b=0.0
- "create metallic blue sphere" -> material_type="metallic", metallic=1.0, color_r=0.0, color_g=0.0, color_b=1.0
- "create glass cube with transparency 0.8" -> material_type="glass", transparency=0.8
- "create glowing green cylinder with emission 2.0" -> material_type="emission", emission_strength=2.0, color_r=0.0, color_g=1.0, color_b=0.0
- "create rough red plane" -> material_type="rough", roughness=0.9, color_r=1.0, color_g=0.0, color_b=0.0
- "extrude my bezier curve by 2 units" -> surface_type="extrude", base_curve="bezier curve", extrude_distance=2.0
- "revolve curved path around Z axis" -> surface_type="revolve", base_curve="curved path", revolve_axis="Z"
- "move cube1 by 2,3,1" -> move_x=2, move_y=3, move_z=1
- "scale sphere uniformly by 2" -> scale_uniform=2

Determine the action type and fill appropriate parameters."""

        try:
            completion = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                response_format=ActionRequest
            )
            
            return completion.choices[0].message.parsed
            
        except Exception as e:
            print(f"Error parsing request: {e}")
            return None

    def analyze_missing_attributes(self, user_input: str, parsed_obj: ObjectCreation):
        """Analyze which attributes were missing from user input and inform them"""
        user_lower = user_input.lower()
        
        # Track what was explicitly provided vs defaulted
        provided = []
        defaulted = []
        
        # Check object type (always required)
        if any(obj_type in user_lower for obj_type in ["cube", "sphere", "cylinder"]):
            provided.append("object type")
        
        # Check name
        if "name" in user_lower or "call" in user_lower:
            provided.append("name")
        else:
            defaulted.append(f"name (defaulted to '{parsed_obj.name}')")
        
        # Check location  
        has_coordinates = any(coord in user_input for coord in ["(", "at ", "position"])
        if has_coordinates:
            provided.append("location")
        else:
            if parsed_obj.location_x != 0 or parsed_obj.location_y != 0 or parsed_obj.location_z != 0:
                provided.append("location")
            else:
                defaulted.append("location (defaulted to origin 0,0,0)")
        
        # Check size
        if "size" in user_lower or "scale" in user_lower or "radius" in user_lower:
            provided.append("size")
        else:
            if parsed_obj.size != 1.0:
                provided.append("size")
            else:
                defaulted.append("size (defaulted to 1.0)")
        
        # Check color
        has_color = any(color in user_lower for color in self.color_presets.keys()) or "color" in user_lower
        if has_color:
            provided.append("color")
        else:
            if parsed_obj.color_r != 0.8 and parsed_obj.color_g != 0.8 and parsed_obj.color_b != 0.8:
                provided.append("color")
            else:
                defaulted.append("color (defaulted to gray)")
        
        # Show analysis
        if defaulted:
            print(f"\nNote: The following attributes were missing, so I provided default values:")
            for attr in defaulted:
                print(f"  - {attr}")
            print("Let me know if you want to change any of these defaults.")
        
        if provided:
            print(f"\nProvided attributes: {', '.join(provided)}")

    def analyze_missing_curve_attributes(self, user_input: str, parsed_curve: CurveCreation):
        """Analyze which curve attributes were missing from user input and inform them"""
        user_lower = user_input.lower()
        
        provided = []
        defaulted = []
        
        # Check curve type
        if any(curve_type in user_lower for curve_type in ["bezier", "nurbs", "path"]):
            provided.append("curve type")
        
        # Check name
        if "name" in user_lower or "call" in user_lower:
            provided.append("name")
        else:
            defaulted.append(f"name (defaulted to '{parsed_curve.name}')")
        
        # Check control points
        if "point" in user_lower or any(coord in user_input for coord in ["(", ","]):
            provided.append("control points")
        else:
            defaulted.append(f"control points (defaulted to {len(parsed_curve.control_points)} points)")
        
        # Check curve properties
        if "extrude" in user_lower or "depth" in user_lower:
            provided.append("extrude depth")
        elif parsed_curve.extrude_depth != 0.0:
            provided.append("extrude depth")
        else:
            defaulted.append("extrude depth (defaulted to 0.0)")
        
        if "bevel" in user_lower:
            provided.append("bevel depth")
        elif parsed_curve.bevel_depth != 0.0:
            provided.append("bevel depth")
        else:
            defaulted.append("bevel depth (defaulted to 0.0)")
        
        if "resolution" in user_lower or "smooth" in user_lower:
            provided.append("resolution")
        elif parsed_curve.resolution != 12:
            provided.append("resolution")
        else:
            defaulted.append("resolution (defaulted to 12)")
        
        # Check color
        has_color = any(color in user_lower for color in self.color_presets.keys()) or "color" in user_lower
        if has_color:
            provided.append("color")
        else:
            if parsed_curve.color_r != 0.8 or parsed_curve.color_g != 0.8 or parsed_curve.color_b != 0.8:
                provided.append("color")
            else:
                defaulted.append("color (defaulted to gray)")
        
        # Show analysis
        if defaulted:
            print(f"\nNote: The following curve attributes were missing, so I provided default values:")
            for attr in defaulted:
                print(f"  - {attr}")
            print("Let me know if you want to change any of these defaults.")
        
        if provided:
            print(f"\nProvided curve attributes: {', '.join(provided)}")

    def analyze_missing_surface_attributes(self, user_input: str, parsed_surface: SurfaceCreation):
        """Analyze which surface attributes were missing from user input and inform them"""
        user_lower = user_input.lower()
        
        provided = []
        defaulted = []
        
        # Check surface type
        if any(surface_type in user_lower for surface_type in ["extrude", "revolve", "plane", "grid"]):
            provided.append("surface type")
        
        # Check name
        if "name" in user_lower or "call" in user_lower:
            provided.append("name")
        else:
            defaulted.append(f"name (defaulted to '{parsed_surface.name}')")
        
        # Check base curve for extrude/revolve
        if parsed_surface.surface_type in ["extrude", "revolve"]:
            if "curve" in user_lower or parsed_surface.base_curve:
                provided.append("base curve")
            else:
                defaulted.append("base curve (required for extrude/revolve)")
        
        # Check surface-specific properties
        if parsed_surface.surface_type == "extrude":
            if "distance" in user_lower or "by" in user_lower:
                provided.append("extrude distance")
            elif parsed_surface.extrude_distance != 1.0:
                provided.append("extrude distance")
            else:
                defaulted.append("extrude distance (defaulted to 1.0)")
        
        if parsed_surface.surface_type == "revolve":
            if "axis" in user_lower:
                provided.append("revolve axis")
            elif parsed_surface.revolve_axis != "Z":
                provided.append("revolve axis")
            else:
                defaulted.append("revolve axis (defaulted to Z)")
        
        if parsed_surface.surface_type in ["plane", "grid"]:
            if any(dim in user_lower for dim in ["width", "height", "x", "size"]):
                provided.append("dimensions")
            else:
                defaulted.append(f"dimensions (defaulted to {parsed_surface.width}x{parsed_surface.height})")
        
        if parsed_surface.surface_type == "grid":
            if "subdivision" in user_lower or "detail" in user_lower:
                provided.append("subdivisions")
            elif parsed_surface.subdivisions != 1:
                provided.append("subdivisions")
            else:
                defaulted.append("subdivisions (defaulted to 1)")
        
        # Check color
        has_color = any(color in user_lower for color in self.color_presets.keys()) or "color" in user_lower
        if has_color:
            provided.append("color")
        else:
            if parsed_surface.color_r != 0.8 and parsed_surface.color_g != 0.8 and parsed_surface.color_b != 0.8:
                provided.append("color")
            else:
                defaulted.append("color (defaulted to gray)")
        
        # Show analysis
        if defaulted:
            print(f"\nNote: The following surface attributes were missing, so I provided default values:")
            for attr in defaulted:
                print(f"  - {attr}")
            print("Let me know if you want to change any of these defaults.")
        
        if provided:
            print(f"\nProvided surface attributes: {', '.join(provided)}")

    def show_parsed_info(self, obj: ObjectCreation) -> bool:
        """Display parsed information and get user confirmation"""
        print(f"\nFinal parsed parameters:")
        print(f"  Object Type: {obj.object_type}")
        print(f"  Name: {obj.name}")
        print(f"  Location: ({obj.location_x}, {obj.location_y}, {obj.location_z})")
        print(f"  Size: {obj.size}")
        print(f"  Color (RGB): ({obj.color_r}, {obj.color_g}, {obj.color_b})")
        
        while True:
            confirm = input(f"\nCreate this {obj.object_type}? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                return True
            elif confirm in ['no', 'n']:
                return False
            print("Please enter 'yes' or 'no'")

    def show_curve_info(self, curve: CurveCreation) -> bool:
        """Display curve information and get user confirmation"""
        print(f"\nFinal curve parameters:")
        print(f"  Curve Type: {curve.curve_type}")
        print(f"  Name: {curve.name}")
        print(f"  Control Points: {len(curve.control_points)} points")
        for i, point in enumerate(curve.control_points):
            print(f"    Point {i+1}: ({point[0]}, {point[1]}, {point[2]})")
        print(f"  Dimensions: {curve.dimensions}")
        print(f"  Resolution: {curve.resolution}")
        print(f"  Extrude Depth: {curve.extrude_depth}")
        print(f"  Bevel Depth: {curve.bevel_depth}")
        print(f"  Color (RGB): ({curve.color_r}, {curve.color_g}, {curve.color_b})")
        
        while True:
            confirm = input(f"\nCreate this {curve.curve_type} curve? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                return True
            elif confirm in ['no', 'n']:
                return False
            print("Please enter 'yes' or 'no'")

    def show_surface_info(self, surface: SurfaceCreation) -> bool:
        """Display surface information and get user confirmation"""
        print(f"\nFinal surface parameters:")
        print(f"  Surface Type: {surface.surface_type}")
        print(f"  Name: {surface.name}")
        
        if surface.surface_type in ["extrude", "revolve"]:
            print(f"  Base Curve: {surface.base_curve}")
            
        if surface.surface_type == "extrude":
            print(f"  Extrude Distance: {surface.extrude_distance}")
        elif surface.surface_type == "revolve":
            print(f"  Revolve Axis: {surface.revolve_axis}")
        elif surface.surface_type in ["plane", "grid"]:
            print(f"  Dimensions: {surface.width} x {surface.height}")
            
        if surface.surface_type == "grid":
            print(f"  Subdivisions: {surface.subdivisions}")
            
        print(f"  Color (RGB): ({surface.color_r}, {surface.color_g}, {surface.color_b})")
        
        while True:
            confirm = input(f"\nCreate this {surface.surface_type} surface? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                return True
            elif confirm in ['no', 'n']:
                return False
            print("Please enter 'yes' or 'no'")
            
    def validate_manipulation_request(self, manipulation_params: ObjectManipulation) -> tuple[bool, str]:
        """Validate manipulation request and check if object exists"""
        if manipulation_params.object_name not in self.objects_registry:
            return False, f"Object '{manipulation_params.object_name}' not found. Available objects: {', '.join(self.objects_registry) if self.objects_registry else 'none'}"
        return True, ""
    
    def get_manipulation_defaults(self, manipulation_params: ObjectManipulation) -> ObjectManipulation:
        """Apply default values for missing manipulation parameters"""
        if manipulation_params.manipulation_type == "move":
            if manipulation_params.move_x is None:
                manipulation_params.move_x = 0.0
            if manipulation_params.move_y is None:
                manipulation_params.move_y = 0.0
            if manipulation_params.move_z is None:
                manipulation_params.move_z = 0.0
        
        elif manipulation_params.manipulation_type == "scale":
            # If uniform scale is provided, use it for all axes
            if manipulation_params.scale_uniform is not None:
                manipulation_params.scale_x = manipulation_params.scale_uniform
                manipulation_params.scale_y = manipulation_params.scale_uniform
                manipulation_params.scale_z = manipulation_params.scale_uniform
            else:
                # Apply defaults for individual axes
                if manipulation_params.scale_x is None:
                    manipulation_params.scale_x = 1.0
                if manipulation_params.scale_y is None:
                    manipulation_params.scale_y = 1.0
                if manipulation_params.scale_z is None:
                    manipulation_params.scale_z = 1.0
        
        elif manipulation_params.manipulation_type == "rotate":
            if manipulation_params.rotate_x is None:
                manipulation_params.rotate_x = 0.0
            if manipulation_params.rotate_y is None:
                manipulation_params.rotate_y = 0.0
            if manipulation_params.rotate_z is None:
                manipulation_params.rotate_z = 0.0
        
        return manipulation_params
    
    def show_manipulation_info(self, manipulation_params: ObjectManipulation) -> bool:
        """Display manipulation information and get user confirmation"""
        print(f"\nManipulation parameters:")
        print(f"  Action: {manipulation_params.manipulation_type}")
        print(f"  Object: {manipulation_params.object_name}")
        
        if manipulation_params.manipulation_type == "move":
            print(f"  Move offset: ({manipulation_params.move_x}, {manipulation_params.move_y}, {manipulation_params.move_z})")
        elif manipulation_params.manipulation_type == "scale":
            if manipulation_params.scale_uniform is not None:
                print(f"  Uniform scale: {manipulation_params.scale_uniform}")
            else:
                print(f"  Scale factors: X={manipulation_params.scale_x}, Y={manipulation_params.scale_y}, Z={manipulation_params.scale_z}")
        elif manipulation_params.manipulation_type == "rotate":
            print(f"  Rotation (degrees): X={manipulation_params.rotate_x}, Y={manipulation_params.rotate_y}, Z={manipulation_params.rotate_z}")
        
        while True:
            confirm = input(f"\nApply this {manipulation_params.manipulation_type} to {manipulation_params.object_name}? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                return True
            elif confirm in ['no', 'n']:
                return False
            print("Please enter 'yes' or 'no'")
    
    def ask_for_object_clarification(self, manipulation_type: str) -> Optional[str]:
        """Ask user to specify which object to manipulate"""
        if not self.objects_registry:
            print("No objects available to manipulate.")
            return None
        
        print(f"\nWhich object would you like to {manipulation_type}?")
        print("Available objects:")
        for i, name in enumerate(self.objects_registry, 1):
            print(f"  {i}. {name}")
        
        while True:
            choice = input("Enter object name or number: ").strip()
            
            # Try as direct name match
            if choice in self.objects_registry:
                return choice
            
            # Try as number
            try:
                index = int(choice) - 1
                if 0 <= index < len(self.objects_registry):
                    return self.objects_registry[index]
                else:
                    print(f"Invalid number. Please enter 1-{len(self.objects_registry)}")
            except ValueError:
                print("Invalid input. Please enter a valid object name or number.")
                
            # Ask if they want to cancel
            cancel = input("Type 'cancel' to abort, or try again: ").strip().lower()
            if cancel == 'cancel':
                return None

    def show_detailed_help(self):
        """Display comprehensive help information"""
        print("="*70)
        print("    DETAILED USAGE GUIDE")
        print("="*70)
        print()
        print("SUPPORTED ACTIONS & REQUIRED PARAMETERS:")
        print()
        print("1. CREATE OBJECTS:")
        print("   Syntax: 'create [color] [object_type] [at x,y,z] [size N]'")
        print("   - object_type: cube, sphere, cylinder (REQUIRED)")
        print("   - color: red, green, blue, yellow, purple, cyan, white, black, gray (optional)")
        print("   - location: coordinates like 'at 2,3,1' (optional, default: 0,0,0)")
        print("   - size: scale factor like 'size 2' (optional, default: 1.0)")
        print("   Examples: 'create red cube', 'create blue sphere at 2,0,3 size 1.5'")
        print()
        print("2. CREATE CURVES:")
        print("   Syntax: 'create [color] [curve_type] curve [with points/spiral] [properties]'")
        print("   - curve_type: bezier, nurbs, poly (optional, default: nurbs)")
        print("   - control_points: 'from (x,y,z) to (x,y,z)' OR 'spiral' (REQUIRED)")
        print("   - extrude_depth: 'extrude depth N' for 3D volume (optional, default: 0.0)")
        print("   - bevel_depth: 'bevel depth N' for rounded edges (optional, default: 0.0)")
        print("   - resolution: 'resolution N' for smoothness 1-64 (optional, default: 12)")
        print("   - color: same as objects (optional)")
        print("   Examples: 'create red bezier curve from (0,0,0) to (2,2,2) to (4,0,0)'")
        print("            'create green spiral curve with extrude depth 0.2'")
        print()
        print("   CURVE PROPERTIES EXPLAINED:")
        print("   - extrude_depth: Gives curves thickness (0 = invisible line, >0 = 3D tube)")
        print("   - bevel_depth: Rounds the edges (0 = sharp, >0 = smooth/rounded)")
        print("   - For visible curves, use extrude_depth > 0 OR bevel_depth > 0")
        print()
        print("3. CREATE SURFACES:")
        print("   A) PLANE: 'create [color] plane [WxH]'")
        print("      - width/height: dimensions like '5x3' (optional, default: 2x2)")
        print("      Example: 'create blue plane 5x3'")
        print()
        print("   B) GRID: 'create [color] grid [WxH] [with N subdivisions]'")
        print("      - width/height: dimensions (optional, default: 2x2)")
        print("      - subdivisions: detail level 1-20 (optional, default: 1)")
        print("      Example: 'create red grid 4x4 with 8 subdivisions'")
        print()
        print("   C) EXTRUDE: 'extrude [curve_name] by N units'")
        print("      - curve_name: name of existing curve (REQUIRED)")
        print("      - distance: extrusion distance (REQUIRED)")
        print("      Example: 'extrude spiral curve by 1.5 units'")
        print()
        print("   D) REVOLVE: 'revolve [curve_name] around [X/Y/Z] axis'")
        print("      - curve_name: name of existing curve (REQUIRED)")
        print("      - axis: X, Y, or Z (optional, default: Z)")
        print("      Example: 'revolve bezier curve around Y axis'")
        print()
        print("4. OTHER ACTIONS:")
        print("   - LIST: 'list objects' - show all objects in scene")
        print("   - DELETE: 'delete [object_name]' or 'delete all objects'")
        print("   - MANIPULATE: 'move/scale/rotate [object_name] [parameters]'")
        print("     Examples: 'move cube by 2,0,1', 'scale sphere by 1.5', 'rotate cylinder 45 degrees'")
        print("   - VIEW: 'view scene' - open Blender GUI to see current scene")
        print("   - HELP: 'help' - show this detailed guide")
        print()
        print("="*70)

    def confirm_deletion(self, deletion_params: ObjectDeletion) -> bool:
        """Confirm deletion with user before proceeding"""
        if deletion_params.action == "delete_all":
            if not self.objects_registry:
                print("No objects to delete.")
                return False
                
            print(f"\nConfirmation required:")
            print(f"This will delete ALL {len(self.objects_registry)} objects:")
            for i, name in enumerate(self.objects_registry, 1):
                print(f"  {i}. {name}")
                
            while True:
                confirm = input(f"\nDelete all objects? (yes/no): ").strip().lower()
                if confirm in ['yes', 'y']:
                    return True
                elif confirm in ['no', 'n']:
                    return False
                print("Please enter 'yes' or 'no'")
                
        else:  # delete_specific
            if deletion_params.object_name not in self.objects_registry:
                print(f"Object '{deletion_params.object_name}' not found.")
                print(f"Available objects: {', '.join(self.objects_registry) if self.objects_registry else 'none'}")
                return False
                
            while True:
                confirm = input(f"\nDelete object '{deletion_params.object_name}'? (yes/no): ").strip().lower()
                if confirm in ['yes', 'y']:
                    return True
                elif confirm in ['no', 'n']:
                    return False
                print("Please enter 'yes' or 'no'")
    
    def generate_deletion_code(self, deletion_params: ObjectDeletion) -> str:
        """Generate Blender code for deletion"""
        if deletion_params.action == "delete_all":
            return '''
# Delete all mesh objects
mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
count = len(mesh_objects)
for obj in mesh_objects:
    bpy.data.objects.remove(obj, do_unlink=True)
print(f"Deleted {count} objects")
'''
        else:  # delete_specific
            return f'''
# Delete specific object by name
if "{deletion_params.object_name}" in bpy.data.objects:
    obj = bpy.data.objects["{deletion_params.object_name}"]
    bpy.data.objects.remove(obj, do_unlink=True)
    print("Deleted object '{deletion_params.object_name}'")
else:
    print("Object '{deletion_params.object_name}' not found")
'''

    def generate_manipulation_code(self, manipulation_params: ObjectManipulation) -> str:
        """Generate Blender code for object manipulation"""
        
        if manipulation_params.manipulation_type == "move":
            return f'''
# Move object '{manipulation_params.object_name}'
if "{manipulation_params.object_name}" in bpy.data.objects:
    obj = bpy.data.objects["{manipulation_params.object_name}"]
    obj.location.x += {manipulation_params.move_x}
    obj.location.y += {manipulation_params.move_y}
    obj.location.z += {manipulation_params.move_z}
    print("Moved '{manipulation_params.object_name}' by ({manipulation_params.move_x}, {manipulation_params.move_y}, {manipulation_params.move_z})")
else:
    print("Object '{manipulation_params.object_name}' not found")
'''
        
        elif manipulation_params.manipulation_type == "scale":
            return f'''
# Scale object '{manipulation_params.object_name}'
if "{manipulation_params.object_name}" in bpy.data.objects:
    obj = bpy.data.objects["{manipulation_params.object_name}"]
    obj.scale.x *= {manipulation_params.scale_x}
    obj.scale.y *= {manipulation_params.scale_y}
    obj.scale.z *= {manipulation_params.scale_z}
    print("Scaled '{manipulation_params.object_name}' by factors ({manipulation_params.scale_x}, {manipulation_params.scale_y}, {manipulation_params.scale_z})")
else:
    print("Object '{manipulation_params.object_name}' not found")
'''
        
        elif manipulation_params.manipulation_type == "rotate":
            # Convert degrees to radians
            rad_x = math.radians(manipulation_params.rotate_x)
            rad_y = math.radians(manipulation_params.rotate_y)
            rad_z = math.radians(manipulation_params.rotate_z)
            
            return f'''
# Rotate object '{manipulation_params.object_name}'
import mathutils
if "{manipulation_params.object_name}" in bpy.data.objects:
    obj = bpy.data.objects["{manipulation_params.object_name}"]
    # Add rotation to existing rotation
    obj.rotation_euler.x += {rad_x}
    obj.rotation_euler.y += {rad_y}
    obj.rotation_euler.z += {rad_z}
    print("Rotated '{manipulation_params.object_name}' by ({manipulation_params.rotate_x}°, {manipulation_params.rotate_y}°, {manipulation_params.rotate_z}°)")
else:
    print("Object '{manipulation_params.object_name}' not found")
'''
        
        return ""
    
    def generate_material_code(self, material: MaterialProperties, material_name: str, color_r: float, color_g: float, color_b: float) -> str:
        """Generate Blender code for material creation with advanced properties"""
        
        # Set default values based on material type
        if material.material_type == "metallic":
            metallic = material.metallic if material.metallic is not None else 1.0
            roughness = material.roughness if material.roughness is not None else 0.1
            emission = material.emission_strength if material.emission_strength is not None else 0.0
            transparency = material.transparency if material.transparency is not None else 0.0
        elif material.material_type == "glass":
            metallic = material.metallic if material.metallic is not None else 0.0
            roughness = material.roughness if material.roughness is not None else 0.0
            emission = material.emission_strength if material.emission_strength is not None else 0.0
            transparency = material.transparency if material.transparency is not None else 0.9
        elif material.material_type == "emission":
            metallic = material.metallic if material.metallic is not None else 0.0
            roughness = material.roughness if material.roughness is not None else 0.5
            emission = material.emission_strength if material.emission_strength is not None else 1.0
            transparency = material.transparency if material.transparency is not None else 0.0
        elif material.material_type == "plastic":
            metallic = material.metallic if material.metallic is not None else 0.0
            roughness = material.roughness if material.roughness is not None else 0.3
            emission = material.emission_strength if material.emission_strength is not None else 0.0
            transparency = material.transparency if material.transparency is not None else 0.0
        elif material.material_type == "rough":
            metallic = material.metallic if material.metallic is not None else 0.0
            roughness = material.roughness if material.roughness is not None else 0.9
            emission = material.emission_strength if material.emission_strength is not None else 0.0
            transparency = material.transparency if material.transparency is not None else 0.0
        else:  # basic
            metallic = material.metallic if material.metallic is not None else 0.0
            roughness = material.roughness if material.roughness is not None else 0.5
            emission = material.emission_strength if material.emission_strength is not None else 0.0
            transparency = material.transparency if material.transparency is not None else 0.0
        
        return f'''
# Create {material.material_type} material
material = bpy.data.materials.new(name="{material_name}")
material.use_nodes = True
nodes = material.node_tree.nodes
principled = nodes["Principled BSDF"]

# Set material properties
principled.inputs["Base Color"].default_value = ({color_r}, {color_g}, {color_b}, 1.0)
principled.inputs["Metallic"].default_value = {metallic}
principled.inputs["Roughness"].default_value = {roughness}

# Handle emission - try both old and new input names for compatibility
try:
    principled.inputs["Emission Color"].default_value = ({color_r * emission}, {color_g * emission}, {color_b * emission}, 1.0)
except KeyError:
    try:
        principled.inputs["Emission"].default_value = ({color_r * emission}, {color_g * emission}, {color_b * emission}, 1.0)
    except KeyError:
        print("Warning: Could not set emission color")

try:
    principled.inputs["Emission Strength"].default_value = {emission}
except KeyError:
    print("Warning: Could not set emission strength")

# Handle transparency if needed
if {transparency} > 0.0:
    try:
        principled.inputs["Alpha"].default_value = {1.0 - transparency}
        material.blend_method = 'BLEND'
        material.show_transparent_back = False
    except KeyError:
        print("Warning: Could not set transparency")
'''
    
    def generate_curve_code(self, curve: CurveCreation) -> str:
        """Generate Blender Python code for curve creation"""
        
        # Generate proper spiral points if user requested spiral and no specific points provided
        if "spiral" in curve.name.lower() and len(curve.control_points) <= 4:
            # Create a spiral pattern
            import math
            spiral_points = []
            num_turns = 3
            points_per_turn = 8
            radius_start = 0.5
            radius_end = 2.0
            height_per_turn = 1.0
            
            for i in range(num_turns * points_per_turn + 1):
                t = i / points_per_turn  # parameter from 0 to num_turns
                angle = t * 2 * math.pi
                radius = radius_start + (radius_end - radius_start) * (t / num_turns)
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
                z = t * height_per_turn
                spiral_points.append([x, y, z])
            
            curve.control_points = spiral_points
            print(f"Generated spiral with {len(spiral_points)} control points")
        
        # Validate control points
        if len(curve.control_points) < 2:
            return "# Error: Need at least 2 control points for a curve\nprint('Error: Need at least 2 control points for a curve')"
        
        blender_code = f'''
# Create {curve.curve_type} curve '{curve.name}'
import bpy
import bmesh
from mathutils import Vector

# Create new curve data
curve_data = bpy.data.curves.new(name="{curve.name}", type='CURVE')
curve_data.dimensions = '{curve.dimensions}'
curve_data.resolution_u = {curve.resolution}
curve_data.extrude = {curve.extrude_depth}
curve_data.bevel_depth = {curve.bevel_depth}

# Map curve type to Blender spline type
curve_type_mapping = {{
    'bezier': 'BEZIER',
    'nurbs': 'NURBS', 
    'poly': 'POLY'
}}
spline_type = curve_type_mapping.get('{curve.curve_type}', 'NURBS')
spline = curve_data.splines.new(spline_type)

# Set control points
control_points = {curve.control_points}
'''

        if curve.curve_type.lower() == "bezier":
            blender_code += f'''
# Add points for bezier curve
spline.bezier_points.add(len(control_points) - 1)
for i, point in enumerate(control_points):
    bezier_point = spline.bezier_points[i]
    bezier_point.co = Vector(point)
    bezier_point.handle_left_type = 'AUTO'
    bezier_point.handle_right_type = 'AUTO'
'''
        else:  # NURBS or POLY
            blender_code += f'''
# Add points for {curve.curve_type} curve
spline.points.add(len(control_points) - 1)
for i, point in enumerate(control_points):
    spline.points[i].co = (point[0], point[1], point[2], 1.0)  # x, y, z, weight
'''

        blender_code += f'''
# Create object and link to scene
curve_obj = bpy.data.objects.new("{curve.name}", curve_data)
bpy.context.collection.objects.link(curve_obj)

# Set as active object
bpy.context.view_layer.objects.active = curve_obj
curve_obj.select_set(True)

'''
        
        # Add material code
        if curve.material and curve.material.material_type != "basic":
            blender_code += self.generate_material_code(curve.material, f"{curve.name}_Material", curve.color_r, curve.color_g, curve.color_b)
        else:
            blender_code += f'''
# Create basic material and set color
material = bpy.data.materials.new(name="{curve.name}_Material")
material.use_nodes = True
material.node_tree.nodes["Principled BSDF"].inputs[0].default_value = ({curve.color_r}, {curve.color_g}, {curve.color_b}, 1.0)
'''
        
        blender_code += f'''
# Apply material to curve
curve_obj.data.materials.append(material)

print(f"Created {curve.curve_type} curve '{curve.name}' with {{len(control_points)}} control points")
'''
        
        return blender_code
    
    def generate_surface_code(self, surface: SurfaceCreation) -> str:
        """Generate Blender Python code for surface creation"""
        
        if surface.surface_type in ["extrude", "revolve"]:
            if not surface.base_curve or surface.base_curve not in self.objects_registry:
                return f"# Error: Base curve '{surface.base_curve}' not found for {surface.surface_type} operation\nprint('Error: Base curve not found')"
        
        blender_code = f'''
# Create {surface.surface_type} surface '{surface.name}'
import bpy
from mathutils import Vector

'''

        if surface.surface_type == "plane":
            blender_code += f'''
# Create plane surface
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "{surface.name}"

# Scale to desired dimensions
obj.scale.x = {surface.width}
obj.scale.y = {surface.height}
obj.scale.z = 1.0

print(f"Created plane surface '{surface.name}' with dimensions {{obj.scale.x}}x{{obj.scale.y}}")
'''

        elif surface.surface_type == "grid":
            blender_code += f'''
# Create grid surface with subdivisions
bpy.ops.mesh.primitive_grid_add(x_subdivisions={surface.subdivisions}, y_subdivisions={surface.subdivisions}, size=1, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "{surface.name}"

# Scale to desired dimensions
obj.scale.x = {surface.width}
obj.scale.y = {surface.height}
obj.scale.z = 1.0

print(f"Created grid surface '{surface.name}' with {{obj.scale.x}}x{{obj.scale.y}} dimensions and {surface.subdivisions} subdivisions")
'''

        elif surface.surface_type == "extrude":
            blender_code += f'''
# Extrude curve to create surface
base_curve_name = "{surface.base_curve}"
if base_curve_name in bpy.data.objects:
    base_curve = bpy.data.objects[base_curve_name]
    
    # Duplicate the curve for extrusion
    bpy.context.view_layer.objects.active = base_curve
    base_curve.select_set(True)
    bpy.ops.object.duplicate()
    
    extruded_obj = bpy.context.active_object
    extruded_obj.name = "{surface.name}"
    
    # Set extrusion depth
    curve_data = extruded_obj.data
    curve_data.extrude = {surface.extrude_distance}
    curve_data.bevel_depth = 0.1  # Small bevel for better surface
    
    # Convert to mesh for better surface properties
    bpy.context.view_layer.objects.active = extruded_obj
    bpy.ops.object.convert(target='MESH')
    
    obj = extruded_obj
    print(f"Created extruded surface '{surface.name}' from curve '{{base_curve_name}}' with distance {surface.extrude_distance}")
else:
    print(f"Error: Base curve '{{base_curve_name}}' not found")
    obj = None
'''

        elif surface.surface_type == "revolve":
            axis_map = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}
            axis_vector = axis_map.get(surface.revolve_axis, (0, 0, 1))
            
            blender_code += f'''
# Revolve curve around axis to create surface
base_curve_name = "{surface.base_curve}"
if base_curve_name in bpy.data.objects:
    base_curve = bpy.data.objects[base_curve_name]
    
    # Duplicate the curve for revolving
    bpy.context.view_layer.objects.active = base_curve
    base_curve.select_set(True)
    bpy.ops.object.duplicate()
    
    revolved_obj = bpy.context.active_object
    revolved_obj.name = "{surface.name}"
    
    # Add screw modifier for revolving
    screw_modifier = revolved_obj.modifiers.new(name="Screw", type='SCREW')
    screw_modifier.axis = '{surface.revolve_axis}'
    screw_modifier.angle = 6.28319  # 2*pi radians (360 degrees)
    screw_modifier.steps = 16  # Number of steps around the revolution
    screw_modifier.render_steps = 16
    
    # Apply the modifier to create the mesh
    bpy.context.view_layer.objects.active = revolved_obj
    bpy.ops.object.modifier_apply(modifier="Screw")
    
    obj = revolved_obj
    print(f"Created revolved surface '{surface.name}' from curve '{{base_curve_name}}' around {surface.revolve_axis} axis")
else:
    print(f"Error: Base curve '{{base_curve_name}}' not found")
    obj = None
'''

        # Add material application for all surface types
        blender_code += f'''
# Create material and apply to surface
if obj:
'''
        if surface.material and surface.material.material_type != "basic":
            blender_code += "    " + self.generate_material_code(surface.material, f"{surface.name}_Material", surface.color_r, surface.color_g, surface.color_b).replace("\n", "\n    ")
        else:
            blender_code += f'''
    material = bpy.data.materials.new(name="{surface.name}_Material")
    material.use_nodes = True
    material.node_tree.nodes["Principled BSDF"].inputs[0].default_value = ({surface.color_r}, {surface.color_g}, {surface.color_b}, 1.0)
'''
        
        blender_code += f'''
    # Apply material to surface
    obj.data.materials.append(material)
'''
        
        return blender_code
    
    def generate_blender_code(self, obj: ObjectCreation) -> str:
        """Generate Blender Python code from the schema"""
        
        if obj.object_type == "cube":
            # Cube uses scale parameter
            create_code = f"bpy.ops.mesh.primitive_cube_add(location=({obj.location_x}, {obj.location_y}, {obj.location_z}), scale=({obj.size}, {obj.size}, {obj.size}))"
        elif obj.object_type == "sphere":
            # Sphere uses radius parameter
            create_code = f"bpy.ops.mesh.primitive_uv_sphere_add(location=({obj.location_x}, {obj.location_y}, {obj.location_z}), radius={obj.size})"
        elif obj.object_type == "cylinder":
            # Cylinder uses radius and depth parameters
            create_code = f"bpy.ops.mesh.primitive_cylinder_add(location=({obj.location_x}, {obj.location_y}, {obj.location_z}), radius={obj.size}, depth={obj.size*2})"
        
        blender_code = f"""
# Create {obj.object_type}
{create_code}

# Get the created object and set name
obj = bpy.context.active_object
obj.name = "{obj.name}"

"""
        
        # Add material code
        if obj.material and obj.material.material_type != "basic":
            blender_code += self.generate_material_code(obj.material, f"{obj.name}_Material", obj.color_r, obj.color_g, obj.color_b)
        else:
            blender_code += f"""
# Create basic material and set color
material = bpy.data.materials.new(name="{obj.name}_Material")
material.use_nodes = True
material.node_tree.nodes["Principled BSDF"].inputs[0].default_value = ({obj.color_r}, {obj.color_g}, {obj.color_b}, 1.0)
"""
        
        blender_code += f"""
# Apply material to object
obj.data.materials.append(material)

print(f"Created {obj.object_type} '{obj.name}' successfully")
"""
        return blender_code
    
    def run_blender_script(self, user_code: str, open_gui: bool = False) -> bool:
        """Execute Blender script with user code"""
        
        # Choose between background mode (for rendering) or GUI mode (for viewing)
        blender_mode = [] if open_gui else ["--background"]
        
        full_script = f'''
import bpy
import os

print("=== BLENDER SESSION START ===")

# Load existing session scene if available, otherwise start fresh
scene_file = "{self.session_blend_file}"
print(f"Looking for existing scene file: {{scene_file}}")

if os.path.exists(scene_file):
    try:
        print("Found existing scene file, loading...")
        # Print what objects are in scene before loading
        mesh_objects_before = [obj.name for obj in bpy.data.objects if obj.type == 'MESH']
        curve_objects_before = [obj.name for obj in bpy.data.objects if obj.type == 'CURVE']
        print(f"Objects in default scene before loading - MESH: {{mesh_objects_before}}, CURVE: {{curve_objects_before}}")
        
        bpy.ops.wm.open_mainfile(filepath=scene_file)
        
        # Print what objects are in scene after loading
        mesh_objects_after = [obj.name for obj in bpy.data.objects if obj.type == 'MESH']
        curve_objects_after = [obj.name for obj in bpy.data.objects if obj.type == 'CURVE']
        print(f"Objects in scene after loading - MESH: {{mesh_objects_after}}, CURVE: {{curve_objects_after}}")
        print("Loaded existing session scene")
    except Exception as e:
        print(f"Failed to load session scene: {{e}}")
        print("Starting fresh...")
        # Clear all objects for fresh start
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False, confirm=False)
else:
    print("No existing scene file found, starting fresh")
    # Remove all default objects for completely clean scene (first time only)
    default_objects = [obj.name for obj in bpy.data.objects]
    print(f"Removing default objects: {{default_objects}}")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False, confirm=False)
    print("Cleaned default scene")

print("\\n=== EXECUTING USER CODE ===")
# User's object creation/deletion/manipulation code
{user_code}

print("\\n=== SCENE SETUP ===")
# Setup camera if needed
if not any(obj.type == 'CAMERA' for obj in bpy.data.objects):
    bpy.ops.object.camera_add(location=(7, -7, 5))
    camera = bpy.context.active_object
    camera.rotation_euler = (1.1, 0, 0.785)
    bpy.context.scene.camera = camera
    # hiding the camera since it was showing in Blender's view
    camera.hide_viewport = True  # Set to True to hide
    print("Added camera")
else:
    print("Camera already exists")

# Setup light if needed  
if not any(obj.type == 'LIGHT' for obj in bpy.data.objects):
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    print("Added light")
else:
    print("Light already exists")

print("\\n=== FINAL SCENE STATE ===")
# List all objects in the scene by type
all_objects = {{}}
for obj in bpy.data.objects:
    if obj.type not in all_objects:
        all_objects[obj.type] = []
    all_objects[obj.type].append(obj.name)

for obj_type, names in all_objects.items():
    print(f"{{obj_type}}: {{names}}")

# List all renderable objects (MESH and CURVE)
mesh_objects = [obj.name for obj in bpy.data.objects if obj.type == 'MESH']
curve_objects = [obj.name for obj in bpy.data.objects if obj.type == 'CURVE']
renderable_objects = mesh_objects + curve_objects

print(f"\\nTARGET MESH OBJECTS TO RENDER: {{mesh_objects}}")
print(f"TARGET CURVE OBJECTS TO RENDER: {{curve_objects}}")
print(f"ALL RENDERABLE OBJECTS: {{renderable_objects}}")
print(f"Total renderable objects: {{len(renderable_objects)}}")

# Check if curves have proper volume for rendering
for obj in bpy.data.objects:
    if obj.type == 'CURVE':
        curve_data = obj.data
        print(f"Curve '{{obj.name}}': extrude={{curve_data.extrude}}, bevel={{curve_data.bevel_depth}}, dimensions={{curve_data.dimensions}}")
        if curve_data.extrude == 0 and curve_data.bevel_depth == 0:
            print(f"WARNING: Curve '{{obj.name}}' has no volume - may not be visible in render!")

# Save scene first
bpy.ops.wm.save_as_mainfile(filepath="{self.session_blend_file}")
print(f"Scene saved as {self.session_blend_file}")

# Only render if running in background mode
if not {open_gui}:
    print("\\n=== RENDERING ===")
    # Render scene
    scene = bpy.context.scene
    scene.render.filepath = "{self.session_render_file}"
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = 800
    scene.render.resolution_y = 600
    bpy.ops.render.render(write_still=True)
    print(f"Screenshot saved as {self.session_render_file}")
else:
    print("\\n=== BLENDER GUI MODE ===")
    print("Opening Blender GUI to view scene...")
    # Try to set viewport shading, but handle the case where screen context isn't available
    try:
        if bpy.context.screen:
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.shading.type = 'MATERIAL_PREVIEW'
                            break
        else:
            print("Screen context not available - viewport shading will use defaults")
    except Exception as ex:
        print(f"Could not set viewport shading: {{ex}}")
        print("This is normal when opening GUI mode - you can manually change shading in Blender")

print("=== BLENDER SESSION END ===")
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(full_script)
            script_path = f.name
        
        if open_gui:
            print("Opening Blender GUI...")
            result = subprocess.Popen([self.blender_path, "--python", script_path, self.session_blend_file])
            print(f"Blender GUI launched with PID: {result.pid}")
            return True  
        else:
            print("Running Blender in background...")
            result = subprocess.run([self.blender_path, "--background", "--python", script_path])
            return result.returncode == 0