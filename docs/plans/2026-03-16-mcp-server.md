# Implementation Plan — Feature #18: MCP Server

**Feature**: MCP Server (FR-013)
**Date**: 2026-03-16
**Status**: Draft

## Overview

Expose `search_code_context` tool via MCP protocol with stdio and HTTP SSE transport.

## Architecture

- **MCPServer**: Main class implementing MCP protocol
- **Transport**: stdio (local) + HTTP SSE (remote)
- **Tool**: `search_code_context(query, repo?, language?, api_key)`

## Implementation Steps

### Step 1: Create MCP Server Module
- Create `src/query/mcp.py`
- Implement `MCPServer` class
- Implement `search_code_context` tool callback

### Step 2: Implement Tool Parameters
- `query` (required): str - natural language or symbol query
- `repo` (optional): str - repository name filter
- `language` (optional): str - programming language filter
- `api_key` (required): str - API key for authentication

### Step 3: Error Handling
- Return MCP-compliant error responses for:
  - Missing required parameters → `invalid_params`
  - Invalid API key → `unauthorized`
  - Validation errors → `invalid_params` with details

### Step 4: Transport Support
- **stdio**: For local AI agent integration
- **HTTP SSE**: For remote agent integration

### Step 5: Integration with Existing Components
- Use `QueryHandler` for query processing
- Use `AuthMiddleware.verify_api_key()` for auth
- Return structured results matching QueryResponse

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/query/mcp.py` | Create - MCPServer implementation |
| `src/query/__init__.py` | Modify - export MCPServer |
| `tests/test_mcp.py` | Create - unit tests |

## Acceptance Criteria (from feature-list.json)

1. Given valid MCP tool-call request with query and api_key, when processed, then structured context results returned as MCP tool response
2. Given malformed MCP request missing required parameters, when received, then MCP-compliant error response with missing fields indication
3. Given MCP client connected via stdio, when tool call is sent, then response is received via same transport
4. Given MCP client connected via HTTP SSE, when tool call is sent, then response is received via SSE

## Test Strategy

- Unit tests for parameter validation
- Unit tests for error handling (missing params, invalid auth)
- Integration tests for stdio transport (mock)
- Integration tests for HTTP SSE transport (mock)
