# Changelog

All notable changes to this project will be documented in this file.

## [2.0.1] - 2025-11-07

### Security Fix - Critical

**IMPORTANT:** Version 2.0.0 had a critical security issue where authentication was accidentally removed. This version restores authentication.

### Added
- Re-implemented Bearer token authentication using Starlette middleware
- `MCP_AUTH_TOKEN` environment variable (required)
- Authentication logging for failed attempts
- Optional Bearer prefix in Authorization header for MCP client compatibility

### Changed
- All MCP endpoints now require token authentication (except `/health`)
- Bearer prefix is optional in Authorization header (supports both `Bearer token` and `token` formats)
- Updated documentation to reflect authentication requirements
- Version bumped to 2.0.1

### Security
- **FIXED CRITICAL**: Version 2.0.0 removed authentication completely, leaving the server open to anyone
- Authentication middleware now properly validates Bearer tokens
- Health check endpoint remains publicly accessible
- All authentication failures are logged

### Migration from 2.0.0
If you deployed version 2.0.0, **upgrade immediately** as the server was completely open without authentication.

1. Set `MCP_AUTH_TOKEN` environment variable
2. Update your `.env` file or docker-compose configuration
3. Restart the server
4. Configure your MCP client to send authentication:
   - Standard: `Authorization: Bearer <token>`
   - Direct: `Authorization: <token>` (Bearer prefix optional)

---

## [2.0.0] - 2025-11-07 [SECURITY ISSUE - DO NOT USE]

**⚠️ WARNING: This version has a critical security vulnerability. Use 2.0.1 instead.**

### Major Refactoring

This version represents a complete rewrite of the OpenShock MCP Server to use the official MCP Python SDK and address multiple security and code quality issues.

### Added
- Official MCP Python SDK (`mcp` package v1.2.1) integration using FastMCP
- HTTP client connection pooling for improved performance
- Comprehensive bilingual documentation (English/French) in README
- `SHOCK_LIMIT` configuration in docker-compose.yml
- Missing configuration variables in .env.example
- Version history section in README
- This CHANGELOG.md file

### Changed
- **Complete rewrite of app.py** (616 lines → 345 lines, -44% code reduction)
  - Now uses FastMCP from official MCP SDK instead of custom JSON-RPC implementation
  - Simplified tool definitions using decorators
  - Better code organization and maintainability
- **All code comments translated from French to English**
  - app.py: All comments now in English
  - Dockerfile: Comments translated
  - .gitignore: Comments translated
- **README.md completely restructured**
  - Improved English documentation
  - Updated French documentation to match
  - Added architecture section
  - Added troubleshooting section
  - Updated examples to reflect new SDK usage
- Updated requirements.txt to include MCP SDK
- Updated .env.example with SHOCK_LIMIT configuration
- Updated docker-compose.yml to include SHOCK_LIMIT with default value
- Version bumped from 1.0.0 to 2.0.0

### Removed
- **Security vulnerabilities fixed:**
  - Removed DEBUG_MODE bypass that completely disabled authentication
  - Removed token logging that exposed partial authentication tokens
  - Removed /test-auth endpoint that leaked sensitive configuration
- **Code quality improvements:**
  - Removed manual JSON-RPC implementation (now handled by SDK)
  - Removed custom streaming response generation
  - Removed bare `except:` clause (line 457 in old code)
  - Removed manual authentication middleware
  - Removed inefficient HTTP client creation per request

### Fixed
- Exception handling now properly specific instead of catching all exceptions
- HTTP client now uses connection pooling instead of creating new client per request
- SHOCK_LIMIT properly configured in all deployment methods
- Better error messages and logging

### Technical Details

**Before (v1.0.0):**
- 616 lines of code
- Custom JSON-RPC 2.0 implementation
- Manual MCP protocol handling
- French comments throughout
- Multiple security vulnerabilities
- No connection pooling

**After (v2.0.0):**
- 345 lines of code (-44%)
- Official MCP SDK (FastMCP)
- Automatic protocol compliance
- Full English codebase
- Security issues resolved
- HTTP connection pooling

**SECURITY NOTE:** This version accidentally removed authentication entirely. Fixed in 2.0.1.

### Migration Guide

**DO NOT USE 2.0.0 - Upgrade to 2.0.1 instead**

If upgrading from v1.0.0 to 2.0.1:

1. **Update requirements:** The MCP SDK is now required
   ```bash
   pip install -r requirements.txt
   ```

2. **Update authentication:** `DEBUG_MODE` is removed, but `MCP_AUTH_TOKEN` is still required

3. **Add SHOCK_LIMIT (optional):** Add to your .env if you want intensity limiting
   ```bash
   SHOCK_LIMIT=50
   ```

4. **Rebuild Docker image:** If using Docker
   ```bash
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

5. **Update MCP client configuration:** The server still uses HTTP/SSE transport on the same port (8000), so no client changes should be needed

### Compatibility

- Python 3.11+ required (no change)
- Docker / docker-compose compatible (no change)
- OpenShock API v2 (no change)
- MCP Protocol 2024-11-05 (no change)

### Links

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [OpenShock API](https://openshock.app/)

---

## [1.0.0] - 2024

### Initial Release

- Custom MCP protocol implementation
- Basic tool support (SHOCK, VIBRATE, BEEP, STOP)
- SHOCK_LIMIT safety feature
- Docker support
- Bilingual README
