"""All Pydantic models"""

from pydantic import BaseModel, Field
from typing import Literal, Optional

class MaterialProperties(BaseModel):
    material_type: Literal["basic", "metallic", "glass", "emission", "plastic", "rough"] = Field(default="basic", description="Type of material surface")
    metallic: Optional[float] = Field(default=0.0, description="Metallic factor (0.0=non-metal, 1.0=pure metal)", ge=0, le=1)
    roughness: Optional[float] = Field(default=0.5, description="Surface roughness (0.0=mirror, 1.0=rough)", ge=0, le=1)
    emission_strength: Optional[float] = Field(default=0.0, description="Emission/glow strength", ge=0)
    transparency: Optional[float] = Field(default=0.0, description="Transparency (0.0=opaque, 1.0=transparent)", ge=0, le=1)

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
    material: Optional[MaterialProperties] = Field(default=None, description="Material properties")

class CurveCreation(BaseModel):
    curve_type: Literal["bezier", "nurbs", "poly"] = Field(description="Type of curve to create")
    name: str = Field(description="Unique name for the curve")
    # Control points as list of [x, y, z] coordinates
    control_points: list[list[float]] = Field(description="List of 3D control points [[x1,y1,z1], [x2,y2,z2], ...]")
    # Curve properties
    extrude_depth: Optional[float] = Field(default=0.0, description="Extrusion depth for 3D curves")
    bevel_depth: Optional[float] = Field(default=0.0, description="Bevel depth for rounded curves")
    resolution: Optional[int] = Field(default=12, description="Curve resolution/smoothness", ge=1, le=64)
    dimensions: Literal["2D", "3D"] = Field(default="3D", description="Curve dimensions")
    # Color properties (same as ObjectCreation)
    color_r: float = Field(default=0.8, description="Red component (0-1)", ge=0, le=1)
    color_g: float = Field(default=0.8, description="Green component (0-1)", ge=0, le=1)
    color_b: float = Field(default=0.8, description="Blue component (0-1)", ge=0, le=1)
    material: Optional[MaterialProperties] = Field(default=None, description="Material properties")

class SurfaceCreation(BaseModel):
    surface_type: Literal["extrude", "revolve", "plane", "grid"] = Field(description="Type of surface")
    name: str = Field(description="Unique name for the surface")
    base_curve: Optional[str] = Field(default=None, description="Name of curve to base surface on")
    extrude_distance: Optional[float] = Field(default=1.0, description="Extrude distance")
    revolve_axis: Literal["X", "Y", "Z"] = Field(default="Z", description="Axis for revolving")
    # Plane/Grid specific parameters
    width: Optional[float] = Field(default=2.0, description="Width for plane/grid surfaces")
    height: Optional[float] = Field(default=2.0, description="Height for plane/grid surfaces")
    subdivisions: Optional[int] = Field(default=1, description="Subdivisions for grid surfaces", ge=1, le=20)
    # Color properties
    color_r: float = Field(default=0.8, description="Red component (0-1)", ge=0, le=1)
    color_g: float = Field(default=0.8, description="Green component (0-1)", ge=0, le=1)
    color_b: float = Field(default=0.8, description="Blue component (0-1)", ge=0, le=1)
    material: Optional[MaterialProperties] = Field(default=None, description="Material properties")

class ObjectDeletion(BaseModel):
    action: Literal["delete_specific", "delete_all"] = Field(description="Type of deletion action")
    object_name: Optional[str] = Field(default=None, description="Name of object to delete (required for delete_specific)")

class ObjectManipulation(BaseModel):
    manipulation_type: Literal["move", "scale", "rotate"] = Field(description="Type of manipulation to perform")
    object_name: str = Field(description="Name of object to manipulate")
    # Move parameters
    move_x: Optional[float] = Field(default=1, description="X offset for move (relative)")
    move_y: Optional[float] = Field(default=1, description="Y offset for move (relative)")
    move_z: Optional[float] = Field(default=1, description="Z offset for move (relative)")
    # Scale parameters
    scale_x: Optional[float] = Field(default=1, description="X scale factor", gt=0)
    scale_y: Optional[float] = Field(default=1, description="Y scale factor", gt=0)
    scale_z: Optional[float] = Field(default=1, description="Z scale factor", gt=0)
    scale_uniform: Optional[float] = Field(default=2, description="Uniform scale factor", gt=0)
    # Rotate parameters (in degrees)
    rotate_x: Optional[float] = Field(default=90, description="X rotation in degrees")
    rotate_y: Optional[float] = Field(default=90, description="Y rotation in degrees")
    rotate_z: Optional[float] = Field(default=90, description="Z rotation in degrees")

class ActionRequest(BaseModel):
    action_type: Literal["create", "create_curve", "create_surface", "list", "delete", "manipulate", "view", "help"] = Field(description="Type of action requested")
    creation_params: Optional[ObjectCreation] = Field(default=None, description="Parameters for object creation")
    curve_params: Optional[CurveCreation] = Field(default=None, description="Parameters for curve creation")
    surface_params: Optional[SurfaceCreation] = Field(default=None, description="Parameters for surface creation")
    deletion_params: Optional[ObjectDeletion] = Field(default=None, description="Parameters for object deletion")
    manipulation_params: Optional[ObjectManipulation] = Field(default=None, description="Parameters for object manipulation")
