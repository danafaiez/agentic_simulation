import subprocess
import tempfile
from config import BLENDER_PATH

def generate_blender_script(commands):
    """Generate Blender script given user commands"""

    functions_code = '''
    import bpy
    import math
    import os

    def create_object(object_type, location=(0, 0, 0), size=1.0, color=(0.8, 0.8, 0.8, 1.0), name=None):
        if object_type.lower() == 'cube':
            bpy.ops.mesh.primitive_cube_add(location=location, scale=(size, size, size))
        elif object_type.lower() == 'sphere':
            bpy.ops.mesh.primitive_uv_sphere_add(location=location, radius=size)
        elif object_type.lower() == 'cylinder':
            bpy.ops.mesh.primitive_cylinder_add(location=location, radius=size, depth=size*2)
        else:
            print(f"ERROR: Unsupported object type: {object_type}")
            return None
        
        obj = bpy.context.active_object
        if name:
            obj.name = name
        else:
            print("ERROR: Name is required")
            return None
        
        # giving all objects the same default material -- this is needed to provide color
        material_name = f"{obj.name}_Material"
        material = bpy.data.materials.new(name=material_name)
        material.use_nodes = True
        material.node_tree.nodes["Principled BSDF"].inputs[0].default_value = color
        obj.data.materials.append(material)
        
        print(f"SUCCESS: Created {object_type} '{obj.name}' at {location} with size {size}")
        return obj

    def delete_object_by_name(name):
        if name in bpy.data.objects:
            obj = bpy.data.objects[name]
            if obj.type == 'MESH':
                bpy.data.objects.remove(obj, do_unlink=True)
                print(f"SUCCESS: Deleted object '{name}'")
                return True
            else:
                print(f"ERROR: '{name}' is not a mesh object")
                return False
        else:
            print(f"ERROR: No object named '{name}' found")
            return False

    def delete_all_objects():
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        count = len(mesh_objects)
        for obj in mesh_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        print(f"SUCCESS: Deleted {count} objects")
        return True

    def move_object(obj=None, offset=(0, 0, 0), absolute_position=None):
        # In VI, obj will always be None
        if obj is None:
            # get all mesh_objects and then use the last one to move -- this logic is used for simplicity for V1
            mesh_objects = [o for o in bpy.data.objects if o.type == 'MESH']
            if mesh_objects:
                obj = mesh_objects[-1]  # Use last created object
            else:
                print("ERROR: No objects to manipulate")
                return False
        
        if absolute_position:
            obj.location = absolute_position
            print(f"SUCCESS: Moved '{obj.name}' to absolute position {absolute_position}")
        else:
            obj.location.x += offset[0]
            obj.location.y += offset[1] 
            obj.location.z += offset[2]
            print(f"SUCCESS: Moved '{obj.name}' by offset {offset} to {obj.location}")
        return True

    def scale_object(obj=None, scale_factor=(1, 1, 1)):
        if obj is None:
            # get all mesh_objects and then use the last one to move -- this logic is used for simplicity for V1
            mesh_objects = [o for o in bpy.data.objects if o.type == 'MESH']
            if mesh_objects:
                obj = mesh_objects[-1]  # Use last created object
            else:
                print("ERROR: No objects to manipulate")
                return False
        
        obj.scale.x *= scale_factor[0]
        obj.scale.y *= scale_factor[1]
        obj.scale.z *= scale_factor[2]
        print(f"SUCCESS: Scaled '{obj.name}' by factor {scale_factor} to {obj.scale}")
        return True

    def rotate_object(obj=None, rotation_degrees=(0, 0, 0)):
        if obj is None:
            # get all mesh_objects and then use the last one to move -- this logic is used for simplicity for V1
            mesh_objects = [o for o in bpy.data.objects if o.type == 'MESH']
            if mesh_objects:
                obj = mesh_objects[-1]  # Use last created object
            else:
                print("ERROR: No objects to manipulate")
                return False
        
        obj.rotation_euler.x += math.radians(rotation_degrees[0])
        obj.rotation_euler.y += math.radians(rotation_degrees[1])
        obj.rotation_euler.z += math.radians(rotation_degrees[2])
        current_degrees = (
            math.degrees(obj.rotation_euler.x),
            math.degrees(obj.rotation_euler.y),
            math.degrees(obj.rotation_euler.z)
        )
        print(f"SUCCESS: Rotated '{obj.name}' by {rotation_degrees} degrees to {current_degrees}")
        return True
    '''
        
    setup_code = '''
    # Load existing scene if it exists.  This allows users to build scenes incrementally across multiple program runs.
    
    scene_file = os.path.abspath("result.blend")
    if os.path.exists(scene_file):
        try:
            bpy.ops.wm.open_mainfile(filepath=scene_file)
            print("SUCCESS: Loaded existing scene from result.blend")
        except Exception as e:
            print(f"ERROR: Could not load scene file: {e}")
            if "Cube" in bpy.data.objects:
                bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)
                print("Removed default cube")
    else:
        if "Cube" in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)
            print("Removed default cube - starting fresh")
    '''
        
    render_code = '''
    # Add camera - needed for render.render and creating an image to be later saved as PNG
    # Camera defines the viewing angle/orientation etc for the final image
    if not any(obj.type == 'CAMERA' for obj in bpy.data.objects):
        bpy.ops.object.camera_add(location=(7, -7, 5))
        camera = bpy.context.active_object
        camera.rotation_euler = (1.1, 0, 0.785)
        bpy.context.scene.camera = camera

    # Add light if needed  
    if not any(obj.type == 'LIGHT' for obj in bpy.data.objects):
        bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))

    # Render settings
    scene = bpy.context.scene
    scene.render.filepath = "result_render.png"
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = 800
    scene.render.resolution_y = 600

    # Render
    bpy.ops.render.render(write_still=True)
    print("Screenshot saved as result_render.png!")

    # Save blend file
    bpy.ops.wm.save_as_mainfile(filepath="result.blend")
    print("Saved result to result.blend")
    '''
        
    return functions_code + setup_code + commands + render_code

def run_blender_script(script_content):
    """Execute the Blender script"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        script_path = f.name
    
    
    print("Running Blender...")
    result = subprocess.run([BLENDER_PATH, "--background", "--python", script_path])
    print(f"Blender finished with exit code: {result.returncode}")
    
    if result.returncode == 0:
        print("Success! Check 'result_render.png' and 'result.blend'")
    else:
        print("Error occurred during execution")
