"""Figma API - Team and Project Methods.

Methods for working with teams and projects.
"""
from .client import figma_get


async def figma_get_team_projects(team_id: str) -> dict:
    """Get projects in a team.
    
    Args:
        team_id: Team ID
    
    Returns:
        List of projects
    """
    return await figma_get(f"/teams/{team_id}/projects")


async def figma_get_project_files(
    project_id: str,
    branch_data: bool = False
) -> dict:
    """Get files in a project.
    
    Args:
        project_id: Project ID
        branch_data: Include branch metadata
    
    Returns:
        List of files in project
    """
    params = {"branch_data": branch_data} if branch_data else None
    return await figma_get(f"/projects/{project_id}/files", params=params)
