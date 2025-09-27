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
    print("    CONVERSATIONAL BLENDER AGENT")
    print("="*50)

    print("AVAILABLE COMMANDS:")
    print()
    print("CREATE OBJECTS:")
    print("  'create [color] [object_type] [at location] [size N]'")
    print("  Object types: cube, sphere, cylinder")
    print("  Colors: red, green, blue, yellow, purple, cyan, white, black, gray")
    print("  Examples: 'create red cube' | 'create blue sphere at 2,3,1'")
    print()
    print("LIST OBJECTS:")
    print("  'list objects' | 'show objects'")
    print()
    print("DELETE OBJECTS:")
    print("  'delete [object_name]' | 'delete all objects'")
    print("  Examples: 'delete cube_1' | 'delete all objects'")
    print()
    print("MANIPULATE OBJECTS:")
    print("  Move: 'move [object] by [x,y,z]' (relative positioning)")
    print("        'move [object] to [x,y,z]' (absolute positioning)")
    print("  Scale: 'scale [object] by [factor]' (uniform scaling)")
    print("         'scale [object] to [x]x on [axis]' (per-axis scaling)")
    print("  Rotate: 'rotate [object] [degrees] degrees on [x/y/z] axis'")
    print("  Examples: 'move cube1 by 2,3,1' | 'scale sphere by 1.5'")
    print()
    print("NOTE: Commands are processed one at a time. Multiple actions")
    print("      in a single command are not supported.")
    print()
    print("Type 'quit' to exit")
    print("="*50)
    
    
    while True:
        user_input = input("\n> ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Goodbye, see you next time!")
            break
            
        if not user_input:
            continue
        
        # Step 1: Parse the request
        print("Parsing your request...")
        parsed_request = agent.parse_user_request(user_input)
        #print('==== parsed_request;', parsed_request)
        
        if not parsed_request:
            print("Failed to parse your request. Try being more specific.")
            continue
        
        # Step 2: Handle different action types
        if parsed_request.action_type == "list":
            agent.list_objects_from_registry()
            
        elif parsed_request.action_type == "create":
            if not parsed_request.creation_params:
                print("Error: No creation parameters found.")
                continue
                
            # Validate and ensure unique name
            creation_params = parsed_request.creation_params
            creation_params.name = agent.validate_name(creation_params.name)
            agent.used_names.add(creation_params.name)
            
            # Analyze missing attributes
            agent.analyze_missing_attributes(user_input, creation_params)
            
            # Show parsed info and confirm
            if not agent.show_parsed_info(creation_params):
                print("Creation cancelled")
                continue
            
            # Generate and execute Blender code
            blender_code = agent.generate_blender_code(creation_params)
            success = agent.run_blender_script(blender_code)
            
            if success:
                agent.add_to_registry(creation_params.name)
                print(f"Successfully created {creation_params.name}!")
            else:
                print("Failed to create object")
                
        elif parsed_request.action_type == "delete":
            if not parsed_request.deletion_params:
                print("Error: No deletion parameters found.")
                continue
                
            # Confirm deletion
            if not agent.confirm_deletion(parsed_request.deletion_params):
                print("Deletion cancelled")
                continue
            
            # Generate and execute deletion code
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
            
            # Check if object name is missing or unclear
            if not manipulation_params.object_name or manipulation_params.object_name not in agent.objects_registry:
                # Try to extract manipulation type for clarification
                manipulation_type = manipulation_params.manipulation_type if manipulation_params.manipulation_type else "manipulate"
                clarified_name = agent.ask_for_object_clarification(manipulation_type)
                
                if not clarified_name:
                    print("Manipulation cancelled")
                    continue
                
                manipulation_params.object_name = clarified_name
            
            # Validate the manipulation request
            is_valid, error_message = agent.validate_manipulation_request(manipulation_params)
            if not is_valid:
                print(f"Error: {error_message}")
                continue
            
            # Apply default values for missing parameters
            manipulation_params = agent.get_manipulation_defaults(manipulation_params)
            
            # Show parsed info and confirm
            if not agent.show_manipulation_info(manipulation_params):
                print("Manipulation cancelled")
                continue
            
            # Generate and execute manipulation code
            manipulation_code = agent.generate_manipulation_code(manipulation_params)
            success = agent.run_blender_script(manipulation_code)
            
            if success:
                print(f"Successfully {manipulation_params.manipulation_type}d {manipulation_params.object_name}!")
            else:
                print(f"Failed to {manipulation_params.manipulation_type} object")
        
        else:
            print("Unsupported action type. Try 'create', 'list', 'delete', or 'manipulate'.")

if __name__ == "__main__":
    main()