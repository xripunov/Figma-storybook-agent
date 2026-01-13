"""Figma tools for the Design System Agent.

READ-ONLY tools for exploring Figma design system.
"""
import httpx
import os
from typing import Optional
from dataclasses import dataclass

FIGMA_API_BASE = "https://api.figma.com/v1"


@dataclass
class FigmaConfig:
    """Figma configuration."""
    api_key: str
    team_id: str = "1402973250736207902"
    project_id: str = "298335754"


def get_config() -> FigmaConfig:
    """Get Figma config from environment."""
    api_key = os.getenv("FIGMA_API_KEY")
    if not api_key:
        raise ValueError("FIGMA_API_KEY not set")
    return FigmaConfig(api_key=api_key)


async def list_design_system_files() -> list[dict]:
    """List all files in the design system project."""
    config = get_config()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{FIGMA_API_BASE}/projects/{config.project_id}/files",
            headers={"X-Figma-Token": config.api_key}
        )
        resp.raise_for_status()
        return resp.json().get("files", [])


async def list_components(file_key: str) -> list[dict]:
    """List all components in a Figma file."""
    config = get_config()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{FIGMA_API_BASE}/files/{file_key}/components",
            headers={"X-Figma-Token": config.api_key}
        )
        resp.raise_for_status()
        return resp.json().get("meta", {}).get("components", [])


def _extract_text_from_node(node: dict, texts: list[str], depth: int = 0):
    """Recursively extract text from Figma node tree."""
    # Skip if too deep (avoid infinite recursion)
    if depth > 20:
        return
    
    # If this is a text node, extract its content
    if node.get("type") == "TEXT":
        chars = node.get("characters", "").strip()
        if chars:
            texts.append(chars)
    
    # Recurse into children
    for child in node.get("children", []):
        _extract_text_from_node(child, texts, depth + 1)


async def get_component_guide(file_key: str, component_name: str) -> Optional[str]:
    """Get the documentation/guide for a component.
    
    Looks for a frame named '{component_name} / Guide' and extracts all text from it.
    """
    config = get_config()
    
    # Build the guide frame name pattern
    guide_name = f"{component_name} / Guide"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Get the file structure (this can be slow for large files)
        # We use depth=3 to limit how deep we fetch
        resp = await client.get(
            f"{FIGMA_API_BASE}/files/{file_key}",
            params={"depth": 2},  # Get top-level structure first
            headers={"X-Figma-Token": config.api_key}
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Find the guide frame node ID
        guide_node_id = None
        
        def find_guide_frame(node: dict):
            nonlocal guide_node_id
            name = node.get("name", "")
            if name.lower() == guide_name.lower():
                guide_node_id = node.get("id")
                return True
            for child in node.get("children", []):
                if find_guide_frame(child):
                    return True
            return False
        
        # Search in the document
        document = data.get("document", {})
        find_guide_frame(document)
        
        if not guide_node_id:
            return None
        
        # Now fetch the specific node with full depth
        resp = await client.get(
            f"{FIGMA_API_BASE}/files/{file_key}/nodes",
            params={"ids": guide_node_id},
            headers={"X-Figma-Token": config.api_key}
        )
        resp.raise_for_status()
        nodes_data = resp.json()
        
        # Extract text from the guide frame
        node_data = nodes_data.get("nodes", {}).get(guide_node_id, {}).get("document", {})
        
        texts = []
        _extract_text_from_node(node_data, texts)
        
        if texts:
            return "\n\n".join(texts)
        
        return None


async def get_component_info(file_key: str, component_name: str) -> Optional[dict]:
    """Get detailed info about a specific component."""
    components = await list_components(file_key)
    
    # Find matching component (case-insensitive partial match)
    name_lower = component_name.lower()
    matches = [c for c in components if name_lower in c["name"].lower()]
    
    if not matches:
        return None
    
    # Return best match (shortest name that matches)
    return min(matches, key=lambda c: len(c["name"]))


async def search_components(query: str, file_key: Optional[str] = None) -> list[dict]:
    """Search for components across the design system."""
    # Default to UI Kit if no file specified
    if not file_key:
        file_key = "fRi3HAgxLDuHW4MJQPf5r3"  # Bank 02 UI Kit
    
    components = await list_components(file_key)
    
    # Search by name
    query_lower = query.lower()
    matches = [c for c in components if query_lower in c["name"].lower()]
    
    # Also search in containing frame name
    matches.extend([
        c for c in components 
        if query_lower in c.get("containing_frame", {}).get("name", "").lower()
        and c not in matches
    ])
    
    return matches[:20]  # Limit results


async def get_component_variants(file_key: str, component_name: str) -> list[dict]:
    """Get all variants of a component (e.g., all Button variants).
    
    Searches by containing_frame name, which is the parent frame 
    that groups all variants of a component in Figma.
    """
    components = await list_components(file_key)
    
    name_lower = component_name.lower().strip()
    
    # Strategy 1: Find components where containing_frame matches exactly
    frame_matches = [
        c for c in components 
        if c.get("containing_frame", {}).get("name", "").lower().strip() == name_lower
    ]
    
    if frame_matches:
        return frame_matches
    
    # Strategy 2: Find components where containing_frame starts with the name
    frame_starts_with = [
        c for c in components 
        if c.get("containing_frame", {}).get("name", "").lower().startswith(name_lower)
    ]
    
    if frame_starts_with:
        # Group by frame and return the one with most variants
        frames = {}
        for c in frame_starts_with:
            frame = c.get("containing_frame", {}).get("name", "")
            if frame not in frames:
                frames[frame] = []
            frames[frame].append(c)
        
        # Return the frame with most components (most likely the main component)
        best_frame = max(frames.keys(), key=lambda f: len(frames[f]))
        return frames[best_frame]
    
    # Strategy 3: Fallback to component name search (but prefer exact matches)
    exact_name_matches = [
        c for c in components 
        if c["name"].lower().strip() == name_lower
    ]
    
    if exact_name_matches:
        # Get all variants from the same frame as the exact match
        frame_name = exact_name_matches[0].get("containing_frame", {}).get("name", "")
        if frame_name:
            return [c for c in components if c.get("containing_frame", {}).get("name") == frame_name]
        return exact_name_matches
    
    # Strategy 4: Partial name match (original behavior)
    partial_matches = [c for c in components if name_lower in c["name"].lower()]
    
    if partial_matches:
        frame_name = partial_matches[0].get("containing_frame", {}).get("name", "")
        if frame_name:
            return [c for c in components if c.get("containing_frame", {}).get("name") == frame_name]
    
    return partial_matches


    return partial_matches


async def get_node_image(file_key: str, node_id: str) -> Optional[str]:
    """Get the image URL for a specific node."""
    config = get_config()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{FIGMA_API_BASE}/images/{file_key}",
            params={"ids": node_id, "format": "png", "scale": 2},
            headers={"X-Figma-Token": config.api_key}
        )
        if resp.status_code != 200:
            return None
            
        data = resp.json()
        images = data.get("images", {})
        return images.get(node_id)


async def get_node_data(file_key: str, node_id: str) -> Optional[dict]:
    """Get full data for a specific node to inspect properties."""
    config = get_config()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{FIGMA_API_BASE}/files/{file_key}/nodes",
            params={"ids": node_id},
            headers={"X-Figma-Token": config.api_key}
        )
        if resp.status_code != 200:
            return None
        return resp.json().get("nodes", {}).get(node_id, {}).get("document")


async def get_file_variables(file_key: str) -> dict:
    """Get map of variable ID -> Name for the file."""
    config = get_config()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{FIGMA_API_BASE}/files/{file_key}/variables/local",
            headers={"X-Figma-Token": config.api_key}
        )
        if resp.status_code != 200:
            return {}
        
        # Build map id -> values
        # Response structure: meta: { variables: [ { id, name, ... } ] }
        variables = resp.json().get("meta", {}).get("variables", [])
        return {v["id"]: v["name"] for v in variables}


async def get_file_styles(file_key: str) -> dict:
    """Get map of style ID -> Name for the file."""
    config = get_config()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{FIGMA_API_BASE}/files/{file_key}/styles",
            headers={"X-Figma-Token": config.api_key}
        )
        if resp.status_code != 200:
            return {}
        
        # Build map id -> values
        # Response structure: meta: { styles: [ { node_id, style_type, name, description, key } ] }
        # NOTE: endpoint returns styles metadata. But node references style by 'node_id' or 'key'?
        # Node uses 'styles' map: { "fill": style_id }. documentation says style_id corresponds to what?
        # Usually it matches the style's node_id or key? Let's assume node_id based on common usage.
        styles = resp.json().get("meta", {}).get("styles", [])
        # Provide mapping for both ID and Key just in case
        mapping = {s["node_id"]: s["name"] for s in styles}
        # Also map key just in case some refs use keys
        mapping.update({s["key"]: s["name"] for s in styles}) 
        return mapping


def _extract_tokens_recursive(node: dict, var_map: dict, style_map: dict, tokens: list, path: list):
    """Recursively find boundVariables and styles."""
    node_name = node.get("name", "Unknown")
    curr_path =  f"{path[-1]} > {node_name}" if path else node_name
    
    # 1. Variables
    bound_vars = node.get("boundVariables", {})
    if bound_vars:
        for prop, val in bound_vars.items():
            if isinstance(val, dict) and "id" in val:
                var_name = var_map.get(val["id"])
                if var_name:
                    tokens.append(f"{curr_path} ({prop}): 🔹 {var_name}")
            # Fills/Strokes are lists in boundVariables sometimes?
            # Figma API: 'fills' in boundVariables is list of variable aliases matching fills array index
            elif isinstance(val, list):
                 for i, alias in enumerate(val):
                     if isinstance(alias, dict) and "id" in alias:
                         var_name = var_map.get(alias["id"])
                         if var_name:
                             tokens.append(f"{curr_path} ({prop}[{i}]): 🔹 {var_name}")

    # 2. Styles
    styles = node.get("styles", {})
    if styles:
        for prop, style_id in styles.items():
            style_name = style_map.get(style_id)
            if style_name:
                 tokens.append(f"{curr_path} ({prop}): 🔸 {style_name}")
                 
    # Recurse
    # Limit depth to avoid massive dumps?
    if len(path) < 5: 
        for child in node.get("children", []):
            _extract_tokens_recursive(child, var_map, style_map, tokens, path + [node_name])


async def get_component_details(file_key: str, query: str) -> dict:
    """Get full details about a component: search result, variants, and rule guide.
    
    This is a "super tool" that combines search, variants, guide, and property inspection.
    """
    # 1. Search to find precise name/frame
    search_results = await search_components(query, file_key)
    
    if not search_results:
        return {"error": f"Компоненты по запросу '{query}' не найдены"}
    
    # 2. Pick the best match to query for details
    best_match = search_results[0]
    target_name = best_match.get("name")
    target_id = best_match.get("node_id")
    
    # ... (Search logic matches query to frame name) ...
    for res in search_results:
        frame = res.get("containing_frame", {}).get("name", "")
        if query.lower() in frame.lower():
            target_name = frame
            target_id = res.get("node_id")
            break
            
    if not target_name:
        target_name = query

    # 3. Parallel fetch: Variants, Guide, Image, Node Props
    variants = await get_component_variants(file_key, target_name)
    guide = await get_component_guide(file_key, target_name)
    
    image_url = None
    node_props = {}
    
    if target_id:
        image_url = await get_node_image(file_key, target_id)
        node_data = await get_node_data(file_key, target_id)
        
        if node_data:
            # Fetch maps
            var_map = await get_file_variables(file_key)
            style_map = await get_file_styles(file_key)
            
            resolved_props = []
            _extract_tokens_recursive(node_data, var_map, style_map, resolved_props, [])
            
            # Deduplicate and sort
            resolved_props = sorted(list(set(resolved_props)))
            
            if resolved_props:
                node_props["tokens"] = resolved_props

    
    # Also try to get guide for the query itself if target_name didn't work
    if not guide and target_name.lower() != query.lower():
        guide = await get_component_guide(file_key, query)

    return {
        "found_name": target_name,
        "search_matches": [
            f"{c['name']} (Frame: {c.get('containing_frame', {}).get('name', '')})" 
            for c in search_results[:5]
        ],
        "variants": [v['name'] for v in variants[:20]],
        "variants_count": len(variants),
        "guide": guide,
        "image_url": image_url,
        "props": node_props
    }


def parse_figma_url(url: str) -> dict:
    """Extract file_key and node_id from a Figma URL."""
    # Example: https://www.figma.com/file/fRi3HAgxLDuHW4MJQPf5r3/Bank-02-UI-Kit?type=design&node-id=15635%3A61453&mode=design&t=...
    # Or: https://www.figma.com/design/fRi3HAgxLDuHW4MJQPf5r3/Bank-02-UI-Kit?node-id=15635-61453...
    import re
    from urllib.parse import unquote
    
    # Extract file key (alphanumeric, 22 chars usually)
    # Matches /file/KEY or /design/KEY
    key_match = re.search(r"/(?:file|design)/([a-zA-Z0-9]{22,})", url)
    if not key_match:
        return {"error": "Не удалось найти ID файла в ссылке"}
    
    file_key = key_match.group(1)
    
    # Extract node_id
    # Usually in query param ?node-id=123%3A456
    node_match = re.search(r"node-id=([^&]+)", url)
    node_id = None
    if node_match:
        # Figma URLs encode ':' as '%3A', but sometimes it's '-' in new URLs?
        # Usually API expects "123:456". URL might have "123%3A456" or "123-456"
        raw_id = unquote(node_match.group(1))
        # Replace dash with colon if it looks like "123-456" and strictly digits? 
        # Actually Figma sometimes uses dashes in URLs for node IDs now.
        # But API expects regular node IDs. Let's assume unquote is enough for %3A.
        # If it is '123-456' format (new one), we might need to convert to '123:456'.
        # However, let's trust that the ID provided works, or try to normalize.
        node_id = raw_id.replace("-", ":") if ":" not in raw_id and "-" in raw_id else raw_id
    
    return {
        "file_key": file_key,
        "node_id": node_id
    }


async def find_component_usages(file_key: str, component_node_id: str) -> dict:
    """Scan a file to find usages (instances) of a component."""
    config = get_config()
    
    # Fetch the WHOLE file (can be heavy!)
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.get(
            f"{FIGMA_API_BASE}/files/{file_key}",
            headers={"X-Figma-Token": config.api_key}
        )
        if resp.status_code != 200:
            return {"error": f"Ошибка загрузки файла: {resp.status_code}"}
        
        data = resp.json()
        document = data.get("document", {})
        
        usages = []
        
        def _scan(node, path):
            if node.get("type") == "INSTANCE" and node.get("componentId") == component_node_id:
                # Found usage!
                # Context is the frame name (path[-1] usually)
                context = path[-1] if path else "Root"
                usages.append({
                    "name": node.get("name"),
                    "id": node.get("id"),
                    "context": context
                })
            
            # Recurse
            node_name = node.get("name", "Unknown")
            # Don't add 'Group' or hidden frames to path logic if we want "Screen Name"?
            # Let's just track full path
            new_path = path
            if node.get("type") in ["FRAME", "SECTION", "CANVAS"]:
                 new_path = path + [node_name]
                 
            for child in node.get("children", []):
                _scan(child, new_path)
                
        _scan(document, [])
        
        # Group stats
        grouped = {}
        for u in usages:
            ctx = u["context"]
            if ctx not in grouped:
                grouped[ctx] = 0
            grouped[ctx] += 1
            
        return {
            "total_count": len(usages),
            "contexts": grouped,
            "usage_samples": usages[:5] 
        }


        return {
            "total_count": len(usages),
            "contexts": grouped,
            "usage_samples": usages[:5] 
        }


async def analyze_figma_url(url: str) -> dict:
    """Analyze a Figma URL: identify component, get details and usage stats."""
    # 1. Parse URL
    parsed = parse_figma_url(url)
    if "error" in parsed:
        return parsed
        
    file_key = parsed["file_key"]
    node_id = parsed["node_id"]
    
    # 2. Inspect the node to understand what it is
    # We use cached/helper to get node data
    node_data = await get_node_data(file_key, node_id)
    if not node_data:
        # Try to continue if node lookup fails? No, critical.
        return {"error": "Не удалось загрузить данные ноды по ссылке (возможно, неверный ID)"}
    
    # Resolve target ID (Master Component)
    target_id = node_id
    target_name = node_data.get("name", "Unknown")
    node_type = node_data.get("type")
    
    # If instance, switch to master component
    if node_type == "INSTANCE":
        comp_id = node_data.get("componentId")
        if comp_id:
            target_id = comp_id
            # NOTE: We don't know the master component Name yet.
            # We can try to fetch the master component node to get its name?
            # Or just use the instance name (which usually matches).
            # Let's try to fetch master node data to be precise about name
            master_data = await get_node_data(file_key, target_id)
            if master_data:
                target_name = master_data.get("name", target_name)
    
    # 3. Get Usages (Precise search by ID)
    # We scan the SAME file where the link is pointing to
    # usages = await find_component_usages(file_key, target_id)
    usages = None # Disabled by user request
    
    # 4. Get Details (Search by Name)
    # This gives us Guide, Variants, etc.
    details = await get_component_details(file_key, target_name)
    
    return {
        "analysis_type": "Instance Link" if node_type == "INSTANCE" else "Component Link",
        "target_name": target_name,
        "target_id": target_id,
        "location_file": file_key,
        "usages": usages,
        "details": details
    }


# File key mapping for convenience
FILE_KEYS = {
    "foundation": "4ELwCVLtFVJEOvTWTMgzoc",
    "ui-kit": "fRi3HAgxLDuHW4MJQPf5r3",
    "organisms": "JbfXQWGV0BhKVA1RLwn5V9",
    "content": "orK6ik3Y3jz9Kdae26Xd4D",
    "local-components": "FwE8tG9F5b1tzOCiwEia1b",
    "icons": "YcLaNNYi7TSdzgidXCNVmv",
    "logos": "dhbvT9HFmKPsPjFP5dVBjl",
    "cards": "cIVBzK29WPCdAcxu51JKD8",
    "graphics": "gsYPhh1TIxL59UmGR1281c",
    "illustrations": "mgdGa7yTGTBDFpcjfnbeVF",
    "pictograms": "p6eSfKFu7XHBWi5P6u62C5",
    "infrastructure": "D4nh89Loek8sSkNlrtqM9a",
    "deprecated": "HOABEIUXJL5CvA2yHNEN5Q",
    "design-update": "ZSaVtJHZgv30Zu1s21O6Ib",
}


def get_file_key(name: str) -> str:
    """Get file key by friendly name."""
    return FILE_KEYS.get(name.lower(), name)
