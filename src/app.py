"""Chainlit application for Design System Agent with Gemini."""
import chainlit as cl
from google import genai
from google.genai import types
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Import Figma tools
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools.figma_tools import (
    list_design_system_files,
    list_components,
    search_components,
    get_component_variants,
    get_component_info,
    get_component_guide,
    get_component_details,
    get_file_key,
    analyze_figma_url,
    FILE_KEYS,
)

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Tool definitions for Gemini
TOOL_DEFINITIONS = [
    types.FunctionDeclaration(
        name="list_files",
        description="Показать список всех файлов дизайн-системы (Foundation, UI Kit, Icons, etc.)",
        parameters=types.Schema(type="OBJECT", properties={}, required=[])
    ),
    types.FunctionDeclaration(
        name="search_components",
        description="Поиск компонентов по имени. Например: 'Button', 'Avatar', 'Modal'",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "query": types.Schema(type="STRING", description="Название компонента для поиска"),
                "file": types.Schema(
                    type="STRING", 
                    description="Файл для поиска (ui-kit, icons, organisms). По умолчанию ui-kit",
                    enum=list(FILE_KEYS.keys())
                )
            },
            required=["query"]
        )
    ),
    types.FunctionDeclaration(
        name="get_variants",
        description="Получить все варианты компонента (размеры, состояния, типы)",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "component": types.Schema(type="STRING", description="Название компонента"),
                "file": types.Schema(
                    type="STRING",
                    description="Файл (по умолчанию ui-kit)",
                    enum=list(FILE_KEYS.keys())
                )
            },
            required=["component"]
        )
    ),
    types.FunctionDeclaration(
        name="list_components_in_file",
        description="Показать все компоненты в конкретном файле дизайн-системы",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "file": types.Schema(
                    type="STRING",
                    description="Название файла",
                    enum=list(FILE_KEYS.keys())
                )
            },
            required=["file"]
        )
    ),
    types.FunctionDeclaration(
        name="get_guide",
        description="Получить документацию/гайд компонента из Figma (описание, спецификация, использование)",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "component": types.Schema(type="STRING", description="Название компонента (например: Button, Avatar, Modal)"),
                "file": types.Schema(
                    type="STRING",
                    description="Файл (по умолчанию ui-kit)",
                    enum=list(FILE_KEYS.keys())
                )
            },
            required=["component"]
        )
    ),
    types.FunctionDeclaration(
        name="get_component_details",
        description="СУПЕР-ИНСТРУМЕНТ: Получить ВСЮ информацию о компоненте (поиск + варианты + гайд). Используй этот инструмент по умолчанию, когда спрашивают про компонент.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "query": types.Schema(type="STRING", description="Название компонента (Button, Avatar, etc.)"),
                "file": types.Schema(
                    type="STRING",
                    description="Файл (по умолчанию ui-kit)",
                    enum=list(FILE_KEYS.keys())
                )
            },
            required=["query"]
        )
    ),
    types.FunctionDeclaration(
        name="analyze_design_link",
        description="Анализ ссылки на Figma. Используй, если пользователь прислал URL (https://figma.com/...). Возвращает информацию о компоненте и статистику использования.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "url": types.Schema(type="STRING", description="Ссылка на файл/ноду Figma")
            },
            required=["url"]
        )
    ),
    types.FunctionDeclaration(
        name="read_notes",
        description="Прочитать свои заметки (память). Используй в начале сложной задачи, чтобы вспомнить контекст проекта и предыдущие находки.",
        parameters=types.Schema(type="OBJECT", properties={}, required=[])
    ),
    types.FunctionDeclaration(
        name="write_notes",
        description="Записать важную информацию в память. Используй, когда узнаёшь что-то полезное о проекте (токены, правила, решения).",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "content": types.Schema(type="STRING", description="Текст заметки для добавления")
            },
            required=["content"]
        )
    )
]

TOOLS = types.Tool(function_declarations=TOOL_DEFINITIONS)

SYSTEM_PROMPT = """Ты — ИИ-ассистент для работы с дизайн-системой Tochka Bank.

У тебя есть доступ к Figma файлам дизайн-системы через инструменты.

## ВАЖНО — Правила использования инструментов:

**ГЛАВНОЕ ПРАВИЛО: Если пользователь спрашивает о компоненте (как использовать, какие варианты, размеры, что это такое) — ИСПОЛЬЗУЙ `get_component_details`.**
Этот инструмент сразу ищет компонент, показывает его варианты и загружает документацию (гайд).

Остальные инструменты используй только для специфичных задач:
- `search_components` — если нужно только найти правильное название
- `get_variants` — если нужны только варианты
- `get_guide` — если нужно только описание
- `list_files` — показать структуру файлов

## Файлы:
- ui-kit — основные компоненты
- foundation — стили
- icons, content, organisms

## Память:
У тебя есть долгосрочная память (`read_notes`, `write_notes`). 
- В начале сложной задачи — прочитай заметки, чтобы вспомнить контекст.
- Когда узнаёшь что-то важное — запиши это (правила проекта, найденные токены, решения).
- Пример записи: "Для кнопок используется токен sys.primary. Радиус углов: 8px."

## Алгоритм:
1. Ссылка на Figma -> `analyze_design_link`
2. Вопрос про компонент -> `get_component_details`
3. Анализируй полученный JSON (там будут search_matches, variants, guide)
3. Формулируй ответ своими словами на основе гайда и вариантов.

Отвечай на русском языке."""


async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return the result."""
    try:
        if name == "list_files":
            files = await list_design_system_files()
            result = "📁 Файлы дизайн-системы:\n\n"
            for f in files:
                result += f"• **{f['name']}**\n  `{f['key']}`\n"
            return result
            
        elif name == "search_components":
            file_key = get_file_key(args.get("file", "ui-kit"))
            components = await search_components(args["query"], file_key)
            
            if not components:
                return f"❌ Компоненты по запросу '{args['query']}' не найдены"
            
            result = f"🔍 Найдено {len(components)} компонентов:\n\n"
            for c in components[:10]:
                frame = c.get("containing_frame", {}).get("name", "")
                result += f"• **{c['name']}**\n  Фрейм: {frame}\n"
            
            if len(components) > 10:
                result += f"\n... и ещё {len(components) - 10}"
            return result
            
        elif name == "get_variants":
            file_key = get_file_key(args.get("file", "ui-kit"))
            variants = await get_component_variants(file_key, args["component"])
            
            if not variants:
                return f"❌ Варианты для '{args['component']}' не найдены"
            
            frame = variants[0].get("containing_frame", {}).get("name", "Unknown")
            result = f"🎨 **{frame}** — {len(variants)} вариантов:\n\n"
            
            for v in variants[:15]:
                result += f"• {v['name']}\n"
            
            if len(variants) > 15:
                result += f"\n... и ещё {len(variants) - 15}"
            return result
            
        elif name == "list_components_in_file":
            file_key = get_file_key(args["file"])
            components = await list_components(file_key)
            
            # Group by frame
            by_frame = {}
            for c in components:
                frame = c.get("containing_frame", {}).get("name", "Other")
                if frame not in by_frame:
                    by_frame[frame] = []
                by_frame[frame].append(c["name"])
            
            result = f"📦 Компоненты в {args['file']} ({len(components)} всего):\n\n"
            for frame, comps in sorted(by_frame.items())[:20]:
                result += f"**{frame}** ({len(comps)})\n"
            
            if len(by_frame) > 20:
                result += f"\n... и ещё {len(by_frame) - 20} фреймов"
            return result
        
        elif name == "get_guide":
            file_key = get_file_key(args.get("file", "ui-kit"))
            guide = await get_component_guide(file_key, args["component"])
            
            if not guide:
                return f"❌ Гайд для компонента '{args['component']}' не найден.\nВозможно, фрейм называется иначе (попробуйте точное название из Figma)."
            
            # Truncate if too long
            if len(guide) > 3000:
                guide = guide[:3000] + "\n\n... (текст сокращён)"
            
            return f"📖 **{args['component']} / Guide**\n\n{guide}"
            
        elif name == "get_component_details":
            file_key = get_file_key(args.get("file", "ui-kit"))
            details = await get_component_details(file_key, args["query"])
            
            if "error" in details:
                return f"❌ {details['error']}"
            
            # Format the output for the LLM
            found_name = details.get("found_name", "Unknown")
            variants_count = details.get("variants_count", 0)
            variants_list = ", ".join(details.get("variants", []))
            guide_text = details.get("guide") or "Описание не найдено (нет фрейма Guide)"
            
            # Truncate guide if too massive
            if len(guide_text) > 4000:
                guide_text = guide_text[:4000] + "\n...(сокращено)"

            # Format props/tokens
            props_text = ""
            node_props = details.get("props", {})
            if "tokens" in node_props and node_props["tokens"]:
                props_text = "\n🧬 **Токены (найдены в свойствах):**\n" + "\n".join([f"- {t}" for t in node_props["tokens"]]) + "\n"

            # Send image to user immediately if found
            image_url = details.get("image_url")
            if image_url:
                await cl.Message(
                    content="",
                    elements=[
                        cl.Image(url=image_url, name=found_name, display="inline")
                    ]
                ).send()
                
            return f"""
✅ **Найдено: {found_name}**
--------------------------------------------------
🔍 **Результаты поиска:**
{chr(10).join(['- ' + m for m in details.get('search_matches', [])])}

🎨 **Варианты ({variants_count}):**
{variants_list}

📖 **Гайд / Документация:**
--------------------------------------------------
{guide_text}
{props_text}--------------------------------------------------
"""

        elif name == "analyze_design_link":
            analysis = await analyze_figma_url(args["url"])
            if "error" in analysis:
                return f"❌ {analysis['error']}"
            
            target_name = analysis.get("target_name", "Unknown")
            usages = analysis.get("usages", {})
            details = analysis.get("details", {})
            
            # Usage text
            usage_text = ""
            if usages and usages.get("total_count", 0) > 0:
                usage_text = f"📊 **Используется {usages['total_count']} раз** в текущем файле:\n"
                for ctx, count in usages.get("contexts", {}).items():
                    usage_text += f"- {ctx}: {count}\n"
            elif usages is not None:
                 usage_text = "📊 Не используется в этом файле."

            # Image
            image_url = details.get("image_url")
            if image_url:
                await cl.Message(
                    content="",
                    elements=[cl.Image(url=image_url, name=target_name, display="inline")]
                ).send()
            
            # Props
            props_text = ""
            node_props = details.get("props", {})
            if "tokens" in node_props and node_props["tokens"]:
                props_text = "\n🧬 **Токены:**\n" + "\n".join([f"- {t}" for t in node_props["tokens"]]) + "\n"

            guide = details.get("guide") or ""
            if len(guide) > 1000: guide = guide[:1000] + "..."

            return f"""
🔗 **Анализ ссылки:**
Компонент: **{target_name}**
({analysis.get('analysis_type')})

{usage_text}
--------------------------------------------------
{props_text}
📖 **Краткое описание:**
{guide}
"""

        elif name == "read_notes":
            notes_path = ".notes/memory.md"
            if os.path.exists(notes_path):
                with open(notes_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.strip():
                    return f"📝 **Твои заметки:**\n\n{content}"
                else:
                    return "📝 Заметки пусты. Ты ещё ничего не записывал."
            else:
                return "📝 Заметки пусты. Ты ещё ничего не записывал."
        
        elif name == "write_notes":
            notes_dir = ".notes"
            notes_path = f"{notes_dir}/memory.md"
            
            if not os.path.exists(notes_dir):
                os.makedirs(notes_dir)
            
            # Append new note with timestamp
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            new_note = f"\n---\n**[{timestamp}]**\n{args['content']}\n"
            
            with open(notes_path, "a", encoding="utf-8") as f:
                f.write(new_note)
            
            return f"✅ Записано в память:\n{args['content']}"

        else:
            return f"❌ Неизвестный инструмент: {name}"
            
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"


import datetime
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

# ... (imports) ...


@cl.data_layer
def get_data_layer():
    return SQLAlchemyDataLayer(conninfo="sqlite+aiosqlite:///chat_history.db")


@cl.password_auth_callback
def auth_callback(username, password):
    return cl.User(identifier=username)


def save_chat_history(history: list, session_id: str):
    """Save chat history to a JSON file."""
    chat_dir = ".chats"
    if not os.path.exists(chat_dir):
        os.makedirs(chat_dir)
    
    # Convert history objects to dicts
    serializable_history = []
    for content in history:
        parts = []
        for part in content.parts:
            p = {}
            if part.text:
                p["text"] = part.text
            if part.function_call:
                p["function_call"] = {
                    "name": part.function_call.name,
                    "args": dict(part.function_call.args)
                }
            if part.function_response:
                p["function_response"] = {
                    "name": part.function_response.name,
                    "response": part.function_response.response
                }
            parts.append(p)
        
        serializable_history.append({
            "role": content.role,
            "parts": parts,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    filepath = os.path.join(chat_dir, f"chat_{session_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(serializable_history, f, ensure_ascii=False, indent=2)


@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    cl.user_session.set("history", [])
    # Generate unique session ID based on time
    session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    cl.user_session.set("session_id", session_id)
    
    await cl.Message(
        content="👋 Привет! Я ИИ-ассистент для работы с дизайн-системой Tochka Bank.\n\n"
                "Я могу:\n"
                "• Найти компоненты и показать гайды\n"
                "• Показать варианты компонентов\n" 
                "• Ответить на вопросы по использованию\n\n"
                "Попробуй спросить: *«Расскажи про компонент Button»*"
    ).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages."""
    history = cl.user_session.get("history", [])
    session_id = cl.user_session.get("session_id")
    
    # Add user message to history
    history.append(types.Content(role="user", parts=[types.Part(text=message.content)]))
    save_chat_history(history, session_id)
    
    # Create response message
    msg = cl.Message(content="")
    await msg.send()
    
    try:
        # Call Gemini with tools
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[TOOLS],
            )
        )
        # ... (rest of the code) ...
        
        # Process response
        full_response = ""
        tool_was_called = False
        
        for candidate in response.candidates:
            for part in candidate.content.parts:
                # Check for function calls
                if part.function_call:
                    tool_was_called = True
                    func_name = part.function_call.name
                    func_args = dict(part.function_call.args) if part.function_call.args else {}
                    
                    # Show brief indicator (not the full result)
                    await msg.stream_token(f"� *Ищу информацию о компоненте...*\n\n")
                    
                    # Execute tool (result goes to model, not user)
                    result = await execute_tool(func_name, func_args)
                    
                    # Add function response to history
                    history.append(types.Content(
                        role="model",
                        parts=[types.Part(function_call=part.function_call)]
                    ))
                    history.append(types.Content(
                        role="user",
                        parts=[types.Part(function_response=types.FunctionResponse(
                            name=func_name,
                            response={"result": result}
                        ))]
                    ))
                    
                    # Get model's interpretation of the data
                    follow_up = await client.aio.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=history,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT + "\n\nОтветь на вопрос пользователя своими словами, кратко и по делу. Не просто копируй текст, а дай осмысленный ответ.",
                        )
                    )
                    
                    if follow_up.text:
                        await msg.stream_token(follow_up.text)
                        full_response = follow_up.text
                        history.append(types.Content(
                            role="model",
                            parts=[types.Part(text=follow_up.text)]
                        ))
                
                # Regular text response (no tool call)
                elif part.text:
                    await msg.stream_token(part.text)
                    full_response = part.text
        
        # Save history
        if full_response and not tool_was_called:
            history.append(types.Content(role="model", parts=[types.Part(text=full_response)]))
        
        cl.user_session.set("history", history)
        save_chat_history(history, session_id)
        await msg.update()
        
    except Exception as e:
        await msg.stream_token(f"❌ Ошибка: {str(e)}")
        await msg.update()
