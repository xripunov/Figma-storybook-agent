"""Figma API - Style Methods.

Methods for working with styles.
"""
from typing import Optional
from .client import figma_get


async def figma_get_team_styles(
    team_id: str,
    page_size: int = 30,
    after: Optional[str] = None
) -> dict:
    """Get styles in a team library.
    
    Args:
        team_id: Team ID
        page_size: Number of results (max 30)
        after: Pagination cursor
    
    Returns:
        List of team styles
    """
    params = {"page_size": page_size}
    if after:
        params["after"] = after
    return await figma_get(f"/teams/{team_id}/styles", params=params)


async def figma_get_file_styles(file_key: str) -> dict:
    """Get styles in a file.
    
    Args:
        file_key: The file key
    
    Returns:
        List of styles with metadata
    """
    return await figma_get(f"/files/{file_key}/styles")


async def figma_get_style(style_key: str) -> dict:
    """Get a style by key.
    
    Args:
        style_key: Style key
    
    Returns:
        Style data
    """
    return await figma_get(f"/styles/{style_key}")
