"""Entry point and main function"""

from blender_agent import SchemaBlenderAgent
import os

def main():
    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("OpenAI API key not found in environment")
        api_key = input("Enter OpenAI API key: ").strip()
        if not api_key:
            print("API key required")
            return
    
    agent = SchemaBlenderAgent(api_key)
    
    print("="*50)
    print("    BLENDER 3D MODELING AGENT")
    print("="*50)
    print("Available commands:")
    print("- create objects (cube, sphere, cylinder)")
    print("- create multiple objects (3 red cubes and 2 blue spheres)")
    print("- list objects")
    print("- view scene")
    print("- help")
    print("- quit")
    print()
    print("Examples:")
    print("'create red cube'")
    print("'create 3 green cubes and 2 blue spheres'")
    print("'help'")
    print("="*50)
    
    while True:
        user_input = input("\n> ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
            
        if not user_input:
            continue
        
        # Parse the request
        print("Parsing your request...")
        parsed_request = agent.parse_user_request(user_input)
        
        if not parsed_request:
            print("Failed to parse your request. Try being more specific.")
            continue
        
        # Handle different action types
        if parsed_request.action_type == "list":
            agent.list_objects_from_registry()
            
        elif parsed_request.action_type == "batch_create":
            if not parsed_request.batch_params:
                print("Error: No batch parameters found.")
                continue
            
            success = agent.process_batch_creation(parsed_request.batch_params)
            if not success:
                continue
            
        elif parsed_request.action_type == "create":
            if not parsed_request.creation_params:
                print("Error: No creation parameters found.")
                continue
                
            creation_params = parsed_request.creation_params
            creation_params.name = agent.validate_name(creation_params.name)
            agent.used_names.add(creation_params.name)
            
            if not agent.show_parsed_info(creation_params):
                print("Creation cancelled")
                continue
            
            blender_code = agent.generate_blender_code(creation_params)
            success = agent.run_blender_script(blender_code)
            
            if success:
                agent.add_to_registry(creation_params.name)
                print(f"Successfully created {creation_params.name}!")
            else:
                print("Failed to create object")

        elif parsed_request.action_type == "create_curve":
            if not parsed_request.curve_params:
                print("Error: No curve parameters found.")
                continue
                
            curve_params = parsed_request.curve_params
            curve_params.name = agent.validate_name(curve_params.name)
            agent.used_names.add(curve_params.name)
            
            if not agent.show_curve_info(curve_params):
                print("Curve creation cancelled")
                continue
            
            curve_code = agent.generate_curve_code(curve_params)
            success = agent.run_blender_script(curve_code)
            
            if success:
                agent.add_to_registry(curve_params.name)
                print(f"Successfully created {curve_params.curve_type} curve {curve_params.name}!")
            else:
                print("Failed to create curve")

        elif parsed_request.action_type == "create_surface":
            if not parsed_request.surface_params:
                print("Error: No surface parameters found.")
                continue
                
            surface_params = parsed_request.surface_params
            surface_params.name = agent.validate_name(surface_params.name)
            agent.used_names.add(surface_params.name)
            
            if not agent.show_surface_info(surface_params):
                print("Surface creation cancelled")
                continue
            
            surface_code = agent.generate_surface_code(surface_params)
            success = agent.run_blender_script(surface_code)
            
            if success:
                agent.add_to_registry(surface_params.name)
                print(f"Successfully created {surface_params.surface_type} surface {surface_params.name}!")
            else:
                print("Failed to create surface")
                
        elif parsed_request.action_type == "delete":
            if not parsed_request.deletion_params:
                print("Error: No deletion parameters found.")
                continue
                
            if not agent.confirm_deletion(parsed_request.deletion_params):
                print("Deletion cancelled")
                continue
            
            deletion_code = agent.generate_deletion_code(parsed_request.deletion_params)
            success = agent.run_blender_script(deletion_code)
            
            if success:
                if parsed_request.deletion_params.action == "delete_all":
                    agent.clear_registry()
                    agent.used_names.clear()
                    print("Successfully deleted all objects!")
                else:
                    agent.remove_from_registry(parsed_request.deletion_params.object_name)
                    print(f"Successfully deleted {parsed_request.deletion_params.object_name}!")
            else:
                print("Failed to delete object(s)")
        
        elif parsed_request.action_type == "manipulate":
            if not parsed_request.manipulation_params:
                print("Error: No manipulation parameters found.")
                continue
            
            manipulation_params = parsed_request.manipulation_params
            
            if not manipulation_params.object_name or manipulation_params.object_name not in agent.objects_registry:
                manipulation_type = manipulation_params.manipulation_type if manipulation_params.manipulation_type else "manipulate"
                clarified_name = agent.ask_for_object_clarification(manipulation_type)
                
                if not clarified_name:
                    print("Manipulation cancelled")
                    continue
                
                manipulation_params.object_name = clarified_name
            
            is_valid, error_message = agent.validate_manipulation_request(manipulation_params)
            if not is_valid:
                print(f"Error: {error_message}")
                continue
            
            manipulation_params = agent.get_manipulation_defaults(manipulation_params)
            
            if not agent.show_manipulation_info(manipulation_params):
                print("Manipulation cancelled")
                continue
            
            manipulation_code = agent.generate_manipulation_code(manipulation_params)
            success = agent.run_blender_script(manipulation_code)
            
            if success:
                print(f"Successfully {manipulation_params.manipulation_type}d {manipulation_params.object_name}!")
            else:
                print(f"Failed to {manipulation_params.manipulation_type} object")
        
        elif parsed_request.action_type == "view":
            print("Opening Blender GUI to view the current scene...")
            success = agent.run_blender_script("# View current scene", open_gui=True)
            if success:
                print("Blender GUI opened successfully!")
            else:
                print("Failed to open Blender GUI")
        
        elif parsed_request.action_type == "help":
            agent.show_detailed_help()
        
        else:
            print("Unsupported action type. Try 'create', 'list', 'view', or 'help'.")

if __name__ == "__main__":
    main()