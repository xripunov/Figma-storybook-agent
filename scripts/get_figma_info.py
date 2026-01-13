"""Get Figma file info via Framelink MCP."""
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()


async def get_figma_file_info(file_url: str):
    """Get info about a Figma file using MCP."""
    figma_api_key = os.getenv("FIGMA_API_KEY")
    
    if not figma_api_key:
        print("❌ FIGMA_API_KEY not set")
        return None
    
    print(f"🔄 Fetching info for: {file_url}")
    
    process = await asyncio.create_subprocess_exec(
        "npx", "-y", "figma-developer-mcp", "--stdio",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "FIGMA_API_KEY": figma_api_key}
    )
    
    async def send_request(request: dict) -> dict:
        request_str = json.dumps(request) + "\n"
        process.stdin.write(request_str.encode())
        await process.stdin.drain()
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=60.0)
        return json.loads(response_line.decode()) if response_line else None
    
    try:
        # Initialize
        init_response = await send_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0.1.0"}
            }
        })
        
        if "error" in init_response:
            print(f"❌ Init error: {init_response['error']}")
            return None
            
        print("✅ MCP initialized")
        
        # List available tools
        tools_response = await send_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        })
        
        if "result" in tools_response:
            tools = tools_response["result"].get("tools", [])
            print(f"\n📦 Available MCP Tools ({len(tools)}):")
            for tool in tools[:10]:  # Show first 10
                print(f"   - {tool['name']}: {tool.get('description', '')[:60]}...")
            if len(tools) > 10:
                print(f"   ... and {len(tools) - 10} more")
        
        # Call get_figma_data tool
        data_response = await send_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_figma_data",
                "arguments": {
                    "fileKey": file_url
                }
            }
        })
        
        if "result" in data_response:
            print(f"\n📄 Figma Data:")
            result = data_response["result"]
            print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])
        elif "error" in data_response:
            print(f"❌ Error: {data_response['error']}")
            
        return data_response
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        process.terminate()
        await process.wait()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python scripts/get_figma_info.py <figma-file-url-or-key>")
        print("Example: python scripts/get_figma_info.py https://www.figma.com/file/abc123/MyDesign")
        sys.exit(1)
    
    asyncio.run(get_figma_file_info(sys.argv[1]))
