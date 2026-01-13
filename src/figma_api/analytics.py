"""Figma API - Library Analytics Methods.

Methods for library usage analytics.
"""
from typing import Optional
from .client import figma_get


async def figma_get_library_analytics_component_usages(
    file_key: str,
    cursor: Optional[str] = None
) -> dict:
    """Get library analytics component usage data.
    
    Args:
        file_key: Library file key
        cursor: Pagination cursor
    
    Returns:
        Component usage analytics
    """
    params = {"cursor": cursor} if cursor else None
    return await figma_get(f"/analytics/libraries/{file_key}/component_usages", params=params)


async def figma_get_library_analytics_style_usages(
    file_key: str,
    cursor: Optional[str] = None
) -> dict:
    """Get library analytics style usage data.
    
    Args:
        file_key: Library file key
        cursor: Pagination cursor
    
    Returns:
        Style usage analytics
    """
    params = {"cursor": cursor} if cursor else None
    return await figma_get(f"/analytics/libraries/{file_key}/style_usages", params=params)


async def figma_get_library_analytics_variable_usages(
    file_key: str,
    cursor: Optional[str] = None
) -> dict:
    """Get library analytics variable usage data.
    
    Args:
        file_key: Library file key
        cursor: Pagination cursor
    
    Returns:
        Variable usage analytics
    """
    params = {"cursor": cursor} if cursor else None
    return await figma_get(f"/analytics/libraries/{file_key}/variable_usages", params=params)
