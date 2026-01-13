"""Figma API - Component Methods.

Methods for working with components and component sets.
"""
from typing import Optional
from .client import figma_get


async def figma_get_team_components(
    team_id: str,
    page_size: int = 30,
    after: Optional[str] = None
) -> dict:
    """Get components in a team library.
    
    Args:
        team_id: Team ID
        page_size: Number of results (max 30)
        after: Pagination cursor
    
    Returns:
        List of team components
    """
    params = {"page_size": page_size}
    if after:
        params["after"] = after
    return await figma_get(f"/teams/{team_id}/components", params=params)


async def figma_get_file_components(file_key: str) -> dict:
    """Get components in a file.
    
    Args:
        file_key: The file key
    
    Returns:
        List of components with metadata
    """
    return await figma_get(f"/files/{file_key}/components")


async def figma_get_component(component_key: str) -> dict:
    """Get a component by key.
    
    Args:
        component_key: Component key
    
    Returns:
        Component data
    """
    return await figma_get(f"/components/{component_key}")


async def figma_get_team_component_sets(
    team_id: str,
    page_size: int = 30,
    after: Optional[str] = None
) -> dict:
    """Get component sets in a team library.
    
    Args:
        team_id: Team ID
        page_size: Number of results
        after: Pagination cursor
    
    Returns:
        List of component sets
    """
    params = {"page_size": page_size}
    if after:
        params["after"] = after
    return await figma_get(f"/teams/{team_id}/component_sets", params=params)


async def figma_get_file_component_sets(file_key: str) -> dict:
    """Get component sets in a file.
    
    Args:
        file_key: The file key
    
    Returns:
        List of component sets
    """
    return await figma_get(f"/files/{file_key}/component_sets")


async def figma_get_component_set(component_set_key: str) -> dict:
    """Get a component set by key.
    
    Args:
        component_set_key: Component set key
    
    Returns:
        Component set data
    """
    return await figma_get(f"/component_sets/{component_set_key}")
