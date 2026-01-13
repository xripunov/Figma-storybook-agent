"""Figma REST API client for project/team file listing.

This is READ-ONLY - no modifications to Figma files.
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

FIGMA_API_BASE = "https://api.figma.com/v1"


async def get_project_files(project_id: str) -> dict:
    """Get all files in a Figma project (READ-ONLY)."""
    api_key = os.getenv("FIGMA_API_KEY")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{FIGMA_API_BASE}/projects/{project_id}/files",
            headers={"X-Figma-Token": api_key}
        )
        response.raise_for_status()
        return response.json()


async def get_team_projects(team_id: str) -> dict:
    """Get all projects in a Figma team (READ-ONLY)."""
    api_key = os.getenv("FIGMA_API_KEY")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{FIGMA_API_BASE}/teams/{team_id}/projects",
            headers={"X-Figma-Token": api_key}
        )
        response.raise_for_status()
        return response.json()


async def main():
    """List files from the design system project."""
    team_id = "1402973250736207902"
    project_id = "298335754"
    
    print("🔒 READ-ONLY mode - no changes will be made to Figma\n")
    
    # Get team projects
    print(f"📁 Team {team_id} projects:")
    print("-" * 50)
    try:
        team_data = await get_team_projects(team_id)
        for project in team_data.get("projects", []):
            marker = "→" if str(project["id"]) == project_id else " "
            print(f"  {marker} [{project['id']}] {project['name']}")
    except httpx.HTTPStatusError as e:
        print(f"  ❌ Error: {e.response.status_code} - {e.response.text[:100]}")
    
    print()
    
    # Get project files
    print(f"📄 Project {project_id} files:")
    print("-" * 50)
    try:
        project_data = await get_project_files(project_id)
        for file in project_data.get("files", []):
            print(f"  📄 {file['name']}")
            print(f"     Key: {file['key']}")
            print(f"     URL: https://www.figma.com/file/{file['key']}")
            print(f"     Modified: {file.get('last_modified', 'N/A')}")
            print()
    except httpx.HTTPStatusError as e:
        print(f"  ❌ Error: {e.response.status_code} - {e.response.text[:100]}")


if __name__ == "__main__":
    asyncio.run(main())
