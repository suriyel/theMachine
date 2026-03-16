"""
Example: MCP Server (Feature #18)

This example demonstrates how to use the MCP Server to expose the
search_code_context tool via the MCP protocol.

Run the MCP server:
    python -m src.query.mcp

This will start the server in stdio mode, waiting for MCP tool calls.
"""

# Example MCP tool call payload
example_tool_call = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "search_code_context",
        "arguments": {
            "query": "how to configure spring WebClient timeout",
            "api_key": "your-api-key-here",
            "repo": "spring-framework",  # optional
            "language": "Java"  # optional
        }
    }
}

# Example response
example_response = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "content": [
            {
                "type": "text",
                "text": "{\"results\": [{\"repository\": \"spring-framework\", \"file_path\": \"spring-web/src/main/java/org/springframework/web/client/HttpInterfaceProxyFactory.java\", \"symbol\": \"WebClient\", \"score\": 0.95, \"content\": \"public class WebClient extends HttpAccessor implements ...\"}], \"query_time_ms\": 125.5}"
            }
        ]
    }
}

if __name__ == "__main__":
    print("MCP Server Example")
    print("=" * 50)
    print("\nTo run the MCP server:")
    print("  python -m src.query.mcp")
    print("\nExample tool call:")
    print(example_tool_call)
    print("\nExample response:")
    print(example_response)
