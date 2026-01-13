"""Figma API - Comment Methods.

Methods for working with comments and reactions.
"""
from typing import Optional, List
from .client import figma_get, figma_post, figma_delete


async def figma_get_comments(file_key: str, as_md: bool = False) -> dict:
    """Get comments in a Figma file.
    
    Args:
        file_key: The file key
        as_md: Return comments as markdown
    
    Returns:
        List of comments
    """
    params = {"as_md": as_md} if as_md else None
    return await figma_get(f"/files/{file_key}/comments", params=params)


async def figma_post_comment(
    file_key: str,
    message: str,
    client_meta: Optional[dict] = None,
    comment_id: Optional[str] = None
) -> dict:
    """Add a comment to a Figma file.
    
    Args:
        file_key: The file key
        message: Comment text
        client_meta: Position metadata (x, y, node_id, node_offset)
        comment_id: Parent comment ID for replies
    
    Returns:
        Created comment data
    """
    data = {"message": message}
    if client_meta:
        data["client_meta"] = client_meta
    if comment_id:
        data["comment_id"] = comment_id
    
    return await figma_post(f"/files/{file_key}/comments", json_data=data)


async def figma_delete_comment(file_key: str, comment_id: str) -> dict:
    """Delete a comment from a Figma file.
    
    Args:
        file_key: The file key
        comment_id: Comment ID to delete
    
    Returns:
        Empty dict on success
    """
    return await figma_delete(f"/files/{file_key}/comments/{comment_id}")


async def figma_get_comment_reactions(
    file_key: str,
    comment_id: str,
    cursor: Optional[str] = None
) -> dict:
    """Get reactions for a comment.
    
    Args:
        file_key: The file key
        comment_id: Comment ID
        cursor: Pagination cursor
    
    Returns:
        List of reactions
    """
    params = {"cursor": cursor} if cursor else None
    return await figma_get(f"/files/{file_key}/comments/{comment_id}/reactions", params=params)


async def figma_post_comment_reaction(
    file_key: str,
    comment_id: str,
    emoji: str
) -> dict:
    """Add a reaction to a comment.
    
    Args:
        file_key: The file key
        comment_id: Comment ID
        emoji: Emoji unicode or shortcode
    
    Returns:
        Reaction data
    """
    return await figma_post(
        f"/files/{file_key}/comments/{comment_id}/reactions",
        json_data={"emoji": emoji}
    )


async def figma_delete_comment_reaction(
    file_key: str,
    comment_id: str,
    emoji: str
) -> dict:
    """Delete a reaction from a comment.
    
    Args:
        file_key: The file key
        comment_id: Comment ID
        emoji: Emoji to remove
    
    Returns:
        Empty dict on success
    """
    # Note: Figma API uses emoji as query param for deletion
    return await figma_delete(f"/files/{file_key}/comments/{comment_id}/reactions?emoji={emoji}")
