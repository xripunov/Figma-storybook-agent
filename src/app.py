"""Chainlit application for Design System Agent with Gemini 3.

Features:
- Gemini 3 Flash Preview with Thinking mode
- Complete Figma API Toolset (27+ methods)
- Beautiful tool call visualization with cl.Step
- Automatic Function Calling (AFC)
"""
import chainlit as cl
from google import genai
from google.genai import types
import os
import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

# Import Figma API
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import src.figma_api as figma_api
from tools.figma_tools import (
    get_file_key, 
    analyze_figma_url, 
    search_components, 
    get_component_details,
    search_patterns,
    get_pattern_info,
    search_design_system,
    generate_figma_link,
    get_variant_image,
    FIGMA_UI_KIT_KEY,
    FIGMA_PATTERNS_KEY
)

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


# =============================================================================
# =============================================================================
# Helper for Async execution in Sync Tools
# =============================================================================

def run_async(coro):
    """Run async coroutine in a sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def resolve_file_key(file_alias: str) -> str:
    """Resolve file alias to actual Figma file key."""
    if file_alias == "ui-kit":
        return os.getenv("FIGMA_UI_KIT_FILE_KEY", "fRi3HAgxLDuHW4MJQPf5r3")
    return file_alias

# =============================================================================
import httpx

# Helper to safely send image from sync tool
def send_image_sync(url: str, name: str):
    """Download and send image to Chainlit UI synchronously."""
    try:
        # Download image content (server-side, bypassing client S3 blocks)
        with httpx.Client() as http:
            resp = http.get(url, timeout=10)
            if resp.status_code == 200:
                image_data = resp.content
                
                # Send to Chainlit
                # cl.run_sync runs an async function from a sync context
                async def _send():
                    await cl.Message(
                        content="", 
                        elements=[
                            cl.Image(content=image_data, name=name, display="inline")
                        ]
                    ).send()
                
                cl.run_sync(_send())
    except Exception as e:
        print(f"Failed to send image: {e}")
# Sync Tools (No Visualization for AFC Compatibility)
# =============================================================================

def get_design_component_details(component_name: str, file: str = "ui-kit") -> dict:
    """SUPER TOOL: Get full component details (guide, variants, tokens).
    
    ALWAYS use this tool when asked about a component (e.g. "Tell me about Button").
    
    Args:
        component_name: Name of the component (e.g. "Button", "Input")
        file: File alias (default: "ui-kit")
    """
    file_key = resolve_file_key(file)
    res = run_async(
        get_component_details(file_key, component_name)
    )
    
    # Check for image and proxy it
    if res and res.get("image_url"):
        send_image_sync(res["image_url"], f"{component_name}_preview")
        res["image_url"] = "Image sent to chat." # Hide raw URL from model
        
    return res

def find_components(query: str, file: str = "ui-kit") -> list:
    """Smart search for components by name (fuzzy match).
    
    Args:
        query: Component name to search for (e.g., "Button", "Input")
        file: File alias to search in (default: "ui-kit")
    """
    file_key = resolve_file_key(file)
    return run_async(
        search_components(query, file_key)
    )


def get_design_pattern_info(pattern_name: str) -> dict:
    """Get detailed info about a design PATTERN (not component).
    
    Use this for UX patterns like: validation, modals, forms, navigation, etc.
    Patterns are in a separate file from components.
    
    Args:
        pattern_name: Name of the pattern (e.g. "Валидация", "Модальные", "Формы")
    """
    res = run_async(
        get_pattern_info(pattern_name)
    )
    
    if res and res.get("image_url"):
         send_image_sync(res["image_url"], f"{pattern_name}_preview")
         res["image_url"] = "Image sent to chat."
         
    return res


def search_design_system_tool(query: str) -> list:
    """Search across ALL design system: components AND patterns.
    
    Use this when user asks a general question that could be about either.
    Returns results from both UI Kit and Patterns.
    
    Args:
        query: Search term (e.g. "модальные", "кнопка", "валидация")
    """
    return run_async(
        search_design_system(query)
    )

def get_component_variant_image_tool(component_name: str, description: str) -> dict:
    """Generate/Get image for a SPECIFIC component variant (e.g. Primary Button).
    
    Use this when user asks to "make", "show", "generate" a specific version.
    
    Args:
        component_name: Component name (e.g. "Button")
        description: Desired properties (e.g. "primary small disabled")
    """
    res = run_async(
        get_variant_image(component_name, description)
    )
    
    if res and res.get("image_url"):
        send_image_sync(res["image_url"], res.get("variant_name", "variant"))
        res["image_url"] = "Image sent to chat."
        
    return res

# --- File Methods ---

def figma_get_file(file_key: str, depth: int = 2) -> dict:
    """Get a Figma file by key."""
    return run_async(
        figma_api.figma_get_file(file_key, depth=depth)
    )

def figma_get_file_nodes(file_key: str, ids: list[str]) -> dict:
    """Get specific nodes from a Figma file."""
    return run_async(
        figma_api.figma_get_file_nodes(file_key, ids)
    )

def figma_get_images(file_key: str, ids: list[str], format: str = "png") -> dict:
    """Render images from a Figma file."""
    return run_async(
        figma_api.figma_get_images(file_key, ids, format=format)
    )

def figma_get_image_fills(file_key: str) -> dict:
    """Get image fills in a Figma file."""
    return run_async(
        figma_api.figma_get_image_fills(file_key)
    )

def figma_get_file_versions(file_key: str) -> dict:
    """Get version history of a Figma file."""
    return run_async(
        figma_api.figma_get_file_versions(file_key)
    )

# --- Comment Methods ---

def figma_get_comments(file_key: str) -> dict:
    """Get comments in a Figma file."""
    return run_async(
        figma_api.figma_get_comments(file_key)
    )

def figma_post_comment(file_key: str, message: str, comment_id: str = None) -> dict:
    """Add a comment to a Figma file or reply to a comment."""
    return run_async(
        figma_api.figma_post_comment(file_key, message, comment_id=comment_id)
    )

def figma_delete_comment(file_key: str, comment_id: str) -> dict:
    """Delete a comment from a Figma file."""
    return run_async(
        figma_api.figma_delete_comment(file_key, comment_id)
    )

def figma_get_comment_reactions(file_key: str, comment_id: str) -> dict:
    """Get reactions for a comment."""
    return run_async(
        figma_api.figma_get_comment_reactions(file_key, comment_id)
    )

def figma_post_comment_reaction(file_key: str, comment_id: str, emoji: str) -> dict:
    """Add a reaction to a comment."""
    return run_async(
        figma_api.figma_post_comment_reaction(file_key, comment_id, emoji)
    )

def figma_delete_comment_reaction(file_key: str, comment_id: str, emoji: str) -> dict:
    """Delete a reaction from a comment."""
    return run_async(
        figma_api.figma_delete_comment_reaction(file_key, comment_id, emoji)
    )

# --- Team and Project Methods ---

def figma_get_team_projects(team_id: str) -> dict:
    """Get projects in a team."""
    return run_async(
        figma_api.figma_get_team_projects(team_id)
    )

def figma_get_project_files(project_id: str) -> dict:
    """Get files in a project."""
    return run_async(
        figma_api.figma_get_project_files(project_id)
    )

# --- Component Methods ---

def figma_get_team_components(team_id: str, page_size: int = 30) -> dict:
    """Get components in a team library."""
    return run_async(
        figma_api.figma_get_team_components(team_id, page_size)
    )

def figma_get_file_components(file_key: str) -> dict:
    """Get components in a file."""
    return run_async(
        figma_api.figma_get_file_components(file_key)
    )

def figma_get_component(component_key: str) -> dict:
    """Get a component by key."""
    return run_async(
        figma_api.figma_get_component(component_key)
    )

def figma_get_team_component_sets(team_id: str, page_size: int = 30) -> dict:
    """Get component sets in a team library."""
    return run_async(
        figma_api.figma_get_team_component_sets(team_id, page_size)
    )

def figma_get_file_component_sets(file_key: str) -> dict:
    """Get component sets in a file."""
    return run_async(
        figma_api.figma_get_file_component_sets(file_key)
    )

def figma_get_component_set(component_set_key: str) -> dict:
    """Get a component set by key."""
    return run_async(
        figma_api.figma_get_component_set(component_set_key)
    )

# --- Style Methods ---

def figma_get_team_styles(team_id: str, page_size: int = 30) -> dict:
    """Get styles in a team library."""
    return run_async(
        figma_api.figma_get_team_styles(team_id, page_size)
    )

def figma_get_file_styles(file_key: str) -> dict:
    """Get styles in a file."""
    return run_async(
        figma_api.figma_get_file_styles(file_key)
    )

def figma_get_style(style_key: str) -> dict:
    """Get a style by key."""
    return run_async(
        figma_api.figma_get_style(style_key)
    )

# --- Helper Methods ---

async def helper_analyze_url(url: str) -> dict:
    """Analyze Figma URL and return details."""
    return await call_tool(
        "analyze_figma_url", 
        {"url": url}, 
        analyze_figma_url(url)
    )


# =============================================================================
# Configuration
# =============================================================================

# SIMPLIFIED TOOLS LIST - only the essentials to avoid model confusion
TOOLS = [
    get_design_component_details,  # For component questions
    get_component_variant_image_tool, # For specific variant images
    get_design_pattern_info,       # For pattern questions
    search_design_system_tool,     # Universal search
    figma_get_comments,            # For comments
    figma_post_comment,            # For adding comments
]

SYSTEM_PROMPT = """Ты — AI-ассистент по дизайн-системе Figma.

## ИСТОЧНИКИ ИНФОРМАЦИИ

### Компоненты (UI Kit)
Атомарные UI-элементы: Button, Input, Avatar, Badge, Checkbox, Chip, Dropdown, 
Tab Bar, Table, Text Area, Toast, Tooltip, Spinner, Switch, Radio, Slider и др.

### Организмы
Составные компоненты: Bank Card, Account Card, Flow Result View, Page Header,
Payment Widget, Task Card, Timeline Event, Error View, Search Module и др.

### Паттерны (UX-правила)
UX-практики: Валидация, Формы, Навигация по экранам, Загрузка страницы, 
Брейкпоинты, Ховеры, Тёмная тема, Modal, Drawer, Tooltip и др.

## СТРАТЕГИЯ ОТВЕТА

1. **Если вопрос про UI-элемент** → `get_design_component_details(name)`
   
2. **Если вопрос про правила/поведение** → `get_design_pattern_info(name)`

3. **Если не уверена или не нашла** → `search_design_system_tool(query)`
   Используй поиск как fallback — он ищет везде.

4. **Если тема пересекается** (Modal, Tooltip, etc.) → вызови ОБА инструмента

## ИСПОЛЬЗОВАНИЕ СВОЙСТВ

В ответе `get_design_component_details` есть поле `props.summary`:
- **ИСПОЛЬЗУЙ ЕГО** для описания компонента.
- **НЕ ПЕРЕЧИСЛЯЙ** список вариантов из поля `variants`, если их много. Лучше написать: "Основные свойства: размер, цвет, состояние...".
- Если есть `props.definitions` (для кода), используй их для генерации примеров, если просят код.

## ГЕНЕРАЦИЯ (КОД + ИЗОБРАЖЕНИЕ)

Если попросили "сгенерировать", "сделать" или "показать" конкретный варинт (кнопку primary):

1. **Код**: используй `get_design_component_details` → поле `props.definitions` → генерируй JSX
2. **Изображение**: вызови `get_component_variant_image_tool(name, properties)`
   
Пример вопроса: "Сделай кнопку primary small"
→ Вызов 1: `get_design_component_details("Button")` (для кода)
→ Вызов 2: `get_component_variant_image_tool("Button", "primary small")` (для картинки)

## ФОРМАТ ОТВЕТА

📦 **[Название]** (компонент) или 📐 **[Название]** (паттерн)

[Изображение варианта, если просили]

[Информация: описание из гайда + краткая сводка свойств (Type, Size...)]

🔗 [Открыть в Figma](ссылка)

## ОТЛАДКА

Если в ответе есть поле `_debug_info` и что-то не нашлось (картинка или свойства):
- Сообщи пользователю технические детали: "Debug Info: Page={page_id}, Target={target_id}, Via={image_found_via}".
- Это поможет разработчику исправить ошибку.

## ПРАВИЛА
- Отвечай на русском
- Не нашла → используй поиск
- Не придумывай правил
- Всегда давай ссылку на Figma
"""




@cl.on_chat_start
async def on_chat_start():
    await cl.Message(
        content="""👋 **Привет! Я ассистент по дизайн-системе Точка Банка.**

Могу помочь с:

📦 **Компоненты** — Button, Input, Modal, Card...
- "Расскажи про Button"
- "Какие варианты у Input?"

📐 **Паттерны** — Валидация, Формы, Навигация...
- "Как работает валидация?"
- "Есть правила про модальные окна?"

🔍 **Поиск** — найду нужное
- "Есть что-то про высоту модалок?"
"""
    ).send()



@cl.on_message
async def on_message(message: cl.Message):
    async with cl.Step(name="🤖 Поиск", type="run") as step:
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                response = await client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=message.content,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        tools=TOOLS
                    )
                )
                
                answer_text = ""
                for candidate in response.candidates:
                    for part in candidate.content.parts:
                        if part.text:
                            answer_text += part.text
                
                break
                    
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and retry_count < max_retries - 1:
                    wait_time = (2 ** retry_count) * 2
                    step.output = f"⏳ Rate limit hit. Retrying in {wait_time}s..."
                    await asyncio.sleep(wait_time)
                    retry_count += 1
                    continue
                else:
                    step.output = f"❌ Error: {error_str}"
                    await cl.Message(content=f"Error: {error_str}").send()
                    return

    if answer_text:
        await cl.Message(content=answer_text).send()
