from ui_menus import show_main_menu, show_object_menu, show_delete_menu, show_manipulation_menu
from object_registry import add_to_registry, remove_from_registry, clear_registry, list_objects_from_registry
from blender_interface import run_blender_script, generate_blender_script


def main():
    while True:
        choice = show_main_menu()
        
        # Create Object
        if choice == '1':  
            obj_type, location, size, color, name = show_object_menu()
            
            command = f"create_object('{obj_type}', location={location}, size={size}, color={color}, name='{name}')\n"
            
            print(f"\nGenerating command: {command}")
            script = generate_blender_script(command)
            run_blender_script(script)
            
            # Add to local registry after successful creation
            add_to_registry(name)
            
        elif choice == '2':  # Manipulate Object
            result = show_manipulation_menu()
            if result[0] is not None:
                operation, params = result
                
                if operation == 'move':
                    if 'offset' in params:
                        command = f"move_object(offset={params['offset']})\n"
                    else:
                        command = f"move_object(absolute_position={params['absolute_position']})\n"
                elif operation == 'scale':
                    command = f"scale_object(scale_factor={params['scale_factor']})\n"
                elif operation == 'rotate':
                    command = f"rotate_object(rotation_degrees={params['rotation_degrees']})\n"
                
                print(f"\nGenerating command: {command}")
                script = generate_blender_script(command)
                run_blender_script(script)
            
        elif choice == '3':  # Delete Object
            result = show_delete_menu()
            if result[0] is not None:
                operation, params = result
                
                if operation == 'delete_by_name':
                    name = params['name']
                    command = f"delete_object_by_name('{name}')\n"
                    # Remove from local registry
                    remove_from_registry(name)
                elif operation == 'delete_all':
                    command = "delete_all_objects()\n"
                    # Clear local registry
                    clear_registry()
                
                print(f"\nGenerating command: {command}")
                script = generate_blender_script(command)
                run_blender_script(script)
                
        elif choice == '4':  # List Objects
            list_objects_from_registry()
            
        elif choice == '5':  # Exit
            print("Goodbye!")
            break

if __name__ == "__main__":
    main()