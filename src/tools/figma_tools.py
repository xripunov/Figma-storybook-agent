"""Figma tools for the Design System Agent.

READ-ONLY tools for exploring Figma design system.
"""
import httpx
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

FIGMA_API_BASE = "https://api.figma.com/v1"

# File keys from environment
FIGMA_UI_KIT_KEY = os.getenv("FIGMA_UI_KIT_FILE_KEY", "fRi3HAgxLDuHW4MJQPf5r3")
FIGMA_PATTERNS_KEY = os.getenv("FIGMA_PATTERNS_FILE_KEY", "CBS0qZz6lqoU2Mh3StNwV7")


def generate_figma_link(file_key: str, node_id: str) -> str:
    """Generate a direct link to a Figma frame."""
    # Convert node_id from 123:456 to 123-456 for URL
    url_node_id = node_id.replace(":", "-") if node_id else ""
    return f"https://www.figma.com/design/{file_key}?node-id={url_node_id}"


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
        
        # Normalize for comparison: remove spaces, lowercase
        target_clean = component_name.lower().replace(" ", "")
        
        def find_guide_frame(node: dict):
            nonlocal guide_node_id
            name = node.get("name", "")
            name_clean = name.lower().replace(" ", "")
            
            # Check for "Guide" and Component Name
            # Matches: "Link Cell / Guide", "LinkCell / Guide", "Link Cell Guide"
            if "guide" in name.lower() and target_clean in name_clean:
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
    """Search for components across the design system.
    
    Results are ranked: exact match > starts_with > contains
    """
    # Default to UI Kit if no file specified
    if not file_key:
        file_key = "fRi3HAgxLDuHW4MJQPf5r3"  # Bank 02 UI Kit
    
    components = await list_components(file_key)
    
    query_lower = query.lower().strip()
    
    # Tier 1: Exact match on containing_frame name (best - this is the component group)
    exact_frame = [
        c for c in components 
        if c.get("containing_frame", {}).get("name", "").lower().strip() == query_lower
    ]
    
    # Tier 2: Exact match on component name
    exact_name = [
        c for c in components 
        if c["name"].lower().strip() == query_lower
        and c not in exact_frame
    ]
    
    # Tier 3: Frame starts with query
    starts_frame = [
        c for c in components 
        if c.get("containing_frame", {}).get("name", "").lower().startswith(query_lower)
        and c not in exact_frame and c not in exact_name
    ]
    
    # Tier 4: Name starts with query
    starts_name = [
        c for c in components 
        if c["name"].lower().startswith(query_lower)
        and c not in exact_frame and c not in exact_name and c not in starts_frame
    ]
    
    # Tier 5: Fuzzy match (ignore spaces)
    # Helper to clean string for fuzzy comparison
    def clean(s): return s.lower().replace(" ", "").replace("-", "").replace("_", "")
    query_clean = clean(query)
    
    fuzzy_matches = []
    seen = set(c["node_id"] for c in exact_frame + exact_name + starts_frame + starts_name)
    
    if len(query_clean) > 3: # Only fuzzy search if query has substance
        for c in components:
            if c["node_id"] in seen:
                continue
                
            frame = c.get("containing_frame", {}).get("name", "")
            name = c["name"]
            
            # Check frame name fuzzy
            if query_clean in clean(frame):
                fuzzy_matches.append(c)
                seen.add(c["node_id"])
                continue
                
            # Check component name fuzzy
            if query_clean in clean(name):
                fuzzy_matches.append(c)
                seen.add(c["node_id"])

    # Tier 6: Standard Contains match (fallback)
    contains = [
        c for c in components 
        if (query_lower in c["name"].lower() or 
            query_lower in c.get("containing_frame", {}).get("name", "").lower())
        and c["node_id"] not in seen
    ]
    
    # Combine in priority order
    results = exact_frame + exact_name + starts_frame + starts_name + fuzzy_matches + contains
    
    return results[:20]  # Limit results


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


def _rgb_to_hex(r: float, g: float, b: float) -> str:
    """Convert RGB (0-1 range) to HEX color."""
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def _extract_tokens_recursive(node: dict, var_map: dict, style_map: dict, tokens: list, raw_props: list, path: list):
    """Recursively find boundVariables, styles, and raw properties."""
    node_name = node.get("name", "Unknown")
    node_type = node.get("type", "")
    curr_path = f"{path[-1]} > {node_name}" if path else node_name
    
    # Skip hidden nodes
    if not node.get("visible", True):
        return
    
    # 1. Bound Variables (Tokens)
    bound_vars = node.get("boundVariables", {})
    if bound_vars:
        for prop, val in bound_vars.items():
            if isinstance(val, dict) and "id" in val:
                var_name = var_map.get(val["id"])
                if var_name:
                    tokens.append(f"{curr_path} ({prop}): 🔹 {var_name}")
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
    
    # 3. Raw Properties (when no tokens/styles are bound)
    # Only extract from top-level important nodes to avoid noise
    if len(path) < 3:  # Limit depth for raw props
        # Fills (background colors)
        fills = node.get("fills", [])
        for i, fill in enumerate(fills):
            if fill.get("type") == "SOLID" and fill.get("visible", True):
                color = fill.get("color", {})
                if color:
                    hex_color = _rgb_to_hex(color.get("r", 0), color.get("g", 0), color.get("b", 0))
                    opacity = fill.get("opacity", 1)
                    opacity_str = f" ({int(opacity*100)}%)" if opacity < 1 else ""
                    raw_props.append(f"{curr_path} (fill): 🎨 {hex_color}{opacity_str}")
        
        # Corner radius
        corner = node.get("cornerRadius")
        if corner and corner > 0:
            raw_props.append(f"{curr_path} (radius): 📐 {corner}px")
        
        # Strokes
        strokes = node.get("strokes", [])
        for stroke in strokes:
            if stroke.get("type") == "SOLID" and stroke.get("visible", True):
                color = stroke.get("color", {})
                if color:
                    hex_color = _rgb_to_hex(color.get("r", 0), color.get("g", 0), color.get("b", 0))
                    weight = node.get("strokeWeight", 1)
                    raw_props.append(f"{curr_path} (stroke): ✏️ {hex_color} ({weight}px)")
        
        # Text properties
        if node_type == "TEXT":
            font_name = node.get("style", {}).get("fontFamily") or node.get("fontName", {}).get("family")
            font_size = node.get("style", {}).get("fontSize") or node.get("fontSize")
            if font_name or font_size:
                raw_props.append(f"{curr_path} (text): 🔤 {font_name or ''} {font_size}px")
    
    # Recurse into children
    if len(path) < 5:
        for child in node.get("children", []):
            _extract_tokens_recursive(child, var_map, style_map, tokens, raw_props, path + [node_name])


async def get_component_details(file_key: str, query: str) -> dict:
    """Get full details about a component: search result, variants, and rule guide.
    
    This is a "super tool" that combines search, variants, guide, and property inspection.
    """
    import datetime
    def log(msg):
        with open("figma_debug.log", "a") as f:
            f.write(f"[{datetime.datetime.now()}] {msg}\n")

    log(f"--- START get_component_details: {query} ---")

    # 1. Search to find precise name/frame
    search_results = await search_components(query, file_key)
    log(f"Search results count: {len(search_results)}")
    
    if not search_results:
        log("No search results found.")
        return {"error": f"Компоненты по запросу '{query}' не найдены"}
    
    # 2. Pick the best match to query for details
    best_match = search_results[0]
    target_name = best_match.get("name")
    target_id = best_match.get("node_id")
    
    # Helper for fuzzy comparison
    def clean(s): return s.lower().replace(" ", "").replace("-", "").replace("_", "")
    query_clean = clean(query)
    
    # Try to find a Component Set (containing frame) that matches the query
    for res in search_results:
        frame_name = res.get("containing_frame", {}).get("name", "")
        frame_id = res.get("containing_frame", {}).get("nodeId")
        frame_clean = clean(frame_name)
        
        # Check if query matches the Frame name (fuzzy)
        if query_clean in frame_clean or frame_clean in query_clean:
            log(f"Found better target via fuzzy match: {frame_name} (was {target_name})")
            target_name = frame_name
            target_id = frame_id or res.get("node_id")
            break
            
    if not target_name:
        target_name = query

    # 3. Parallel fetch: Variants, Guide, Image, Node Props
    variants = await get_component_variants(file_key, target_name)
    guide = await get_component_guide(file_key, target_name)
    
    # Also try to get guide for the query itself if target_name didn't work
    if not guide and target_name.lower() != query.lower():
        guide = await get_component_guide(file_key, query)

    # 3.5 Extract properties from target node (Component Set)
    node_props = {}
    if target_id:
        node_data = await get_node_data(file_key, target_id)
        log(f"Got node_data for target_id {target_id}: {node_data is not None}")
        
        if node_data:
            # Extract component properties (for code generation)
            comp_props = node_data.get("componentPropertyDefinitions", {})
            if comp_props:
                node_props["definitions"] = comp_props
                
                # Create readable summary
                summary_lines = []
                for prop_name, prop_def in comp_props.items():
                    p_type = prop_def.get("type")
                    if p_type == "VARIANT":
                        opts = prop_def.get("variantOptions", [])
                        summary_lines.append(f"• {prop_name}: {', '.join(opts)}")
                    elif p_type == "BOOLEAN":
                        summary_lines.append(f"• {prop_name}: True/False")
                    elif p_type == "TEXT":
                        summary_lines.append(f"• {prop_name}: Text")
                
                node_props["summary"] = "\n".join(summary_lines)
                log(f"Extracted props summary with {len(summary_lines)} lines")

    # 4. Find the best "Cover" image (Top-level frame named same as component)
    image_url = None
    page_id = best_match.get("containing_frame", {}).get("pageId")
    
    log(f"Trying to find cover image. PageID: {page_id}")

    
    if page_id:
        # Try to find a top-level frame that exactly matches the component name
        cover_node_id = await find_top_level_frame(file_key, page_id, target_name)
        log(f"find_top_level_frame result: {cover_node_id}")
        
        if cover_node_id:
            image_url = await get_node_image(file_key, cover_node_id)
            log(f"Got image URL from cover: {image_url is not None}")
            
    # Fallback to Component Set or direct ID if no cover found
    if not image_url and target_id:
        log(f"Fallback to target_id: {target_id}")
        image_url = await get_node_image(file_key, target_id)
        
    # Log properties count
    log(f"Props extracted: definitions={len(node_props.get('definitions', {}))}, summary_len={len(node_props.get('summary', ''))}")
        
    # 5. Build Figma link
    figma_link = None
    if target_id:
        figma_link = generate_figma_link(file_key, target_id)
        
    return {
        "found_name": target_name,
        "search_matches": [
            f"{c['name']} (Frame: {c.get('containing_frame', {}).get('name', '')})" 
            for c in search_results[:5]
        ],
        "variants": [], 
        "variants_count": len(variants),
        "guide": guide,
        "image_url": image_url,
        "figma_link": figma_link,
        "props": node_props,
        "_debug_info": {
            "page_id": page_id,
            "target_id": target_id,
            "best_match_frame": best_match.get("containing_frame"),
            "image_found_via": "cover" if page_id and image_url and image_url != (await get_node_image(file_key, target_id) if target_id else None) else "target_id",
            "props_count": len(node_props.get("definitions", {}))
        }
    }

async def find_top_level_frame(file_key: str, page_id: str, name: str) -> Optional[str]:
    """Find a top-level frame (or inside Section) that matches the name."""
    import datetime
    def log(msg):
        with open("figma_debug.log", "a") as f:
            f.write(f"[{datetime.datetime.now()}] [find_top_level] {msg}\n")

    config = get_config()
    target_clean = name.lower().replace(" ", "")
    log(f"Searching for '{name}' (clean: {target_clean}) in page {page_id}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Depth 3 covers Page -> Section -> Frame
        resp = await client.get(
            f"{FIGMA_API_BASE}/files/{file_key}/nodes",
            params={"ids": page_id, "depth": 3},
            headers={"X-Figma-Token": config.api_key}
        )
        if resp.status_code != 200:
            log(f"Error fetching page nodes: {resp.status_code}")
            return None
            
        data = resp.json()
        page_node = data.get("nodes", {}).get(page_id, {}).get("document", {})
        
        found_id = None
        
        def search_recursive(node, depth=0):
            nonlocal found_id
            if found_id: return
            
            node_name = node.get("name", "")
            node_type = node.get("type", "")
            clean_name = node_name.lower().replace(" ", "")
            node_id = node.get("id")
            
            # log(f"[{depth}] Checking {node_type}: {node_name} ({node_id})")
            
            # Check match (Frame, Component, Component Set)
            if clean_name == target_clean and node_type in ["FRAME", "COMPONENT_SET", "COMPONENT", "SECTION"]:
                log(f"FOUND MATCH! {node_name} ({node_id})")
                found_id = node["id"]
                return

            if "children" in node:
                for child in node["children"]:
                    search_recursive(child, depth + 1)
                    
        search_recursive(page_node)
        
        if not found_id:
             log("No match found after recursive search.")
             
        return found_id


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
    "ui-kit": FIGMA_UI_KIT_KEY,
    "patterns": FIGMA_PATTERNS_KEY,
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


# =============================================================================
# PATTERNS TOOLS
# =============================================================================

async def list_patterns() -> list[dict]:
    """List all patterns (pages) from the Bank Patterns file.
    
    Each page in the Patterns file is a separate pattern topic.
    Returns list of pages with their IDs.
    """
    config = get_config()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{FIGMA_API_BASE}/files/{FIGMA_PATTERNS_KEY}",
            params={"depth": 1},  # Just get pages
            headers={"X-Figma-Token": config.api_key}
        )
        resp.raise_for_status()
        data = resp.json()
        
        pages = []
        document = data.get("document", {})
        for child in document.get("children", []):
            if child.get("type") == "CANVAS":
                pages.append({
                    "name": child.get("name"),
                    "id": child.get("id"),
                    "type": "pattern"
                })
        
        return pages


async def search_patterns(query: str) -> list[dict]:
    """Search for patterns by name.
    
    Searches across all pattern pages in the Bank Patterns file.
    Results are ranked: exact match > starts_with > contains.
    """
    patterns = await list_patterns()
    
    query_lower = query.lower().strip()
    
    # Tier 1: Exact match
    exact = [p for p in patterns if p["name"].lower().strip() == query_lower]
    
    # Tier 2: Starts with
    starts = [p for p in patterns 
              if p["name"].lower().startswith(query_lower) and p not in exact]
    
    # Tier 3: Contains
    contains = [p for p in patterns 
                if query_lower in p["name"].lower() 
                and p not in exact and p not in starts]
    
    return exact + starts + contains


async def get_pattern_info(pattern_name: str) -> dict:
    """Get detailed info about a pattern.
    
    Patterns are pages in the Bank Patterns file.
    This function fetches the guide (if exists as a frame named like the page),
    renders an image, and returns with a Figma link.
    """
    config = get_config()
    
    # 1. Find the pattern page
    patterns = await search_patterns(pattern_name)
    
    if not patterns:
        return {"error": f"Паттерн '{pattern_name}' не найден"}
    
    best_match = patterns[0]
    page_id = best_match["id"]
    page_name = best_match["name"]
    
    # 2. Get page content to find guide frame
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.get(
            f"{FIGMA_API_BASE}/files/{FIGMA_PATTERNS_KEY}/nodes",
            params={"ids": page_id, "depth": 2},
            headers={"X-Figma-Token": config.api_key}
        )
        resp.raise_for_status()
        nodes_data = resp.json()
        
        page_node = nodes_data.get("nodes", {}).get(page_id, {}).get("document", {})
        
        # Look for guide frame (named same as page or "Guide")
        guide_frame_id = None
        guide_text = None
        examples = []
        all_frames = []
        
        for child in page_node.get("children", []):
            child_name = child.get("name", "").lower()
            child_type = child.get("type", "")
            
            if child_type == "FRAME" or child_type == "SECTION":
                # Store all frames for fallback text extraction
                # Sort key: x position (to read left-to-right)
                x_pos = child.get("absoluteBoundingBox", {}).get("x", 0)
                all_frames.append((x_pos, child))
                
                # Check for explicit guide frame
                if "guide" in child_name or child_name == page_name.lower():
                    guide_frame_id = child.get("id")
                elif "guide" not in child_name:
                    examples.append({
                        "name": child.get("name"),
                        "id": child.get("id")
                    })
        
        # 3. Extract text
        if guide_frame_id:
            # Case A: Found explicit guide frame
            resp = await client.get(
                f"{FIGMA_API_BASE}/files/{FIGMA_PATTERNS_KEY}/nodes",
                params={"ids": guide_frame_id},
                headers={"X-Figma-Token": config.api_key}
            )
            resp.raise_for_status()
            guide_data = resp.json()
            guide_node = guide_data.get("nodes", {}).get(guide_frame_id, {}).get("document", {})
            
            texts = []
            _extract_text_from_node(guide_node, texts)
            if texts:
                guide_text = "\n\n".join(texts)
                
        else:
            # Case B: No explicit guide frame -> Aggregate text from ALL frames
            # Sort frames left-to-right
            all_frames.sort(key=lambda x: x[0])
            
            # Limit to first 5 frames to avoid too much noise, or just take all?
            # Let's take all frames that look like text content (e.g. not named "Example")
            # For now, let's take up to 10 frames
            sorted_frames = [f[1] for f in all_frames[:10]]
            
            # We need to fetch full content for these frames
            frame_ids = [f["id"] for f in sorted_frames]
            if frame_ids:
                resp = await client.get(
                    f"{FIGMA_API_BASE}/files/{FIGMA_PATTERNS_KEY}/nodes",
                    params={"ids": ",".join(frame_ids)},
                    headers={"X-Figma-Token": config.api_key}
                )
                if resp.status_code == 200:
                    nodes_data = resp.json().get("nodes", {})
                    all_texts = []
                    
                    for fid in frame_ids:
                        f_node = nodes_data.get(fid, {}).get("document", {})
                        f_name = f_node.get("name", "")
                        f_texts = []
                        _extract_text_from_node(f_node, f_texts)
                        
                        if f_texts:
                            # Add frame name as header if it has text
                            section_text = f"### {f_name}\n" + "\n".join(f_texts)
                            all_texts.append(section_text)
                    
                    if all_texts:
                        guide_text = "\n\n".join(all_texts)
        
        # 4. Get image of the pattern page (first meaningful frame)
        image_url = None
        # Use first frame from sorted list if available
        render_frame_id = guide_frame_id
        if not render_frame_id and all_frames:
             # Sort again just to be sure
             all_frames.sort(key=lambda x: x[0])
             render_frame_id = all_frames[0][1]["id"]
             
        if render_frame_id:
            image_url = await get_node_image(FIGMA_PATTERNS_KEY, render_frame_id)
        
        # 5. Generate Figma link
        figma_link = generate_figma_link(FIGMA_PATTERNS_KEY, page_id)
        
        return {
            "name": page_name,
            "type": "pattern",
            "guide": guide_text,
            "examples": [e["name"] for e in examples[:10]],
            "image_url": image_url,
            "figma_link": figma_link,
            "related_patterns": [p["name"] for p in patterns[1:5]] if len(patterns) > 1 else []
        }


async def get_variant_image(component_name: str, description: str) -> dict:
    """Find and render a specific variant of a component.
    
    Args:
        component_name: Name of the component (e.g. "Button")
        description: Description of properties (e.g. "small primary disabled")
        
    Returns:
        dict with 'image_url' and 'variant_name'
    """
    # 1. Get all variants
    variants = await get_component_variants(FIGMA_UI_KIT_KEY, component_name)
    
    if not variants:
        return {"error": f"Component '{component_name}' not found or has no variants."}
    
    # 2. Score variants based on description match
    desc_words = set(description.lower().split())
    best_variant = None
    best_score = -1
    
    for v in variants:
        v_name = v["name"]
        # Parse name "Type=Primary, Size=Small" -> set("primary", "small")
        props_str = v_name.replace("=", " ").replace(",", " ")
        v_words = set(props_str.lower().split())
        
        # Calculate score: intersection size
        score = len(desc_words.intersection(v_words))
        
        # Determine if it is a 'default' variant logic if no strict match?
        # Just simple scoring for now
        
        if score > best_score:
            best_score = score
            best_variant = v
        elif score == best_score and best_variant is None:
             best_variant = v
             
    if not best_variant:
        # Fallback to first if absolutely no match (should unlikely happen if list not empty)
        best_variant = variants[0]
        
    # 3. Get image
    variant_id = best_variant.get("node_id")
    image_url = await get_node_image(FIGMA_UI_KIT_KEY, variant_id)
    
    return {
        "variant_name": best_variant.get("name"),
        "image_url": image_url,
        "description_match_score": best_score
    }



async def search_design_system(query: str) -> list[dict]:
    """Universal search across components, organisms, and patterns.
    
    Searches UI Kit, Organisms, and Bank Patterns files.
    Returns results with type indicator.
    """
    import asyncio
    
    # Get organisms file key
    organisms_key = FILE_KEYS.get("organisms", "JbfXQWGV0BhKVA1RLwn5V9")
    
    # Search in parallel
    components_task = search_components(query, FIGMA_UI_KIT_KEY)
    organisms_task = search_components(query, organisms_key)
    patterns_task = search_patterns(query)
    
    components, organisms, patterns = await asyncio.gather(
        components_task, organisms_task, patterns_task
    )
    
    results = []
    
    # Add components
    for c in components[:8]:
        results.append({
            "type": "component",
            "name": c.get("containing_frame", {}).get("name") or c.get("name"),
            "file_key": FIGMA_UI_KIT_KEY,
            "node_id": c.get("node_id"),
            "source": "ui-kit"
        })
    
    # Add organisms
    for o in organisms[:5]:
        results.append({
            "type": "organism",
            "name": o.get("containing_frame", {}).get("name") or o.get("name"),
            "file_key": organisms_key,
            "node_id": o.get("node_id"),
            "source": "organisms"
        })
    
    # Add patterns
    for p in patterns[:5]:
        results.append({
            "type": "pattern", 
            "name": p["name"],
            "file_key": FIGMA_PATTERNS_KEY,
            "node_id": p["id"],
            "source": "patterns"
        })
    
    return results

