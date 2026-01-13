"""Test Figma MCP connection via Framelink."""
import asyncio
import json
import subprocess
import sys
import os
from dotenv import load_dotenv

load_dotenv()


async def test_figma_mcp():
    """Test connection to Figma MCP server."""
    figma_api_key = os.getenv("FIGMA_API_KEY")
    
    if not figma_api_key or figma_api_key == "your-figma-personal-access-token":
        print("❌ FIGMA_API_KEY not set in .env file")
        print("   1. Go to Figma → Settings → Personal Access Tokens")
        print("   2. Create a new token")
        print("   3. Add it to .env: FIGMA_API_KEY=your-token")
        return False
    
    print("🔄 Starting Framelink Figma MCP server...")
    
    # Start MCP server as subprocess
    process = await asyncio.create_subprocess_exec(
        "npx", "-y", "figma-developer-mcp", "--stdio",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "FIGMA_API_KEY": figma_api_key}
    )
    
    # Send initialize request (MCP protocol)
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "design-system-agent-test",
                "version": "0.1.0"
            }
        }
    }
    
    try:
        # Send request
        request_str = json.dumps(init_request) + "\n"
        process.stdin.write(request_str.encode())
        await process.stdin.drain()
        
        # Read response with timeout
        response_line = await asyncio.wait_for(
            process.stdout.readline(),
            timeout=30.0
        )
        
        if response_line:
            response = json.loads(response_line.decode())
            if "result" in response:
                print("✅ Figma MCP server connected successfully!")
                print(f"   Server: {response['result'].get('serverInfo', {}).get('name', 'unknown')}")
                print(f"   Version: {response['result'].get('serverInfo', {}).get('version', 'unknown')}")
                return True
            else:
                print(f"❌ Unexpected response: {response}")
                return False
        else:
            stderr = await process.stderr.read()
            print(f"❌ No response from server. Stderr: {stderr.decode()}")
            return False
            
    except asyncio.TimeoutError:
        print("❌ Connection timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        process.terminate()
        await process.wait()


if __name__ == "__main__":
    success = asyncio.run(test_figma_mcp())
    sys.exit(0 if success else 1)
