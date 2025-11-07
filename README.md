# OpenShock MCP Server | Serveur MCP OpenShock

[English](#english) | [Français](#français)

---

## English

A Model Context Protocol (MCP) server for controlling OpenShock devices, built with the official Python MCP SDK. Features automatic shock intensity limiting and secure HTTP-based communication.

### Features

- **Official MCP SDK**: Built using the official `mcp` Python package from Anthropic
- **Complete MCP Protocol**: Full implementation of MCP standard with proper tool definitions
- **Available Tools**:
  - `SHOCK`: Send shock commands with automatic intensity limiting
  - `VIBRATE`: Send vibration commands
  - `BEEP`: Send sound/beep commands
  - `STOP`: Stop all commands
- **Safety Features**: Automatic shock intensity limiting via `SHOCK_LIMIT` environment variable
- **HTTP/SSE Transport**: Modern HTTP-based MCP server with Server-Sent Events support
- **Connection Pooling**: Efficient HTTP client connection management
- **Docker Support**: Easy deployment with Docker and docker-compose

### Architecture

This server uses:
- **FastMCP** from the official `mcp` Python SDK for MCP protocol handling
- **FastAPI** for HTTP transport layer
- **HTTPX** for async HTTP client with connection pooling
- **OpenShock API v2** for device control

### Installation

#### Prerequisites

- Docker and docker-compose (recommended)
- OR Python 3.11+ with pip
- Valid OpenShock API token

#### Configuration

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd openshock-mcp-server
   ```

2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file with your configuration:
   ```bash
   OPENSHOCK_API_TOKEN=your_openshock_token_here
   MCP_AUTH_TOKEN=your_secure_mcp_token_here
   SHOCK_LIMIT=50  # Optional: limit shock intensity (0 = no limit)
   ```

#### Starting with Docker Compose (Recommended)

```bash
docker-compose up -d
```

The server will be accessible at `http://localhost:8000`

#### Starting with Docker

```bash
docker build -t openshock-mcp-server .
docker run -p 8000:8000 \
  -e OPENSHOCK_API_TOKEN=your_token \
  -e MCP_AUTH_TOKEN=your_mcp_token \
  -e SHOCK_LIMIT=50 \
  openshock-mcp-server
```

#### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENSHOCK_API_TOKEN=your_token
export MCP_AUTH_TOKEN=your_mcp_token
export SHOCK_LIMIT=50

# Run the server
python app.py
```

### Usage

#### MCP Client Connection

Connect your MCP client to `http://localhost:8000` using HTTP/SSE transport.

**Authentication Required:** All requests must include the authentication token in the `Authorization` header. The `Bearer` prefix is optional for MCP client compatibility:

```
Authorization: Bearer your_mcp_auth_token
```
or
```
Authorization: your_mcp_auth_token
```

The `/health` endpoint is publicly accessible without authentication.

#### Available MCP Tools

##### 1. SHOCK
Send shock commands with automatic intensity limiting.

**Parameters:**
- `shockers` (list): List of shocker configurations
  - `id` (string): Shocker ID
  - `intensity` (integer): Shock intensity 1-100 (automatically limited by SHOCK_LIMIT)
  - `duration` (integer): Duration in milliseconds (300-30000)

**Example:**
```json
{
  "name": "SHOCK",
  "arguments": {
    "shockers": [
      {
        "id": "your_shocker_id",
        "intensity": 80,
        "duration": 1000
      }
    ]
  }
}
```

If `SHOCK_LIMIT=50`, the intensity will be automatically reduced to 50.

##### 2. VIBRATE
Send vibration commands (not affected by SHOCK_LIMIT).

**Parameters:**
- `shockers` (list): List of shocker configurations
  - `id` (string): Shocker ID
  - `intensity` (integer): Vibration intensity 1-100
  - `duration` (integer): Duration in milliseconds (300-30000)

**Example:**
```json
{
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
}
```

##### 3. BEEP
Send beep/sound commands.

**Parameters:**
- `shockers` (list): List of shocker configurations
  - `id` (string): Shocker ID
  - `intensity` (integer): Beep volume intensity 1-100 (defaults to 50)
  - `duration` (integer): Duration in milliseconds (300-30000)

**Example:**
```json
{
  "name": "BEEP",
  "arguments": {
    "shockers": [
      {
        "id": "your_shocker_id",
        "intensity": 50,
        "duration": 500
      }
    ]
  }
}
```

##### 4. STOP
Stop all commands on specified shockers.

**Parameters:**
- `shockers` (list): List of shockers to stop
  - `id` (string): Shocker ID

**Example:**
```json
{
  "name": "STOP",
  "arguments": {
    "shockers": [
      {
        "id": "your_shocker_id"
      }
    ]
  }
}
```

### Safety Features

#### SHOCK_LIMIT

The `SHOCK_LIMIT` environment variable provides automatic safety limiting for shock commands:

- `SHOCK_LIMIT=0`: No limit (default behavior)
- `SHOCK_LIMIT=50`: Automatically limits shock intensity to maximum 50
- `SHOCK_LIMIT=25`: Automatically limits shock intensity to maximum 25

**Behavior:**
- Commands with intensity higher than `SHOCK_LIMIT` are **not rejected**
- The intensity is **automatically reduced** to the configured limit
- The response includes details about the adjustment
- All adjustments are logged for security audit

**Note**: Only `SHOCK` commands are affected by `SHOCK_LIMIT`. `VIBRATE` and `BEEP` commands are not limited.

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENSHOCK_API_TOKEN` | OpenShock API token | ✅ Yes | - |
| `MCP_AUTH_TOKEN` | MCP authentication token (sent in Authorization header, Bearer prefix optional) | ✅ Yes | - |
| `SHOCK_LIMIT` | Maximum shock intensity (0 = no limit) | ❌ No | 0 |
| `OPENSHOCK_API_URL` | OpenShock API URL | ❌ No | https://api.openshock.app |
| `MCP_SERVER_NAME` | MCP server name | ❌ No | openshock-mcp-server |
| `MCP_VERSION` | Server version | ❌ No | 2.0.1 |
| `PORT` | Listening port | ❌ No | 8000 |

### Health Check

The server provides a health check endpoint at `/health`:

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy"
}
```

### Security Best Practices

- ⚠️ **Token Security**: Keep both `OPENSHOCK_API_TOKEN` and `MCP_AUTH_TOKEN` secure and never commit them to version control
- 🔑 **Strong Tokens**: Use strong, randomly generated tokens for `MCP_AUTH_TOKEN` (e.g., UUID or 32+ character random strings)
- 🔒 **HTTPS in Production**: Always use HTTPS/TLS in production environments
- 🎯 **Configure SHOCK_LIMIT**: Set an appropriate `SHOCK_LIMIT` according to your safety requirements
- 🔐 **Network Security**: Limit network access to the server using firewalls
- 📊 **Audit Logging**: All intensity adjustments and authentication failures are logged for security audit purposes

### Troubleshooting

#### Server won't start
- Verify `OPENSHOCK_API_TOKEN` is set correctly
- Check logs with `docker-compose logs -f` (Docker) or console output (local)

#### Commands not working
- Verify shocker IDs are correct
- Check OpenShock API token has appropriate permissions
- Review logs for error messages

#### Connection issues
- Ensure the server is accessible at the configured port
- Check firewall rules
- Verify MCP client is configured for HTTP/SSE transport

### Development

This server is built using:
- [Model Context Protocol](https://modelcontextprotocol.io/) - The MCP specification
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Official Python implementation
- [OpenShock API](https://openshock.app/) - OpenShock device control API

To contribute or report issues, please use the GitHub repository.

### Version History

**v2.0.1** (Current)
- **Security Fix**: Re-implemented authentication (v2.0.0 had critical vulnerability)
- Bearer token authentication using middleware
- All endpoints require authentication except `/health`

**v2.0.0** (DO NOT USE - Security Issue)
- Complete rewrite using official MCP Python SDK
- **CRITICAL BUG**: Authentication was accidentally removed
- Added HTTP client connection pooling
- Better error handling
- Full English codebase with bilingual documentation

**v1.0.0**
- Initial release with custom MCP implementation

---

## Français

Un serveur Model Context Protocol (MCP) pour contrôler les dispositifs OpenShock, construit avec le SDK Python MCP officiel. Inclut une limitation automatique de l'intensité des chocs et une communication sécurisée basée sur HTTP.

### Fonctionnalités

- **SDK MCP Officiel**: Construit avec le package Python `mcp` officiel d'Anthropic
- **Protocole MCP Complet**: Implémentation complète du standard MCP avec définitions d'outils appropriées
- **Outils disponibles**:
  - `SHOCK`: Envoie des commandes de choc avec limitation automatique d'intensité
  - `VIBRATE`: Envoie des commandes de vibration
  - `BEEP`: Envoie des commandes sonores
  - `STOP`: Arrête toutes les commandes
- **Fonctionnalités de Sécurité**: Limitation automatique de l'intensité des chocs via la variable `SHOCK_LIMIT`
- **Transport HTTP/SSE**: Serveur MCP moderne basé sur HTTP avec support Server-Sent Events
- **Pool de Connexions**: Gestion efficace des connexions HTTP client
- **Support Docker**: Déploiement facile avec Docker et docker-compose

### Architecture

Ce serveur utilise :
- **FastMCP** du SDK Python `mcp` officiel pour la gestion du protocole MCP
- **FastAPI** pour la couche de transport HTTP
- **HTTPX** pour le client HTTP asynchrone avec pool de connexions
- **API OpenShock v2** pour le contrôle des dispositifs

### Installation

#### Prérequis

- Docker et docker-compose (recommandé)
- OU Python 3.11+ avec pip
- Token API OpenShock valide

#### Configuration

1. Clonez le dépôt :
   ```bash
   git clone <repository-url>
   cd openshock-mcp-server
   ```

2. Copiez `.env.example` vers `.env` :
   ```bash
   cp .env.example .env
   ```

3. Éditez le fichier `.env` avec votre configuration :
   ```bash
   OPENSHOCK_API_TOKEN=votre_token_openshock
   MCP_AUTH_TOKEN=votre_token_mcp_securise
   SHOCK_LIMIT=50  # Optionnel: limite l'intensité des chocs (0 = pas de limite)
   ```

#### Démarrage avec Docker Compose (Recommandé)

```bash
docker-compose up -d
```

Le serveur sera accessible sur `http://localhost:8000`

#### Démarrage avec Docker

```bash
docker build -t openshock-mcp-server .
docker run -p 8000:8000 \
  -e OPENSHOCK_API_TOKEN=votre_token \
  -e MCP_AUTH_TOKEN=votre_token_mcp \
  -e SHOCK_LIMIT=50 \
  openshock-mcp-server
```

#### Développement Local

```bash
# Installer les dépendances
pip install -r requirements.txt

# Définir les variables d'environnement
export OPENSHOCK_API_TOKEN=votre_token
export MCP_AUTH_TOKEN=votre_token_mcp
export SHOCK_LIMIT=50

# Lancer le serveur
python app.py
```

### Utilisation

#### Connexion Client MCP

Connectez votre client MCP à `http://localhost:8000` en utilisant le transport HTTP/SSE.

**Authentification Requise:** Toutes les requêtes doivent inclure le token d'authentification dans le header `Authorization`. Le préfixe `Bearer` est optionnel pour la compatibilité avec les clients MCP :

```
Authorization: Bearer votre_token_mcp
```
ou
```
Authorization: votre_token_mcp
```

Le endpoint `/health` est accessible publiquement sans authentification.

#### Outils MCP Disponibles

##### 1. SHOCK
Envoie des commandes de choc avec limitation automatique d'intensité.

**Paramètres:**
- `shockers` (liste): Liste des configurations de shockers
  - `id` (string): ID du shocker
  - `intensity` (integer): Intensité du choc 1-100 (automatiquement limitée par SHOCK_LIMIT)
  - `duration` (integer): Durée en millisecondes (300-30000)

**Exemple:**
```json
{
  "name": "SHOCK",
  "arguments": {
    "shockers": [
      {
        "id": "votre_id_shocker",
        "intensity": 80,
        "duration": 1000
      }
    ]
  }
}
```

Si `SHOCK_LIMIT=50`, l'intensité sera automatiquement réduite à 50.

##### 2. VIBRATE
Envoie des commandes de vibration (non affectée par SHOCK_LIMIT).

**Paramètres:**
- `shockers` (liste): Liste des configurations de shockers
  - `id` (string): ID du shocker
  - `intensity` (integer): Intensité de vibration 1-100
  - `duration` (integer): Durée en millisecondes (300-30000)

**Exemple:**
```json
{
  "name": "VIBRATE",
  "arguments": {
    "shockers": [
      {
        "id": "votre_id_shocker",
        "intensity": 30,
        "duration": 2000
      }
    ]
  }
}
```

##### 3. BEEP
Envoie des commandes sonores.

**Paramètres:**
- `shockers` (liste): Liste des configurations de shockers
  - `id` (string): ID du shocker
  - `intensity` (integer): Intensité du volume sonore 1-100 (par défaut 50)
  - `duration` (integer): Durée en millisecondes (300-30000)

**Exemple:**
```json
{
  "name": "BEEP",
  "arguments": {
    "shockers": [
      {
        "id": "votre_id_shocker",
        "intensity": 50,
        "duration": 500
      }
    ]
  }
}
```

##### 4. STOP
Arrête toutes les commandes sur les shockers spécifiés.

**Paramètres:**
- `shockers` (liste): Liste des shockers à arrêter
  - `id` (string): ID du shocker

**Exemple:**
```json
{
  "name": "STOP",
  "arguments": {
    "shockers": [
      {
        "id": "votre_id_shocker"
      }
    ]
  }
}
```

### Fonctionnalités de Sécurité

#### SHOCK_LIMIT

La variable d'environnement `SHOCK_LIMIT` fournit une limitation automatique de sécurité pour les commandes de choc :

- `SHOCK_LIMIT=0`: Pas de limite (comportement par défaut)
- `SHOCK_LIMIT=50`: Limite automatiquement l'intensité des chocs à 50 maximum
- `SHOCK_LIMIT=25`: Limite automatiquement l'intensité des chocs à 25 maximum

**Comportement:**
- Les commandes avec une intensité supérieure à `SHOCK_LIMIT` ne sont **pas rejetées**
- L'intensité est **automatiquement réduite** à la limite configurée
- La réponse inclut les détails de l'ajustement
- Tous les ajustements sont enregistrés pour audit de sécurité

**Note**: Seules les commandes `SHOCK` sont affectées par `SHOCK_LIMIT`. Les commandes `VIBRATE` et `BEEP` ne sont pas limitées.

### Variables d'Environnement

| Variable | Description | Requis | Défaut |
|----------|-------------|--------|--------|
| `OPENSHOCK_API_TOKEN` | Token API OpenShock | ✅ Oui | - |
| `MCP_AUTH_TOKEN` | Token d'authentification MCP (envoyé dans le header Authorization, préfixe Bearer optionnel) | ✅ Oui | - |
| `SHOCK_LIMIT` | Intensité maximale des chocs (0 = pas de limite) | ❌ Non | 0 |
| `OPENSHOCK_API_URL` | URL de l'API OpenShock | ❌ Non | https://api.openshock.app |
| `MCP_SERVER_NAME` | Nom du serveur MCP | ❌ Non | openshock-mcp-server |
| `MCP_VERSION` | Version du serveur | ❌ Non | 2.0.1 |
| `PORT` | Port d'écoute | ❌ Non | 8000 |

### Vérification de Santé

Le serveur fournit un endpoint de vérification de santé à `/health` :

```bash
curl http://localhost:8000/health
```

Réponse :
```json
{
  "status": "healthy"
}
```

### Bonnes Pratiques de Sécurité

- ⚠️ **Sécurité des Tokens**: Gardez à la fois `OPENSHOCK_API_TOKEN` et `MCP_AUTH_TOKEN` sécurisés et ne les commitez jamais dans le contrôle de version
- 🔑 **Tokens Forts**: Utilisez des tokens forts et générés aléatoirement pour `MCP_AUTH_TOKEN` (ex: UUID ou chaînes aléatoires de 32+ caractères)
- 🔒 **HTTPS en Production**: Utilisez toujours HTTPS/TLS dans les environnements de production
- 🎯 **Configurer SHOCK_LIMIT**: Définissez un `SHOCK_LIMIT` approprié selon vos exigences de sécurité
- 🔐 **Sécurité Réseau**: Limitez l'accès réseau au serveur avec des pare-feu
- 📊 **Journalisation d'Audit**: Tous les ajustements d'intensité et échecs d'authentification sont enregistrés à des fins d'audit de sécurité

### Dépannage

#### Le serveur ne démarre pas
- Vérifiez que `OPENSHOCK_API_TOKEN` est correctement défini
- Consultez les logs avec `docker-compose logs -f` (Docker) ou la sortie console (local)

#### Les commandes ne fonctionnent pas
- Vérifiez que les IDs des shockers sont corrects
- Vérifiez que le token API OpenShock a les permissions appropriées
- Consultez les logs pour les messages d'erreur

#### Problèmes de connexion
- Assurez-vous que le serveur est accessible sur le port configuré
- Vérifiez les règles de pare-feu
- Vérifiez que le client MCP est configuré pour le transport HTTP/SSE

### Développement

Ce serveur est construit avec :
- [Model Context Protocol](https://modelcontextprotocol.io/) - La spécification MCP
- [SDK Python MCP](https://github.com/modelcontextprotocol/python-sdk) - Implémentation Python officielle
- [API OpenShock](https://openshock.app/) - API de contrôle des dispositifs OpenShock

Pour contribuer ou signaler des problèmes, veuillez utiliser le dépôt GitHub.

### Historique des Versions

**v2.0.1** (Actuel)
- **Correction de Sécurité**: Ré-implémentation de l'authentification (v2.0.0 avait une vulnérabilité critique)
- Authentification par token Bearer utilisant un middleware
- Tous les endpoints nécessitent l'authentification sauf `/health`

**v2.0.0** (NE PAS UTILISER - Problème de Sécurité)
- Réécriture complète utilisant le SDK Python MCP officiel
- **BUG CRITIQUE**: L'authentification a été accidentellement supprimée
- Ajout du pool de connexions client HTTP
- Meilleure gestion des erreurs
- Code entièrement en anglais avec documentation bilingue

**v1.0.0**
- Version initiale avec implémentation MCP personnalisée
