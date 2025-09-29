# Core Features

- Batch Creation System
    - Can create multiple objects/surfaces/curves in a single command
    - Parses numeric quantities and generates multiple instances
        - "create 3 red cubes and 2 blue spheres"
        - "make 5 green cylinders"
    - Handles mixed object types and materials in one request
    - Parses numeric quantities and generates multiple instances
    - Automatically creates unique names (red_cube_1, red_cube_2, etc.)

# V4 Limitations

- Limited Primitives
    - Only supports cubes, spheres, and cylinders - no complex meshes or imported models
    - No customized positioning when creating multiple surfaces/curves. Customized positioning only applies to objects. 
    
- No Animation