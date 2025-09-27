import json
import os
from config import REGISTRY_FILE

def load_object_registry():
    """Load object registry from local file"""
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_object_registry(objects):
    """Save objects to local json file"""
    try:
        with open(REGISTRY_FILE, 'w') as f:
            json.dump(objects, f, indent=2)
    except Exception as e:
        print(f"Error saving registry: {e}")

def add_to_registry(name):
    """Add object to registry"""
    objects = load_object_registry()
    if name not in objects:
        objects.append(name)
        save_object_registry(objects)

def remove_from_registry(name):
    """Remove object from registry"""
    objects = load_object_registry()
    if name in objects:
        objects.remove(name)
        save_object_registry(objects)

def clear_registry():
    """Clear all objects from registry"""
    save_object_registry([])

def list_objects_from_registry():
    """List objects from local registry"""
    objects = load_object_registry()
    if objects:
        print("\nAvailable objects:")
        for i, name in enumerate(objects, 1):
            print(f"  {i}. {name}")
        return objects
    else:
        print("\nNo objects in the scene")
        return []