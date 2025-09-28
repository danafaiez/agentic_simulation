# Core Features

## Menu-driven Interface
- Text-based menu system with numbered options for user navigation

## Object Creation
- Create cubes, spheres, and cylinders with customizable parameters

## Location Control
- Set object position using X, Y, Z coordinates (both relative and absolute)

## Size Adjustment
- Scale objects uniformly during creation

## Color Customization
- 7 preset colors plus custom RGB input capability

## Object Naming
- Mandatory unique naming system with duplicate prevention

## Object Manipulation
- Move, scale, and rotate existing objects

## Deletion System
- Delete individual objects by name or all objects at once

## Object Registry
- JSON-based file system to track created objects across sessions

## Scene Persistence
- Saves Blender scene as "result.blend" file

## Automatic Rendering
- Generates PNG screenshots of the scene

## Camera and Lighting Setup
- Automatically adds camera and sun light if missing

# V1 Limitations

## No Natural Language Processing
- Requires navigating through multiple menu levels instead of simple commands

## Limited Object Types
- Only supports 3 primitive shapes (cube, sphere, cylinder)

## Basic Material System
- Only supports color changes, no advanced materials (metallic, glass, emission, etc.)

## No Batch Operations
- Cannot create multiple objects in a single operation

## No Curves or Surfaces
- Limited to basic mesh primitives only

## Hardcoded Blender Path
- Fixed to macOS installation path, not portable across systems

## Sequential Workflow
- Must complete one operation before starting another

## Limited Manipulation Options
- Basic move/scale/rotate only, no advanced transformations

## No Object Selection
- Manipulation operations work on "last created" object rather than specific selection

## No Error Recovery
- If Blender execution fails, user must restart the process