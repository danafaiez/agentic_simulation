from object_registry import load_object_registry

def show_main_menu():
    """Display the main menu and get user choice"""

    print("\n" + "="*50)
    print("       BLENDER AGENT - V1")
    print("="*50)

    print("1. Create Object")
    print("2. Manipulate Object") 
    print("3. Delete Object")    
    print("4. List Objects")     
    print("5. Exit")
    print("-"*50)
    
    while True:
        choice = input("Select an option (1-5): ").strip()
        if choice in ['1', '2', '3', '4', '5']:
            return choice
        print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")

def show_object_menu():
    """Display object creation menu and get parameters"""

    print("\n" + "="*40)
    print("       CREATE OBJECT")
    print("="*40)
    
    # Object type selection
    print("Object Types:")
    print("1. Cube")
    print("2. Sphere") 
    print("3. Cylinder")
    
    while True:
        obj_choice = input("Select object type (1-3): ").strip()
        if obj_choice in ['1', '2', '3']:
            obj_types = {'1': 'cube', '2': 'sphere', '3': 'cylinder'}
            object_type = obj_types[obj_choice]
            break
        print("Invalid choice. Please enter 1, 2, or 3.")
    
    # Location input
    print("\nLocation (x, y, z coordinates):")
    x = float(input("X coordinate (default 0): ") or "0")
    y = float(input("Y coordinate (default 0): ") or "0")
    z = float(input("Z coordinate (default 0): ") or "0")
    location = (x, y, z)
    
    # Size input
    size = float(input("Size (default 1.0): ") or "1.0")
    
    # Color selection
    print("\nColor Options:")
    print("1. Red")
    print("2. Green")
    print("3. Blue")
    print("4. Yellow")
    print("5. Purple")
    print("6. Cyan")
    print("7. Gray")
    print("8. Custom (enter RGB values)")
    
    while True:
        color_choice = input("Select color (1-8): ").strip()
        if color_choice in ['1', '2', '3', '4', '5', '6', '7', '8']:
            colors = {
                '1': (1, 0, 0, 1),      # Red
                '2': (0, 1, 0, 1),      # Green
                '3': (0, 0, 1, 1),      # Blue
                '4': (1, 1, 0, 1),      # Yellow
                '5': (1, 0, 1, 1),      # Purple
                '6': (0, 1, 1, 1),      # Cyan
                '7': (0.5, 0.5, 0.5, 1) # Gray
            }
            if color_choice == '8':
                r = float(input("Red (0-1): "))
                g = float(input("Green (0-1): "))
                b = float(input("Blue (0-1): "))
                color = (r, g, b, 1)
            else:
                color = colors[color_choice]
            break
        print("Invalid choice. Please enter 1-8.")
    
    # Mandatory name with duplicate checking
    objects = load_object_registry()
    while True:
        name = input("Object name (required): ").strip()
        if not name:
            print("Name cannot be empty. Please enter a name for the object.")
            continue
        if name in objects:
            print(f"Object named '{name}' already exists. Please choose a different name.")
            continue
        break
    
    return object_type, location, size, color, name

def show_delete_menu():
    """Show available objects and let user select which to delete"""
    objects = load_object_registry()
    if not objects:
        print("\nNo objects to delete.")
        return None, None
    # Listing all object names, followed by an option for deleting all or canceling.    
    print("\n" + "="*40)
    print("       DELETE OBJECT")
    print("="*40)
    
    print("Available objects:")
    for i, name in enumerate(objects, 1):
        print(f"  {i}. {name}")
    
    print(f"\n{len(objects)+1}. Delete all objects")
    print(f"{len(objects)+2}. Cancel")
    
    while True:
        try:
            choice = int(input(f"Select option (1-{len(objects)+2}): "))
            if 1 <= choice <= len(objects):
                return 'delete_by_name', {'name': objects[choice-1]}
            elif choice == len(objects)+1:
                confirm = input("Delete ALL objects? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    return 'delete_all', {}
                else:
                    return None, None
            elif choice == len(objects)+2:
                return None, None
            else:
                print(f"Invalid choice. Please enter 1-{len(objects)+2}.")
        except ValueError:
            print("Please enter a number.")

def show_manipulation_menu():
    """Display object manipulation menu and get parameters. 
    
    Returns a string, indicating the type of manipulation, and a dictionary indicating the attribute(s) needed for that manipulation.
    """
    objects = load_object_registry()
    if not objects:
        print("\nNo objects to manipulate. Create an object first.")
        return None, None
        
    print("\n" + "="*40)
    print("    MANIPULATE OBJECT")
    print("="*40)

    print("Operations:")
    print("1. Move Object")
    print("2. Scale Object")
    print("3. Rotate Object")
    
    while True:
        op_choice = input("Select operation (1-3): ").strip()
        if op_choice in ['1', '2', '3']:
            break
        print("Invalid choice. Please enter 1, 2, or 3.")
    
    if op_choice == '1':  # Move
        print("\nMove Options:")
        print("1. Relative movement (offset)")
        print("2. Absolute position")
        
        move_type = input("Select move type (1-2): ").strip()
        if move_type == '1':
            x = float(input("X offset: ") or "0")
            y = float(input("Y offset: ") or "0") 
            z = float(input("Z offset: ") or "0")
            return 'move', {'offset': (x, y, z)}
        else:
            x = float(input("X position: ") or "0")
            y = float(input("Y position: ") or "0")
            z = float(input("Z position: ") or "0") 
            return 'move', {'absolute_position': (x, y, z)}
    
    elif op_choice == '2':  # Scale
        print("\nScale Options:")
        print("1. Uniform scale (same for all axes)")
        print("2. Non-uniform scale (different for each axis)")
        
        scale_type = input("Select scale type (1-2): ").strip()
        if scale_type == '1':
            factor = float(input("Scale factor: ") or "1")
            return 'scale', {'scale_factor': (factor, factor, factor)}
        else:
            x = float(input("X scale factor: ") or "1")
            y = float(input("Y scale factor: ") or "1")
            z = float(input("Z scale factor: ") or "1")
            return 'scale', {'scale_factor': (x, y, z)}
    
    elif op_choice == '3':  # Rotate
        print("\nRotation (in degrees):")
        x = float(input("X rotation: ") or "0")
        y = float(input("Y rotation: ") or "0")
        z = float(input("Z rotation: ") or "0")
        return 'rotate', {'rotation_degrees': (x, y, z)}