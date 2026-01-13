"""Figma API - File Methods.

Methods for working with Figma files and nodes.
"""
from typing import Optional, List
from .client import figma_get


async def figma_get_file(
    file_key: str,
    version: Optional[str] = None,
    depth: Optional[int] = None,
    geometry: Optional[str] = None,
    plugin_data: Optional[str] = None,
    branch_data: Optional[bool] = None
) -> dict:
    """Get a Figma file by key.
    
    Args:
        file_key: The file key (from URL)
        version: Specific version ID
        depth: Depth of node tree to return (1-4)
        geometry: Include path data ("paths")
        plugin_data: Plugin data to include
        branch_data: Include branch metadata
    
    Returns:
        File document data
    """
    params = {}
    if version:
        params["version"] = version
    if depth:
        params["depth"] = depth
    if geometry:
        params["geometry"] = geometry
    if plugin_data:
        params["plugin_data"] = plugin_data
    if branch_data:
        params["branch_data"] = branch_data
    
    return await figma_get(f"/files/{file_key}", params=params or None)


async def figma_get_file_nodes(
    file_key: str,
    ids: List[str],
    version: Optional[str] = None,
    depth: Optional[int] = None,
    geometry: Optional[str] = None,
    plugin_data: Optional[str] = None
) -> dict:
    """Get specific nodes from a Figma file.
    
    Args:
        file_key: The file key
        ids: List of node IDs to retrieve
        version: Specific version ID
        depth: Depth of node tree
        geometry: Include path data
        plugin_data: Plugin data to include
    
    Returns:
        Requested nodes data
    """
    params = {"ids": ",".join(ids)}
    if version:
        params["version"] = version
    if depth:
        params["depth"] = depth
    if geometry:
        params["geometry"] = geometry
    if plugin_data:
        params["plugin_data"] = plugin_data
    
    return await figma_get(f"/files/{file_key}/nodes", params=params)


async def figma_get_images(
    file_key: str,
    ids: List[str],
    scale: float = 1,
    format: str = "png",
    svg_include_id: Optional[bool] = None,
    svg_simplify_stroke: Optional[bool] = None,
    use_absolute_bounds: Optional[bool] = None,
    version: Optional[str] = None
) -> dict:
    """Render images from a Figma file.
    
    Args:
        file_key: The file key
        ids: Node IDs to render
        scale: Scale factor (0.01-4)
        format: Image format (png, jpg, svg, pdf)
        svg_include_id: Include node IDs in SVG
        svg_simplify_stroke: Simplify strokes in SVG
        use_absolute_bounds: Use absolute bounds
        version: Specific version
    
    Returns:
        Dict with image URLs keyed by node ID
    """
    params = {
        "ids": ",".join(ids),
        "scale": scale,
        "format": format
    }
    if svg_include_id is not None:
        params["svg_include_id"] = svg_include_id
    if svg_simplify_stroke is not None:
        params["svg_simplify_stroke"] = svg_simplify_stroke
    if use_absolute_bounds is not None:
        params["use_absolute_bounds"] = use_absolute_bounds
    if version:
        params["version"] = version
    
    return await figma_get(f"/images/{file_key}", params=params)


async def figma_get_image_fills(file_key: str) -> dict:
    """Get image fills in a Figma file.
    
    Args:
        file_key: The file key
    
    Returns:
        Dict with image fill URLs
    """
    return await figma_get(f"/files/{file_key}/images")


async def figma_get_file_versions(file_key: str) -> dict:
    """Get version history of a Figma file.
    
    Args:
        file_key: The file key
    
    Returns:
        List of file versions with metadata
    """
    return await figma_get(f"/files/{file_key}/versions")
