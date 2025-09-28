from schemas import (
    ObjectCreation, 
    CurveCreation, 
    MaterialProperties,
    SurfaceCreation, 
    ObjectDeletion, 
    ObjectManipulation, 
    ActionRequest,
    BatchCreation  # Add this line
)
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
        self.used_names = set()
        self.objects_registry = []
        
        self.session_id = int(time.time())
        self.session_blend_file = f"result_{self.session_id}.blend"
        self.session_render_file = f"result_render_{self.session_id}.png"
        
        print(f"Session ID: {self.session_id}")
        print(f"Scene file: {self.session_blend_file}")
        print(f"Render file: {self.session_render_file}")
        
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
        
        color_info = ", ".join([f"{name}: {rgb}" for name, rgb in self.color_presets.items()])
        current_objects = ", ".join(self.objects_registry) if self.objects_registry else "none"
        
        system_prompt = f"""You are a 3D blender modeling assistant. Parse user requests and determine the action type.

CURRENT OBJECTS IN SCENE: {current_objects}

SUPPORTED ACTIONS:
1. CREATE: "create", "make", "add" + single item (cube/sphere/cylinder/plane/grid/curve)
2. CREATE_CURVE: "create curve", "make curve", "bezier curve", "spiral curve" + single curve
3. CREATE_SURFACE: "create surface", "make surface", "create plane/grid" + single surface  
4. BATCH_CREATE: Multiple items in one command
5. LIST: "list", "show", "what objects" 
6. DELETE: "delete", "remove" + object name OR "delete all"
7. MANIPULATE: "move", "scale", "rotate" + object name + parameters
8. VIEW: "view", "show scene", "open blender", "display scene"
9. HELP: "help", "guide", "what can I do", "instructions"

FOR BATCH_CREATE ACTIONS (detect multiple items, quantities, or mixed requests):
- Use when user mentions multiple objects: "create a red cube and blue sphere"
- Use when user mentions quantities of ANY type: "create 3 cubes", "make 5 planes", "create 4 grids"
- Use when user mentions multiple surfaces: "create 3 red planes and 2 blue grids"
- Use when user mentions multiple curves: "create 2 bezier curves and 1 spiral"
- Use when user describes mixed scenes: "create 2 cubes, 3 planes, and 1 curve"
- Parse each item separately into the appropriate objects/curves/surfaces lists
- Generate unique names for each item
- Handle positioning automatically (spread items out to avoid overlap)

Examples of BATCH_CREATE:
- "create 3 planes" -> surfaces=[plane_1, plane_2, plane_3] spaced along X-axis
- "make 5 red grids" -> surfaces=[5 red grids spaced out]
- "create 2 cubes and 3 planes" -> objects=[2 cubes], surfaces=[3 planes]
- "create 4 bezier curves" -> curves=[4 bezier curves spaced out]
- "create 2 spirals" -> curves=[spiral_1, spiral_2] spaced along X-axis
- "make 3 bezier curves and 2 spirals" -> curves=[3 bezier curves, 2 spiral curves]


POSITIONING FOR BATCH_CREATE:
- Spread objects along X-axis with 3-unit spacing to avoid overlap
- For large quantities (>5), arrange in a grid pattern
- Keep Y and Z coordinates at 0 unless specified

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

    def show_batch_info(self, batch: BatchCreation) -> bool:
        """Display batch creation information and get user confirmation"""
        print(f"\nBatch creation parameters:")
        
        total_items = len(batch.objects) + len(batch.curves) + len(batch.surfaces)
        print(f"  Total items to create: {total_items}")
        
        if batch.objects:
            print(f"  Objects ({len(batch.objects)}):")
            for i, obj in enumerate(batch.objects, 1):
                print(f"    {i}. {obj.object_type} '{obj.name}' at ({obj.location_x}, {obj.location_y}, {obj.location_z})")
        
        if batch.curves:
            print(f"  Curves ({len(batch.curves)}):")
            for i, curve in enumerate(batch.curves, 1):
                print(f"    {i}. {curve.curve_type} curve '{curve.name}'")
                
        if batch.surfaces:
            print(f"  Surfaces ({len(batch.surfaces)}):")
            for i, surface in enumerate(batch.surfaces, 1):
                print(f"    {i}. {surface.surface_type} surface '{surface.name}'")
        
        while True:
            confirm = input(f"\nCreate all {total_items} items? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                return True
            elif confirm in ['no', 'n']:
                return False
            print("Please enter 'yes' or 'no'")

    def generate_batch_code(self, batch: BatchCreation) -> str:
        """Generate combined Blender code for batch creation"""
        combined_code = "# Batch creation script\n\n"
        
        for obj in batch.objects:
            combined_code += self.generate_blender_code(obj) + "\n"
        
        for curve in batch.curves:
            combined_code += self.generate_curve_code(curve) + "\n"
            
        for surface in batch.surfaces:
            combined_code += self.generate_surface_code(surface) + "\n"
        
        return combined_code

    def process_batch_creation(self, batch: BatchCreation):
        """Process batch creation with name validation and registry updates"""
        for obj in batch.objects:
            obj.name = self.validate_name(obj.name)
            self.used_names.add(obj.name)
            
        for curve in batch.curves:
            curve.name = self.validate_name(curve.name)
            self.used_names.add(curve.name)
            
        for surface in batch.surfaces:
            surface.name = self.validate_name(surface.name)
            self.used_names.add(surface.name)
        
        if not self.show_batch_info(batch):
            print("Batch creation cancelled")
            return False
        
        batch_code = self.generate_batch_code(batch)
        success = self.run_blender_script(batch_code)
        
        if success:
            for obj in batch.objects:
                self.add_to_registry(obj.name)
            for curve in batch.curves:
                self.add_to_registry(curve.name)
            for surface in batch.surfaces:
                self.add_to_registry(surface.name)
            
            total_created = len(batch.objects) + len(batch.curves) + len(batch.surfaces)
            print(f"Successfully created {total_created} items!")
            return True
        else:
            print("Failed to create batch items")
            return False

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
            if manipulation_params.scale_uniform is not None:
                manipulation_params.scale_x = manipulation_params.scale_uniform
                manipulation_params.scale_y = manipulation_params.scale_uniform
                manipulation_params.scale_z = manipulation_params.scale_uniform
            else:
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
            
            if choice in self.objects_registry:
                return choice
            
            try:
                index = int(choice) - 1
                if 0 <= index < len(self.objects_registry):
                    return self.objects_registry[index]
                else:
                    print(f"Invalid number. Please enter 1-{len(self.objects_registry)}")
            except ValueError:
                print("Invalid input. Please enter a valid object name or number.")
                
            cancel = input("Type 'cancel' to abort, or try again: ").strip().lower()
            if cancel == 'cancel':
                return None

    def show_detailed_help(self):
        """Display comprehensive help information"""
        print("="*70)
        print("    DETAILED USAGE GUIDE")
        print("="*70)
        print()
        print("SUPPORTED ACTIONS:")
        print()
        print("1. CREATE SINGLE OBJECTS:")
        print("   Examples: 'create red cube', 'create blue sphere'")
        print()
        print("2. CREATE MULTIPLE OBJECTS (BATCH):")
        print("   Examples:")
        print("   - 'create 3 red cubes and 2 blue spheres'")
        print("   - 'make 5 green cylinders'")
        print("   - 'create a red cube and metallic sphere'")
        print()
        print("3. OTHER ACTIONS:")
        print("   - 'list objects' - show all objects in scene")
        print("   - 'view scene' - open Blender GUI")
        print("   - 'help' - show this guide")
        print("   - 'quit' - exit program")
        print()
        print("Available colors: red, green, blue, yellow, purple, cyan, white, black, gray")
        print("Available materials: metallic, glass, emission, plastic, rough")
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
                
        else:
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
        else:
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
            rad_x = math.radians(manipulation_params.rotate_x)
            rad_y = math.radians(manipulation_params.rotate_y)
            rad_z = math.radians(manipulation_params.rotate_z)
            
            return f'''
# Rotate object '{manipulation_params.object_name}'
import mathutils
if "{manipulation_params.object_name}" in bpy.data.objects:
    obj = bpy.data.objects["{manipulation_params.object_name}"]
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
        
        if "spiral" in curve.name.lower() and len(curve.control_points) <= 4:
            spiral_points = []
            num_turns = 3
            points_per_turn = 8
            radius_start = 0.5
            radius_end = 2.0
            height_per_turn = 1.0
            
            for i in range(num_turns * points_per_turn + 1):
                t = i / points_per_turn
                angle = t * 2 * math.pi
                radius = radius_start + (radius_end - radius_start) * (t / num_turns)
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
                z = t * height_per_turn
                spiral_points.append([x, y, z])
            
            curve.control_points = spiral_points
            print(f"Generated spiral with {len(spiral_points)} control points")
        
        if len(curve.control_points) < 2:
            return "# Error: Need at least 2 control points for a curve\nprint('Error: Need at least 2 control points for a curve')"
        
        resolution = curve.resolution if curve.resolution is not None else 12
        extrude_depth = curve.extrude_depth if curve.extrude_depth is not None else 0.0
        bevel_depth = curve.bevel_depth if curve.bevel_depth is not None else 0.0

        blender_code = f'''
# Create {curve.curve_type} curve '{curve.name}'
import bpy
import bmesh
from mathutils import Vector

# Create new curve data
curve_data = bpy.data.curves.new(name="{curve.name}", type='CURVE')
curve_data.dimensions = '{curve.dimensions}'
curve_data.resolution_u = {resolution}
curve_data.extrude = {extrude_depth}
curve_data.bevel_depth = {bevel_depth}

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
        else:
            blender_code += f'''
# Add points for {curve.curve_type} curve
spline.points.add(len(control_points) - 1)
for i, point in enumerate(control_points):
    spline.points[i].co = (point[0], point[1], point[2], 1.0)
'''

        blender_code += f'''
# Create object and link to scene
curve_obj = bpy.data.objects.new("{curve.name}", curve_data)
bpy.context.collection.objects.link(curve_obj)

# Set as active object
bpy.context.view_layer.objects.active = curve_obj
curve_obj.select_set(True)

'''
        
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
            create_code = f"bpy.ops.mesh.primitive_cube_add(location=({obj.location_x}, {obj.location_y}, {obj.location_z}), scale=({obj.size}, {obj.size}, {obj.size}))"
        elif obj.object_type == "sphere":
            create_code = f"bpy.ops.mesh.primitive_uv_sphere_add(location=({obj.location_x}, {obj.location_y}, {obj.location_z}), radius={obj.size})"
        elif obj.object_type == "cylinder":
            create_code = f"bpy.ops.mesh.primitive_cylinder_add(location=({obj.location_x}, {obj.location_y}, {obj.location_z}), radius={obj.size}, depth={obj.size*2})"
        
        blender_code = f"""
# Create {obj.object_type}
{create_code}

# Get the created object and set name
obj = bpy.context.active_object
obj.name = "{obj.name}"

"""
        
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
        bpy.ops.wm.open_mainfile(filepath=scene_file)
        print("Loaded existing session scene")
    except Exception as e:
        print(f"Failed to load session scene: {{e}}")
        print("Starting fresh...")
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False, confirm=False)
else:
    print("No existing scene file found, starting fresh")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False, confirm=False)
    print("Cleaned default scene")

print("\\n=== EXECUTING USER CODE ===")
{user_code}

print("\\n=== SCENE SETUP ===")
# Setup camera if needed
if not any(obj.type == 'CAMERA' for obj in bpy.data.objects):
    bpy.ops.object.camera_add(location=(7, -7, 5))
    camera = bpy.context.active_object
    camera.rotation_euler = (1.1, 0, 0.785)
    bpy.context.scene.camera = camera
    camera.hide_viewport = True
    print("Added camera")
else:
    print("Camera already exists")

# Setup light if needed  
if not any(obj.type == 'LIGHT' for obj in bpy.data.objects):
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    print("Added light")
else:
    print("Light already exists")

# Save scene
bpy.ops.wm.save_as_mainfile(filepath="{self.session_blend_file}")
print(f"Scene saved as {self.session_blend_file}")

# Only render if running in background mode
if not {open_gui}:
    print("\\n=== RENDERING ===")
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
    try:
        if bpy.context.screen:
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.shading.type = 'MATERIAL_PREVIEW'
                            break
    except Exception as ex:
        print(f"Could not set viewport shading: {{ex}}")

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