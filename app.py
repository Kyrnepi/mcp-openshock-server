
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
import json
import asyncio
import httpx
import os
from typing import Dict, Any, List, Optional
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
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
SHOCK_LIMIT = int(os.getenv("SHOCK_LIMIT", "0"))  # 0 = pas de limite

# Log de démarrage pour vérifier la configuration
logger.info(f"Starting {MCP_SERVER_NAME} v{MCP_VERSION}")
logger.info(f"OpenShock API URL: {OPENSHOCK_API_URL}")
logger.info(f"OpenShock API Token configured: {'Yes' if OPENSHOCK_API_TOKEN else 'No'}")
logger.info(f"MCP Auth Token configured: {'Yes' if MCP_AUTH_TOKEN else 'No'}")
logger.info(f"Debug mode: {'Yes' if DEBUG_MODE else 'No'}")
logger.info(f"Shock intensity limit: {'No limit' if SHOCK_LIMIT == 0 else str(SHOCK_LIMIT)}")

if DEBUG_MODE:
    logger.warning("DEBUG MODE ENABLED - Authentication may be bypassed!")

if SHOCK_LIMIT > 0:
    logger.info(f"SECURITY: Shock intensity will be automatically limited to maximum {SHOCK_LIMIT}")

if not OPENSHOCK_API_TOKEN:
    raise ValueError("OPENSHOCK_API_TOKEN environment variable is required")
if not MCP_AUTH_TOKEN and not DEBUG_MODE:
    raise ValueError("MCP_AUTH_TOKEN environment variable is required")

app = FastAPI(title="OpenShock MCP Server", version=MCP_VERSION)
security = HTTPBearer(auto_error=False)

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

# Middleware pour logging des requêtes
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    
    # Log des headers pour diagnostic
    auth_header = request.headers.get("authorization")
    content_type = request.headers.get("content-type")
    logger.info(f"Authorization header: {'Present' if auth_header else 'Missing'}")
    logger.info(f"Content-Type: {content_type}")
    
    if auth_header and DEBUG_MODE:
        logger.info(f"Auth header value: {auth_header[:20]}..." if len(auth_header) > 20 else auth_header)
    
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

# Authentification avec diagnostic amélioré
async def verify_token_with_debug(request: Request):
    """Vérification du token avec diagnostic détaillé"""
    
    # En mode debug, bypass l'authentification
    if DEBUG_MODE:
        logger.warning("DEBUG MODE: Bypassing authentication")
        return "debug_token"
    
    # Récupération de l'en-tête Authorization
    auth_header = request.headers.get("authorization")
    
    if not auth_header:
        logger.error("No Authorization header found")
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    logger.info(f"Authorization header found: {auth_header[:20]}...")
    
    # Vérification du format Bearer
    if not auth_header.startswith("Bearer "):
        logger.error(f"Invalid auth header format")
        raise HTTPException(status_code=401, detail="Authorization header must start with 'Bearer '")
    
    # Extraction du token
    token = auth_header[7:]  # Retire "Bearer "
    
    logger.info(f"Extracted token: {token[:10]}..." if len(token) > 10 else f"Extracted token: {token}")
    
    # Comparaison des tokens
    if token != MCP_AUTH_TOKEN:
        logger.error("Token mismatch!")
        raise HTTPException(status_code=401, detail="Invalid token")
    
    logger.info("Authentication successful")
    return token

# Client HTTP pour OpenShock API
async def get_openshock_client():
    return httpx.AsyncClient(
        headers={
            "OpenShockToken": OPENSHOCK_API_TOKEN,
            "Content-Type": "application/json"
        },
        timeout=30.0
    )

# Fonction pour calculer la limite d'intensité maximale pour SHOCK
def get_max_shock_intensity():
    """Retourne l'intensité maximale autorisée pour les chocs"""
    if SHOCK_LIMIT == 0:
        return 100  # Pas de limite
    return min(SHOCK_LIMIT, 100)  # Ne peut pas dépasser 100 de toute façon

# Schémas des outils MCP avec intensité requise pour BEEP et limite de shock
def get_tool_schemas():
    """Retourne les schémas des outils avec la limite de shock appliquée"""
    max_shock_intensity = get_max_shock_intensity()
    
    return {
        "SHOCK": {
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
                                "id": {
                                    "type": "string",
                                    "description": "Shocker ID"
                                },
                                "intensity": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 100,
                                    "description": f"Shock intensity (1-100, automatically limited to {max_shock_intensity} if SHOCK_LIMIT is set)"
                                },
                                "duration": {
                                    "type": "integer",
                                    "minimum": 300,
                                    "maximum": 30000,
                                    "description": "Duration in milliseconds (300-30000)"
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
                                    "minimum": 300,
                                    "maximum": 30000,
                                    "description": "Duration in milliseconds (300-30000)"
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
                                "intensity": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 100,
                                    "description": "Beep volume intensity (1-100)",
                                    "default": 50
                                },
                                "duration": {
                                    "type": "integer",
                                    "minimum": 300,
                                    "maximum": 30000,
                                    "description": "Duration in milliseconds (300-30000)"
                                }
                            },
                            "required": ["id", "intensity", "duration"]
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
                                },
                                "intensity": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 0,
                                    "description": "Always 0 for stop commands",
                                    "default": 0
                                },
                                "duration": {
                                    "type": "integer",
                                    "minimum": 300,
                                    "maximum": 300,
                                    "description": "Always 300ms for stop commands", 
                                    "default": 300
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
    "STOP": 0,
    "SHOCK": 1,
    "VIBRATE": 2,
    "BEEP": 3
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
    tool_schemas = get_tool_schemas()
    return {
        "tools": list(tool_schemas.values())
    }

async def handle_tools_call(params: Dict[str, Any]) -> Dict[str, Any]:
    """Exécute un outil avec les paramètres fournis"""
    tool_name = params.get("name")
    tool_arguments = params.get("arguments", {})
    
    logger.info(f"Processing tools/call request for tool: {tool_name}")
    
    tool_schemas = get_tool_schemas()
    if tool_name not in tool_schemas:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    # Validation des paramètres
    if "shockers" not in tool_arguments:
        raise ValueError("Missing 'shockers' parameter")
    
    # Préparation des commandes pour OpenShock API - Structure corrigée
    shocks = []
    max_shock_intensity = get_max_shock_intensity()
    intensity_adjustments = []  # Pour tracker les ajustements
    
    for shocker in tool_arguments["shockers"]:
        shocker_id = shocker.get("id")
        if not shocker_id:
            raise ValueError("Missing shocker ID")
        
        # Structure de base pour toutes les commandes
        shock_request = {
            "id": shocker_id,
            "type": COMMAND_MAPPING[tool_name]
        }
        
        # Gestion spécifique selon le type de commande
        if tool_name == "STOP":
            # STOP utilise toujours intensité 0 et durée courte
            shock_request.update({
                "intensity": 0,
                "duration": 300
            })
        elif tool_name == "SHOCK":
            # SHOCK avec limitation automatique de l'intensité
            intensity = shocker.get("intensity")
            duration = shocker.get("duration")
            if intensity is None or duration is None:
                raise ValueError(f"{tool_name} requires intensity and duration")
            
            # Validation des limites de base
            if intensity < 1 or intensity > 100:
                raise ValueError("Intensity must be between 1 and 100")
            if duration < 300 or duration > 30000:
                raise ValueError("Duration must be between 300 and 30000 milliseconds")
            
            # Application automatique de la limite SHOCK_LIMIT
            original_intensity = intensity
            if SHOCK_LIMIT > 0 and intensity > max_shock_intensity:
                intensity = max_shock_intensity
                intensity_adjustments.append({
                    "shocker_id": shocker_id,
                    "requested": original_intensity,
                    "applied": intensity
                })
                logger.warning(f"SECURITY: Shock intensity for {shocker_id} reduced from {original_intensity} to {intensity} (SHOCK_LIMIT={SHOCK_LIMIT})")
            
            shock_request.update({
                "intensity": intensity,
                "duration": duration
            })
        elif tool_name == "VIBRATE":
            # VIBRATE n'est pas affectée par SHOCK_LIMIT
            intensity = shocker.get("intensity")
            duration = shocker.get("duration")
            if intensity is None or duration is None:
                raise ValueError(f"{tool_name} requires intensity and duration")
            
            # Validation des limites standard
            if intensity < 1 or intensity > 100:
                raise ValueError("Intensity must be between 1 and 100")
            if duration < 300 or duration > 30000:
                raise ValueError("Duration must be between 300 and 30000 milliseconds")
                
            shock_request.update({
                "intensity": intensity,
                "duration": duration
            })
        elif tool_name == "BEEP":
            # BEEP requiert maintenant intensité ET durée
            intensity = shocker.get("intensity", 50)  # Valeur par défaut à 50
            duration = shocker.get("duration")
            
            if duration is None:
                raise ValueError("BEEP requires duration")
            if intensity < 1 or intensity > 100:
                raise ValueError("Intensity must be between 1 and 100")
            if duration < 300 or duration > 30000:
                raise ValueError("Duration must be between 300 and 30000 milliseconds")
                
            shock_request.update({
                "intensity": intensity,
                "duration": duration
            })
        
        shocks.append(shock_request)
    
    # Structure finale corrigée pour l'API OpenShock v2
    api_request = {
        "shocks": shocks,
        "customName": f"MCP-{tool_name}"
    }
    
    logger.info(f"Sending OpenShock API request: {json.dumps(api_request, indent=2)}")
    
    # Envoi de la requête à OpenShock API
    async with await get_openshock_client() as client:
        try:
            response = await client.post(
                f"{OPENSHOCK_API_URL}/2/shockers/control",
                json=api_request
            )
            
            # Log de la réponse pour diagnostic
            logger.info(f"OpenShock API response status: {response.status_code}")
            logger.info(f"OpenShock API response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                response_text = response.text
                logger.error(f"OpenShock API error response: {response_text}")
                
            response.raise_for_status()
            
            try:
                result = response.json()
                logger.info("OpenShock API request successful")
            except:
                # Si la réponse n'est pas du JSON, utiliser le texte
                result = {"message": response.text, "status": "success"}
            
            # Préparer le message de réponse avec les ajustements d'intensité
            success_message = f"Successfully executed {tool_name} command on {len(shocks)} shocker(s)."
            
            if intensity_adjustments:
                success_message += "\n\nSecurity adjustments applied:"
                for adj in intensity_adjustments:
                    success_message += f"\n- Shocker {adj['shocker_id']}: intensity reduced from {adj['requested']} to {adj['applied']} (SHOCK_LIMIT={SHOCK_LIMIT})"
            
            success_message += f"\n\nAPI Response: {json.dumps(result, indent=2)}"
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": success_message
                    }
                ]
            }
            
        except httpx.HTTPError as e:
            logger.error(f"OpenShock API error: {e}")
            
            # Essayer de récupérer plus de détails sur l'erreur
            error_detail = str(e)
            if hasattr(e, 'response') and e.response:
                try:
                    error_response = e.response.json()
                    error_detail = f"{e} - Response: {json.dumps(error_response, indent=2)}"
                except:
                    error_detail = f"{e} - Response text: {e.response.text}"
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error executing {tool_name} command: {error_detail}"
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
    request: Request,
    json_request: JsonRpcRequest
):
    """Endpoint principal MCP avec authentification diagnostique"""
    # Vérification de l'authentification
    await verify_token_with_debug(request)
    
    logger.info(f"MCP endpoint called with method: {json_request.method}")
    response = await process_jsonrpc_request(json_request)
    
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
        "tools": list(get_tool_schemas().keys()),
        "auth_configured": bool(MCP_AUTH_TOKEN),
        "debug_mode": DEBUG_MODE,
        "shock_limit": SHOCK_LIMIT if SHOCK_LIMIT > 0 else "No limit",
        "max_shock_intensity": get_max_shock_intensity(),
        "endpoints": {
            "mcp": "POST /mcp",
            "health": "GET /health",
            "info": "GET /",
            "test-auth": "POST /test-auth"
        }
    }

@app.get("/health")
async def health_check():
    """Endpoint de santé"""
    return {
        "status": "healthy", 
        "server": MCP_SERVER_NAME, 
        "version": MCP_VERSION,
        "shock_limit": SHOCK_LIMIT if SHOCK_LIMIT > 0 else "No limit"
    }

# Endpoint de test sans authentification pour diagnostiquer
@app.post("/test-auth")
async def test_auth(request: Request):
    """Endpoint de test pour diagnostiquer l'authentification"""
    headers = dict(request.headers)
    auth_header = headers.get("authorization", "Not found")
    
    return {
        "message": "Test endpoint reached",
        "headers": headers,
        "auth_header": auth_header,
        "expected_token": f"{MCP_AUTH_TOKEN[:10]}..." if MCP_AUTH_TOKEN else "Not configured",
        "debug_mode": DEBUG_MODE,
        "shock_limit": SHOCK_LIMIT if SHOCK_LIMIT > 0 else "No limit",
        "max_shock_intensity": get_max_shock_intensity(),
        "token_match": auth_header.replace("Bearer ", "") == MCP_AUTH_TOKEN if auth_header.startswith("Bearer ") else False
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
