# Core Features
- Natural Language Processing
  - Interface with OpenAI-powered command interpretation
  - Automatically extracts object type, location, size, and color from free-form text commands
- Pydantic Schema Validation
  - Type-safe parameter parsing and validation system through Pydantic
- Expanded Color Recognition/Options
- Missing Attribute Analysis
  - Identifies and reports what parameters were defaulted vs. explicitly provided by user
- User Confirmation Dialogs
  - Shows parsed parameters before execution for verification
- Object Clarification Prompts
  - Interactive selection when object names are ambiguous during manipulation (compared to V1 which worked only on "last created" object)
- Session-based File Management
  - Unique session IDs for blend files and renders instead of using a fixed name "result.blend"
- Structured Output Processing
  - Uses OpenAI's structured output format for reliable command interpretation

# Limitations
- Limited Object Types
  - Only supports 3 primitive shapes (cube, sphere, cylinder)
- Basic Material System
  - Only supports color changes, no advanced materials (metallic, glass, emission, etc.)
- No Batch Operations
  - Cannot create multiple objects in a single command
- No Curves or Surfaces
  - Limited to basic mesh primitives only