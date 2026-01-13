"""Figma API Base Client.

Provides async HTTP client for all Figma API endpoints.
"""
import httpx
import os
from typing import Optional, Any
from dataclasses import dataclass


FIGMA_API_BASE = "https://api.figma.com/v1"
FIGMA_API_V2 = "https://api.figma.com/v2"


@dataclass
class FigmaConfig:
    """Configuration for Figma API client."""
    api_key: str
    timeout: float = 30.0


_config: Optional[FigmaConfig] = None


def get_config() -> FigmaConfig:
    """Get or create Figma configuration."""
    global _config
    if _config is None:
        api_key = os.getenv("FIGMA_API_KEY")
        if not api_key:
            raise ValueError("FIGMA_API_KEY environment variable is required")
        _config = FigmaConfig(api_key=api_key)
    return _config


async def figma_request(
    method: str,
    endpoint: str,
    params: Optional[dict] = None,
    json_data: Optional[dict] = None,
    api_version: str = "v1"
) -> dict:
    """Make a request to Figma API.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint (e.g., /files/{file_key})
        params: Query parameters
        json_data: JSON body for POST/PUT requests
        api_version: API version (v1 or v2)
    
    Returns:
        Response JSON as dict
    """
    config = get_config()
    base_url = FIGMA_API_V2 if api_version == "v2" else FIGMA_API_BASE
    url = f"{base_url}{endpoint}"
    
    async with httpx.AsyncClient(timeout=config.timeout) as client:
        response = await client.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers={"X-Figma-Token": config.api_key}
        )
        
        if response.status_code >= 400:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
        
        return response.json()


# Convenience methods
async def figma_get(endpoint: str, params: Optional[dict] = None, api_version: str = "v1") -> dict:
    """GET request to Figma API."""
    return await figma_request("GET", endpoint, params=params, api_version=api_version)


async def figma_post(endpoint: str, json_data: dict, api_version: str = "v1") -> dict:
    """POST request to Figma API."""
    return await figma_request("POST", endpoint, json_data=json_data, api_version=api_version)


async def figma_put(endpoint: str, json_data: dict, api_version: str = "v1") -> dict:
    """PUT request to Figma API."""
    return await figma_request("PUT", endpoint, json_data=json_data, api_version=api_version)


async def figma_delete(endpoint: str, api_version: str = "v1") -> dict:
    """DELETE request to Figma API."""
    return await figma_request("DELETE", endpoint, api_version=api_version)
