"""Figma API Client.

Comprehensive Figma API implementation with all public endpoints.
"""

# Base client
from .client import (
    figma_request,
    figma_get,
    figma_post,
    figma_put,
    figma_delete,
    get_config,
    FigmaConfig,
)

# File methods
from .files import (
    figma_get_file,
    figma_get_file_nodes,
    figma_get_images,
    figma_get_image_fills,
    figma_get_file_versions,
)

# Comment methods
from .comments import (
    figma_get_comments,
    figma_post_comment,
    figma_delete_comment,
    figma_get_comment_reactions,
    figma_post_comment_reaction,
    figma_delete_comment_reaction,
)

# Team and project methods
from .teams import (
    figma_get_team_projects,
    figma_get_project_files,
)

# Component methods
from .components import (
    figma_get_team_components,
    figma_get_file_components,
    figma_get_component,
    figma_get_team_component_sets,
    figma_get_file_component_sets,
    figma_get_component_set,
)

# Style methods
from .styles import (
    figma_get_team_styles,
    figma_get_file_styles,
    figma_get_style,
)

# Analytics methods
from .analytics import (
    figma_get_library_analytics_component_usages,
    figma_get_library_analytics_style_usages,
    figma_get_library_analytics_variable_usages,
)


__all__ = [
    # Client
    "figma_request",
    "figma_get",
    "figma_post",
    "figma_put",
    "figma_delete",
    "get_config",
    "FigmaConfig",
    # Files
    "figma_get_file",
    "figma_get_file_nodes",
    "figma_get_images",
    "figma_get_image_fills",
    "figma_get_file_versions",
    # Comments
    "figma_get_comments",
    "figma_post_comment",
    "figma_delete_comment",
    "figma_get_comment_reactions",
    "figma_post_comment_reaction",
    "figma_delete_comment_reaction",
    # Teams
    "figma_get_team_projects",
    "figma_get_project_files",
    # Components
    "figma_get_team_components",
    "figma_get_file_components",
    "figma_get_component",
    "figma_get_team_component_sets",
    "figma_get_file_component_sets",
    "figma_get_component_set",
    # Styles
    "figma_get_team_styles",
    "figma_get_file_styles",
    "figma_get_style",
    # Analytics
    "figma_get_library_analytics_component_usages",
    "figma_get_library_analytics_style_usages",
    "figma_get_library_analytics_variable_usages",
]
