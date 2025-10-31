
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
import json
import asyncio
import httpx
import os
from typing import Dict, Any, List
import logging
from pydantic import BaseModel
import uvicorn

# Configuration du logging plus détaillé
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration depuis les variables d'environnement
OPENSHOCK_API_URL = os.getenv("OPENSHOCK_API_URL", "https://api.openshock.app")
OPENSHOCK_API_TOKEN = os.getenv("OPENSHOCK_API_TOKEN")
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN")
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "openshock-mcp-server")
MCP_VERSION = os.getenv("MCP_VERSION", "1.0.0")

# Log de démarrage pour vérifier la configuration
logger.info(f"Starting {MCP_SERVER_NAME} v{MCP_VERSION}")
logger.info(f"OpenShock API URL: {OPENSHOCK_API_URL}")
logger.info(f"OpenShock API Token configured: {'Yes' if OPENSHOCK_API_TOKEN else 'No'}")
logger.info(f"MCP Auth Token configured: {'Yes' if MCP_AUTH_TOKEN else 'No'}")

if not OPENSHOCK_API_TOKEN:
    raise ValueError("OPENSHOCK_API_TOKEN environment variable is required")
if not MCP_AUTH_TOKEN:
    raise ValueError("MCP_AUTH_TOKEN environment variable is required")

app = FastAPI(title="OpenShock MCP Server", version=MCP_VERSION)
security = HTTPBearer()

# Modèles Pydantic pour la validation
class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = {}
    id: int | str | None = None

class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Dict[str, Any] | None = None
    error: Dict[str, Any] | None = None
    id: int | str | None = None

class ControlParams(BaseModel):
    shockers: List[Dict[str, Any]]

# Authentification avec logging amélioré
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    logger.info(f"Received token: {credentials.credentials[:10]}..." if credentials.credentials else "No token")
    logger.info(f"Expected token: {MCP_AUTH_TOKEN[:10]}..." if MCP_AUTH_TOKEN else "No expected token")
    
    if credentials.credentials != MCP_AUTH_TOKEN:
        logger.warning(f"Authentication failed - tokens don't match")
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    logger.info("Authentication successful")
    return credentials.credentials

# Client HTTP pour OpenShock API
async def get_openshock_client():
    return httpx.AsyncClient(
        headers={
            "OpenShockToken": OPENSHOCK_API_TOKEN,
            "Content-Type": "application/json"
        },
        timeout=30.0
    )

# Schémas des outils MCP
TOOL_SCHEMAS = {
    "SHOCK": {
        "name": "SHOCK",
        "description": "Send shock command to OpenShock devices",
        "inputSchema": {
            "type": "object",
            "properties": {
                "shockers": {
                    "type": "array",
                    "description": "List of shockers to control",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Shocker ID"
                            },
                            "intensity": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100,
                                "description": "Shock intensity (1-100)"
                            },
                            "duration": {
                                "type": "integer",
                                "minimum": 100,
                                "maximum": 5000,
                                "description": "Duration in milliseconds (100-5000)"
                            }
                        },
                        "required": ["id", "intensity", "duration"]
                    }
                }
            },
            "required": ["shockers"]
        }
    },
    "VIBRATE": {
        "name": "VIBRATE",
        "description": "Send vibrate command to OpenShock devices",
        "inputSchema": {
            "type": "object",
            "properties": {
                "shockers": {
                    "type": "array",
                    "description": "List of shockers to control",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Shocker ID"
                            },
                            "intensity": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100,
                                "description": "Vibration intensity (1-100)"
                            },
                            "duration": {
                                "type": "integer",
                                "minimum": 100,
                                "maximum": 5000,
                                "description": "Duration in milliseconds (100-5000)"
                            }
                        },
                        "required": ["id", "intensity", "duration"]
                    }
                }
            },
            "required": ["shockers"]
        }
    },
    "BEEP": {
        "name": "BEEP",
        "description": "Send beep/sound command to OpenShock devices",
        "inputSchema": {
            "type": "object",
            "properties": {
                "shockers": {
                    "type": "array",
                    "description": "List of shockers to control",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Shocker ID"
                            },
                            "duration": {
                                "type": "integer",
                                "minimum": 100,
                                "maximum": 5000,
                                "description": "Duration in milliseconds (100-5000)"
                            }
                        },
                        "required": ["id", "duration"]
                    }
                }
            },
            "required": ["shockers"]
        }
    },
    "STOP": {
        "name": "STOP",
        "description": "Stop all commands on OpenShock devices",
        "inputSchema": {
            "type": "object",
            "properties": {
                "shockers": {
                    "type": "array",
                    "description": "List of shocker IDs to stop",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Shocker ID"
                            }
                        },
                        "required": ["id"]
                    }
                }
            },
            "required": ["shockers"]
        }
    }
}

# Mappage des commandes MCP vers OpenShock API
COMMAND_MAPPING = {
    "SHOCK": 1,
    "VIBRATE": 2,
    "BEEP": 3,
    "STOP": 0
}

async def handle_initialize(params: Dict[str, Any]) -> Dict[str, Any]:
    """Gère la requête d'initialisation MCP"""
    logger.info("Processing initialize request")
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {
                "listChanged": False
            }
        },
        "serverInfo": {
            "name": MCP_SERVER_NAME,
            "version": MCP_VERSION
        }
    }

async def handle_tools_list(params: Dict[str, Any]) -> Dict[str, Any]:
    """Liste les outils disponibles"""
    logger.info("Processing tools/list request")
    return {
        "tools": list(TOOL_SCHEMAS.values())
    }

async def handle_tools_call(params: Dict[str, Any]) -> Dict[str, Any]:
    """Exécute un outil avec les paramètres fournis"""
    tool_name = params.get("name")
    tool_arguments = params.get("arguments", {})
    
    logger.info(f"Processing tools/call request for tool: {tool_name}")
    
    if tool_name not in TOOL_SCHEMAS:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    # Validation des paramètres
    if "shockers" not in tool_arguments:
        raise ValueError("Missing 'shockers' parameter")
    
    # Préparation de la requête OpenShock
    control_requests = []
    
    for shocker in tool_arguments["shockers"]:
        shocker_id = shocker.get("id")
        if not shocker_id:
            raise ValueError("Missing shocker ID")
        
        control_request = {
            "id": shocker_id,
            "type": COMMAND_MAPPING[tool_name]
        }
        
        # Ajout des paramètres selon le type de commande
        if tool_name in ["SHOCK", "VIBRATE"]:
            intensity = shocker.get("intensity")
            duration = shocker.get("duration")
            if intensity is None or duration is None:
                raise ValueError(f"{tool_name} requires intensity and duration")
            control_request.update({
                "intensity": intensity,
                "duration": duration
            })
        elif tool_name == "BEEP":
            duration = shocker.get("duration")
            if duration is None:
                raise ValueError("BEEP requires duration")
            control_request["duration"] = duration
        
        control_requests.append(control_request)
    
    logger.info(f"Sending {len(control_requests)} control requests to OpenShock API")
    
    # Envoi de la requête à OpenShock API
    async with await get_openshock_client() as client:
        try:
            response = await client.post(
                f"{OPENSHOCK_API_URL}/2/shockers/control",
                json=control_requests
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info("OpenShock API request successful")
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Successfully executed {tool_name} command on {len(control_requests)} shocker(s). Response: {json.dumps(result, indent=2)}"
                    }
                ]
            }
            
        except httpx.HTTPError as e:
            logger.error(f"OpenShock API error: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error executing {tool_name} command: {str(e)}"
                    }
                ],
                "isError": True
            }

# Gestionnaires de méthodes MCP
METHOD_HANDLERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call
}

async def process_jsonrpc_request(request: JsonRpcRequest) -> JsonRpcResponse:
    """Traite une requête JSON-RPC selon le protocole MCP"""
    try:
        logger.info(f"Processing JSON-RPC request: {request.method}")
        handler = METHOD_HANDLERS.get(request.method)
        if not handler:
            logger.warning(f"Unknown method: {request.method}")
            return JsonRpcResponse(
                error={
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                },
                id=request.id
            )
        
        result = await handler(request.params)
        logger.info(f"Request {request.method} processed successfully")
        return JsonRpcResponse(result=result, id=request.id)
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return JsonRpcResponse(
            error={
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            id=request.id
        )

async def generate_stream_response(response: JsonRpcResponse):
    """Génère une réponse streamée"""
    response_json = response.model_dump(exclude_none=True)
    yield f"data: {json.dumps(response_json)}\n\n"

@app.post("/mcp")
async def mcp_endpoint(
    request: JsonRpcRequest,
    token: str = Depends(verify_token)
):
    """Endpoint principal MCP avec support streaming"""
    logger.info(f"MCP endpoint called with method: {request.method}")
    response = await process_jsonrpc_request(request)
    
    return StreamingResponse(
        generate_stream_response(response),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@app.get("/")
async def root():
    """Endpoint racine avec informations sur le serveur"""
    return {
        "name": MCP_SERVER_NAME,
        "version": MCP_VERSION,
        "protocol": "MCP",
        "tools": list(TOOL_SCHEMAS.keys()),
        "auth_configured": bool(MCP_AUTH_TOKEN),
        "endpoints": {
            "mcp": "POST /mcp",
            "health": "GET /health",
            "info": "GET /"
        }
    }

@app.get("/health")
async def health_check():
    """Endpoint de santé"""
    return {"status": "healthy", "server": MCP_SERVER_NAME, "version": MCP_VERSION}

# Endpoint de test sans authentification pour diagnostiquer
@app.post("/test-auth")
async def test_auth(request: Request):
    """Endpoint de test pour diagnostiquer l'authentification"""
    headers = dict(request.headers)
    return {
        "message": "Test endpoint reached",
        "headers": headers,
        "auth_header": headers.get("authorization", "Not found"),
        "expected_token": f"{MCP_AUTH_TOKEN[:10]}..." if MCP_AUTH_TOKEN else "Not configured"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
