from pydantic import BaseModel, Field
from typing import Literal, Optional

class ObjectCreation(BaseModel):
    object_type: Literal["cube", "sphere", "cylinder"] = Field(description="Type of 3D object to create")
    name: str = Field(description="Unique name for the object")
    location_x: float = Field(default=0.0, description="X coordinate position")
    location_y: float = Field(default=0.0, description="Y coordinate position") 
    location_z: float = Field(default=0.0, description="Z coordinate position")
    size: float = Field(default=1.0, description="Size/scale of the object", gt=0)
    color_r: float = Field(default=0.8, description="Red component (0-1)", ge=0, le=1)
    color_g: float = Field(default=0.8, description="Green component (0-1)", ge=0, le=1)
    color_b: float = Field(default=0.8, description="Blue component (0-1)", ge=0, le=1)

class ObjectDeletion(BaseModel):
    action: Literal["delete_specific", "delete_all"] = Field(description="Type of deletion action")
    object_name: Optional[str] = Field(default=None, description="Name of object to delete (required for delete_specific)")

class ObjectManipulation(BaseModel):
    manipulation_type: Literal["move", "scale", "rotate"] = Field(description="Type of manipulation to perform")
    object_name: str = Field(description="Name of object to manipulate")
    # Move parameters
    move_x: Optional[float] = Field(default=None, description="X offset for move (relative)")
    move_y: Optional[float] = Field(default=None, description="Y offset for move (relative)")
    move_z: Optional[float] = Field(default=None, description="Z offset for move (relative)")
    # Scale parameters
    scale_x: Optional[float] = Field(default=None, description="X scale factor", gt=0)
    scale_y: Optional[float] = Field(default=None, description="Y scale factor", gt=0)
    scale_z: Optional[float] = Field(default=None, description="Z scale factor", gt=0)
    scale_uniform: Optional[float] = Field(default=None, description="Uniform scale factor", gt=0)
    # Rotate parameters (in degrees)
    rotate_x: Optional[float] = Field(default=None, description="X rotation in degrees")
    rotate_y: Optional[float] = Field(default=None, description="Y rotation in degrees")
    rotate_z: Optional[float] = Field(default=None, description="Z rotation in degrees")

class ActionRequest(BaseModel):
    """top-level schema that GPT returns when parsing user input"""
    action_type: Literal["create", "list", "delete", "manipulate"] = Field(description="Type of action requested")
    creation_params: Optional[ObjectCreation] = Field(default=None, description="Parameters for object creation")
    deletion_params: Optional[ObjectDeletion] = Field(default=None, description="Parameters for object deletion")
    manipulation_params: Optional[ObjectManipulation] = Field(default=None, description="Parameters for object manipulation")