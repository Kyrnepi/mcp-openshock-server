"""
OpenShock MCP Server
A Model Context Protocol server for controlling OpenShock devices with safety features.
"""

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
import os
from typing import Any, Dict, List, Optional
import logging
from contextlib import asynccontextmanager
import json

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
OPENSHOCK_API_URL = os.getenv("OPENSHOCK_API_URL", "https://api.openshock.app")
OPENSHOCK_API_TOKEN = os.getenv("OPENSHOCK_API_TOKEN")
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN")
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "openshock-mcp-server")
MCP_VERSION = os.getenv("MCP_VERSION", "2.0.1")
SHOCK_LIMIT = int(os.getenv("SHOCK_LIMIT", "0"))  # 0 = no limit

# Startup logging to verify configuration
logger.info(f"Starting {MCP_SERVER_NAME} v{MCP_VERSION}")
logger.info(f"OpenShock API URL: {OPENSHOCK_API_URL}")
logger.info(f"OpenShock API Token configured: {'Yes' if OPENSHOCK_API_TOKEN else 'No'}")
logger.info(f"MCP Auth Token configured: {'Yes' if MCP_AUTH_TOKEN else 'No'}")
logger.info(f"Shock intensity limit: {'No limit' if SHOCK_LIMIT == 0 else str(SHOCK_LIMIT)}")

if SHOCK_LIMIT > 0:
    logger.info(f"SECURITY: Shock intensity will be automatically limited to maximum {SHOCK_LIMIT}")

if not OPENSHOCK_API_TOKEN:
    raise ValueError("OPENSHOCK_API_TOKEN environment variable is required")
if not MCP_AUTH_TOKEN:
    raise ValueError("MCP_AUTH_TOKEN environment variable is required")

# Global HTTP client for connection pooling
http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup/shutdown)"""
    global http_client

    # Startup: Create HTTP client with connection pooling
    logger.info("Initializing HTTP client with connection pooling")
    http_client = httpx.AsyncClient(
        headers={
            "OpenShockToken": OPENSHOCK_API_TOKEN,
            "Content-Type": "application/json"
        },
        timeout=30.0,
        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
    )

    yield

    # Shutdown: Close HTTP client
    logger.info("Closing HTTP client")
    if http_client:
        await http_client.aclose()


# Initialize FastAPI app
app = FastAPI(title=MCP_SERVER_NAME, version=MCP_VERSION, lifespan=lifespan)


def verify_auth(authorization: Optional[str] = Header(None)):
    """Verify authentication token (Bearer prefix optional)"""
    if not authorization:
        logger.warning("Missing Authorization header")
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    # Extract token (Bearer prefix is optional for MCP client compatibility)
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization

    if token != MCP_AUTH_TOKEN:
        logger.warning("Invalid authentication token")
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    return token


def get_max_shock_intensity() -> int:
    """Returns the maximum allowed shock intensity"""
    if SHOCK_LIMIT == 0:
        return 100  # No limit
    return min(SHOCK_LIMIT, 100)  # Cannot exceed 100 anyway


# Command mapping: MCP tool names to OpenShock API command types
COMMAND_MAPPING = {
    "STOP": 0,
    "SHOCK": 1,
    "VIBRATE": 2,
    "BEEP": 3
}


def get_tool_schemas():
    """Returns MCP tool schemas"""
    max_shock_intensity = get_max_shock_intensity()

    return {
        "tools": [
            {
                "name": "SHOCK",
                "description": f"Send shock command to OpenShock devices (intensity automatically limited to {max_shock_intensity} if SHOCK_LIMIT is set)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "shockers": {
                            "type": "array",
                            "description": "List of shockers to control",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "description": "Shocker ID"},
                                    "intensity": {"type": "integer", "minimum": 1, "maximum": 100,
                                                "description": f"Shock intensity (1-100, automatically limited to {max_shock_intensity})"},
                                    "duration": {"type": "integer", "minimum": 300, "maximum": 30000,
                                               "description": "Duration in milliseconds (300-30000)"}
                                },
                                "required": ["id", "intensity", "duration"]
                            }
                        }
                    },
                    "required": ["shockers"]
                }
            },
            {
                "name": "VIBRATE",
                "description": "Send vibration command to OpenShock devices",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "shockers": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "intensity": {"type": "integer", "minimum": 1, "maximum": 100},
                                    "duration": {"type": "integer", "minimum": 300, "maximum": 30000}
                                },
                                "required": ["id", "intensity", "duration"]
                            }
                        }
                    },
                    "required": ["shockers"]
                }
            },
            {
                "name": "BEEP",
                "description": "Send beep/sound command to OpenShock devices",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "shockers": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "intensity": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
                                    "duration": {"type": "integer", "minimum": 300, "maximum": 30000}
                                },
                                "required": ["id", "intensity", "duration"]
                            }
                        }
                    },
                    "required": ["shockers"]
                }
            },
            {
                "name": "STOP",
                "description": "Stop all commands on OpenShock devices",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "shockers": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"}
                                },
                                "required": ["id"]
                            }
                        }
                    },
                    "required": ["shockers"]
                }
            }
        ]
    }


async def execute_openshock_command(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a command on OpenShock devices"""
    if not http_client:
        raise RuntimeError("HTTP client not initialized")

    shockers = arguments.get("shockers", [])
    shocks = []
    max_shock_intensity = get_max_shock_intensity()
    intensity_adjustments = []

    for shocker in shockers:
        shocker_id = shocker.get("id")
        if not shocker_id:
            raise ValueError("Missing shocker ID")

        shock_request = {
            "id": shocker_id,
            "type": COMMAND_MAPPING[tool_name]
        }

        if tool_name == "STOP":
            shock_request.update({"intensity": 0, "duration": 300})
        elif tool_name == "SHOCK":
            intensity = shocker.get("intensity")
            duration = shocker.get("duration")
            if intensity is None or duration is None:
                raise ValueError(f"{tool_name} requires intensity and duration")

            original_intensity = intensity
            if SHOCK_LIMIT > 0 and intensity > max_shock_intensity:
                intensity = max_shock_intensity
                intensity_adjustments.append({
                    "shocker_id": shocker_id,
                    "requested": original_intensity,
                    "applied": intensity
                })

            shock_request.update({"intensity": intensity, "duration": duration})
        elif tool_name in ["VIBRATE", "BEEP"]:
            intensity = shocker.get("intensity", 50 if tool_name == "BEEP" else None)
            duration = shocker.get("duration")
            if intensity is None or duration is None:
                raise ValueError(f"{tool_name} requires intensity and duration")
            shock_request.update({"intensity": intensity, "duration": duration})

        shocks.append(shock_request)

    api_request = {
        "shocks": shocks,
        "customName": f"MCP-{tool_name}"
    }

    response = await http_client.post(
        f"{OPENSHOCK_API_URL}/2/shockers/control",
        json=api_request
    )
    response.raise_for_status()

    try:
        result = response.json()
    except Exception:
        result = {"message": response.text, "status": "success"}

    success_message = f"Successfully executed {tool_name} command on {len(shocks)} shocker(s)."
    if intensity_adjustments:
        success_message += "\n\nSecurity adjustments applied:"
        for adj in intensity_adjustments:
            success_message += f"\n- Shocker {adj['shocker_id']}: intensity reduced from {adj['requested']} to {adj['applied']}"

    return {
        "content": [{"type": "text", "text": success_message}]
    }


@app.post("/mcp")
async def mcp_endpoint(request: Request, authorization: Optional[str] = Header(None)):
    """MCP JSON-RPC endpoint with authentication"""
    verify_auth(authorization)

    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": MCP_SERVER_NAME, "version": MCP_VERSION}
            }
        elif method == "tools/list":
            result = get_tool_schemas()
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            result = await execute_openshock_command(tool_name, arguments)
        else:
            return JSONResponse(
                status_code=200,
                content={"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method not found: {method}"}, "id": request_id}
            )

        async def generate_stream():
            response_data = {"jsonrpc": "2.0", "result": result, "id": request_id}
            yield f"data: {json.dumps(response_data)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        async def generate_error_stream():
            error_data = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": request_id}
            yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate_error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )


@app.get("/health")
async def health_check():
    """Health check endpoint (no authentication required)"""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Server information endpoint"""
    return {
        "name": MCP_SERVER_NAME,
        "version": MCP_VERSION,
        "protocol": "MCP",
        "authentication": "Bearer token (prefix optional)"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on port {port} with authentication enabled")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
