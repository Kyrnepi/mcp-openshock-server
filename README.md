
# OpenShock MCP Server | Serveur MCP OpenShock

[English](#english) | [Français](#français)

---

## English

MCP (Model Context Protocol) server for controlling OpenShock devices with Bearer token authentication and HTTP streaming support.

### Features

- **Complete MCP Protocol**: Full implementation of MCP standard with JSON-RPC 2.0
- **Available Tools**:
  - `SHOCK`: Send shock commands
  - `VIBRATE`: Send vibration commands  
  - `BEEP`: Send sound/beep commands
  - `STOP`: Stop all commands
- **Bearer Authentication**: Secured with authentication token
- **Streaming Support**: HTTP streaming responses
- **Docker Containerization**: Easy deployment with Docker and docker-compose

### Installation

#### Prerequisites

- Docker and docker-compose
- Valid OpenShock API token

#### Configuration

1. Clone the repository
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Edit the `.env` file with your tokens:
   ```bash
   OPENSHOCK_API_TOKEN=your_openshock_token
   MCP_AUTH_TOKEN=your_secure_mcp_token
   ```

#### Starting with Docker Compose

```bash
docker-compose up -d
```

The server will be accessible at `http://localhost:8000`

#### Starting with Docker

```bash
docker build -t mcp-openshock-server .
docker run -p 8000:8000 \
  -e OPENSHOCK_API_TOKEN=your_token \
  -e MCP_AUTH_TOKEN=your_mcp_token \
  mcp-openshock-server
```

### Usage

#### Authentication

All requests must include the authentication header:
```
Authorization: Bearer your_mcp_token
```

#### Endpoints

- `POST /mcp`: Main MCP endpoint
- `GET /health`: Health check
- `GET /`: Server information

#### MCP Request Examples

##### Initialization
```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {},
  "id": 1
}
```

##### List Tools
```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {},
  "id": 2
}
```

##### Execute Shock
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "SHOCK",
    "arguments": {
      "shockers": [
        {
          "id": "your_shocker_id",
          "intensity": 50,
          "duration": 1000
        }
      ]
    }
  },
  "id": 3
}
```

##### Execute Vibration
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "VIBRATE",
    "arguments": {
      "shockers": [
        {
          "id": "your_shocker_id",
          "intensity": 30,
          "duration": 2000
        }
      ]
    }
  },
  "id": 4
}
```

##### Sound/Beep
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "BEEP",
    "arguments": {
      "shockers": [
        {
          "id": "your_shocker_id",
          "duration": 500
        }
      ]
    }
  },
  "id": 5
}
```

##### Stop
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "STOP",
    "arguments": {
      "shockers": [
        {
          "id": "your_shocker_id"
        }
      ]
    }
  },
  "id": 6
}
```

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENSHOCK_API_TOKEN` | OpenShock API token | ✅ | - |
| `MCP_AUTH_TOKEN` | MCP authentication token | ✅ | - |
| `OPENSHOCK_API_URL` | OpenShock API URL | ❌ | https://api.openshock.app |
| `MCP_SERVER_NAME` | MCP server name | ❌ | openshock-mcp-server |
| `MCP_VERSION` | Server version | ❌ | 1.0.0 |
| `PORT` | Listening port | ❌ | 8000 |

### Security

- ⚠️ **Important**: Keep your tokens secure and never share them
- Use strong and unique MCP tokens
- Consider using HTTPS in production
- Limit network access to the server

### Support and Development

This server implements the MCP protocol according to official specifications and OpenShock API v2.

To report issues or contribute, create an issue in the repository.

---

## Français

Serveur MCP (Model Context Protocol) pour contrôler les dispositifs OpenShock avec authentification Bearer token et support streaming HTTP.

### Fonctionnalités

- **Protocole MCP complet**: Implémentation complète du standard MCP avec JSON-RPC 2.0
- **Outils disponibles**:
  - `SHOCK`: Envoie des commandes de choc
  - `VIBRATE`: Envoie des commandes de vibration  
  - `BEEP`: Envoie des commandes sonores
  - `STOP`: Arrête toutes les commandes
- **Authentification Bearer**: Sécurisation via token d'authentification
- **Support streaming**: Réponses HTTP streamées
- **Containerisation Docker**: Déploiement facile avec Docker et docker-compose

### Installation

#### Prérequis

- Docker et docker-compose
- Token API OpenShock valide

#### Configuration

1. Clonez le repository
2. Copiez `.env.example` vers `.env` :
   ```bash
   cp .env.example .env
   ```
3. Editez le fichier `.env` avec vos tokens :
   ```bash
   OPENSHOCK_API_TOKEN=votre_token_openshock
   MCP_AUTH_TOKEN=votre_token_mcp_securise
   ```

#### Démarrage avec Docker Compose

```bash
docker-compose up -d
```

Le serveur sera accessible sur `http://localhost:8000`

#### Démarrage avec Docker

```bash
docker build -t mcp-openshock-server .
docker run -p 8000:8000 \
  -e OPENSHOCK_API_TOKEN=votre_token \
  -e MCP_AUTH_TOKEN=votre_token_mcp \
  mcp-openshock-server
```

### Utilisation

#### Authentification

Toutes les requêtes doivent inclure l'en-tête d'authentification :
```
Authorization: Bearer votre_token_mcp
```

#### Endpoints

- `POST /mcp` : Endpoint principal MCP
- `GET /health` : Vérification de santé
- `GET /` : Informations sur le serveur

#### Exemples de requêtes MCP

##### Initialisation
```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {},
  "id": 1
}
```

##### Liste des outils
```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {},
  "id": 2
}
```

##### Exécution d'un choc
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "SHOCK",
    "arguments": {
      "shockers": [
        {
          "id": "your_shocker_id",
          "intensity": 50,
          "duration": 1000
        }
      ]
    }
  },
  "id": 3
}
```

##### Exécution d'une vibration
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "VIBRATE",
    "arguments": {
      "shockers": [
        {
          "id": "your_shocker_id",
          "intensity": 30,
          "duration": 2000
        }
      ]
    }
  },
  "id": 4
}
```

##### Son/Beep
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "BEEP",
    "arguments": {
      "shockers": [
        {
          "id": "your_shocker_id",
          "duration": 500
        }
      ]
    }
  },
  "id": 5
}
```

##### Arrêt
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "STOP",
    "arguments": {
      "shockers": [
        {
          "id": "your_shocker_id"
        }
      ]
    }
  },
  "id": 6
}
```

### Variables d'environnement

| Variable | Description | Requis | Défaut |
|----------|-------------|---------|---------|
| `OPENSHOCK_API_TOKEN` | Token API OpenShock | ✅ | - |
| `MCP_AUTH_TOKEN` | Token d'authentification MCP | ✅ | - |
| `OPENSHOCK_API_URL` | URL de l'API OpenShock | ❌ | https://api.openshock.app |
| `MCP_SERVER_NAME` | Nom du serveur MCP | ❌ | openshock-mcp-server |
| `MCP_VERSION` | Version du serveur | ❌ | 1.0.0 |
| `PORT` | Port d'écoute | ❌ | 8000 |

### Sécurité

- ⚠️ **Important** : Gardez vos tokens sécurisés et ne les partagez jamais
- Utilisez des tokens MCP forts et uniques
- Considérez l'utilisation de HTTPS en production
- Limitez l'accès réseau au serveur

### Support et développement

Ce serveur implémente le protocole MCP selon les spécifications officielles et l'API OpenShock v2.

Pour signaler des problèmes ou contribuer, créez une issue dans le repository.
