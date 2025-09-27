from schemas import ObjectCreation, ObjectDeletion, ObjectManipulation, ActionRequest
from config import BLENDER_PATH
from openai import OpenAI
import subprocess
import tempfile
import time
import math
from typing import Optional


class SchemaBlenderAgent:
    """An agent class; requires an api_key from OpenAI"""
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.blender_path = "/Applications/Blender.app/Contents/MacOS/Blender"
        self.used_names = set()  # Track used object names
        self.objects_registry = []  # Track created objects for listing/deletion
        
        # Create session identifier based on time of creation, for unique file names
        self.session_id = int(time.time())
        self.session_blend_file = f"result_{self.session_id}.blend"
        self.session_render_file = f"result_render_{self.session_id}.png"
        
        print(f"Session ID: {self.session_id}")
        print(f"Scene file: {self.session_blend_file}")
        print(f"Render file: {self.session_render_file}")
        
        # Colors
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
        """Generate a unique name by adding numbers if needed; used when user did not provide a name."""
        if base_name not in self.used_names:
            return base_name
        
        counter = 1
        while f"{base_name}_{counter}" in self.used_names:
            counter += 1
        return f"{base_name}_{counter}"
    
    def validate_name(self, requested_name: str) -> str:
        """Validate and potentially modify the requested name to ensure uniqueness; happens if use is reusing a name."""
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
        2. LIST: "list", "show", "what objects" 
        3. DELETE: "delete", "remove" + object name OR "delete all"
        4. MANIPULATE: "move", "scale", "rotate" + object name + parameters

        FOR CREATE ACTIONS:
        - object_type: Must be exactly "cube", "sphere", or "cylinder"
        - name: Generate descriptive name if not provided
        - location: Use coordinates if mentioned, default (0,0,0)
        - size: Default 1.0 if not specified
        - color: Convert color names to RGB. 

        FOR DELETE ACTIONS:
        - action: "delete_specific" for named object, "delete_all" for all objects
        - object_name: Required for delete_specific, must match existing object

        FOR MANIPULATE ACTIONS:
        - manipulation_type: "move", "scale", or "rotate"
        - object_name: Required, must match existing object
        - MOVE: move_x, move_y, move_z (relative offsets, default 0 if not specified)
        - SCALE: scale_uniform OR scale_x/scale_y/scale_z (scale factors, default 1.0 if not specified)
        - ROTATE: rotate_x, rotate_y, rotate_z (degrees, default 0 if not specified)

        Examples:
        - "move cube1 by 2,3,1" -> move_x=2, move_y=3, move_z=1
        - "scale sphere uniformly by 2" -> scale_uniform=2
        - "rotate cylinder 45 degrees on x axis" -> rotate_x=45
        - "scale cube to 2x on x, 3x on y" -> scale_x=2, scale_y=3

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
            print('provided:', provided)
        else:
            # check if color rgb was set to default -- edge case here is if user asked 
            # for light grey and agent created an egb of (0.8,0.8,0.8). 
            # Agent would let user know a default gray will be used as color is missing 
            # but result would still be correct and a light grey will be used. 
            if parsed_obj.color_r != 0.8 and parsed_obj.color_g != 0.8 and parsed_obj.color_b != 0.8:
                provided.append("color")
                print('2nd  else')
            else:
                defaulted.append("color (defaulted to gray)")
                print('provided:', provided)
        
        # Show results and let user know if they are ok with it
        if defaulted:
            print(f"\nNote: The following attributes were missing, so I provided default values:")
            for attr in defaulted:
                print(f"  - {attr}")
            print("Let me know if you want to change any of these defaults.")
        
        if provided:
            print(f"\nProvided attributes: {', '.join(provided)}")

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

# Create material and set color
material = bpy.data.materials.new(name="{obj.name}_Material")
material.use_nodes = True
material.node_tree.nodes["Principled BSDF"].inputs[0].default_value = ({obj.color_r}, {obj.color_g}, {obj.color_b}, 1.0)

# Apply material to object
obj.data.materials.append(material)

print(f"Created {obj.object_type} '{obj.name}' successfully")
"""
        return blender_code
    
    def run_blender_script(self, user_code: str) -> bool:
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
        # Print what objects are in scene before loading
        mesh_objects_before = [obj.name for obj in bpy.data.objects if obj.type == 'MESH']
        print(f"Objects in default scene before loading: {{mesh_objects_before}}")
        
        bpy.ops.wm.open_mainfile(filepath=scene_file)
        
        # Print what objects are in scene after loading
        mesh_objects_after = [obj.name for obj in bpy.data.objects if obj.type == 'MESH']
        print(f"Objects in scene after loading: {{mesh_objects_after}}")
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

mesh_objects = [obj.name for obj in bpy.data.objects if obj.type == 'MESH']
print(f"\\nTARGET MESH OBJECTS TO RENDER: {{mesh_objects}}")
print(f"Total mesh objects: {{len(mesh_objects)}}")

print("\\n=== RENDERING ===")
# Render scene
scene = bpy.context.scene
scene.render.filepath = "{self.session_render_file}"
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_x = 800
scene.render.resolution_y = 600
bpy.ops.render.render(write_still=True)
print(f"Screenshot saved as {self.session_render_file}")

# Save result
bpy.ops.wm.save_as_mainfile(filepath="{self.session_blend_file}")
print(f"Scene saved as {self.session_blend_file}")

print("=== BLENDER SESSION END ===")
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(full_script)
            script_path = f.name
        
        print("Running Blender...")
        result = subprocess.run([self.blender_path, "--background", "--python", script_path])
        
        return result.returncode == 0