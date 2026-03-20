#!/usr/bin/env python
"""Example: Web UI Search Page (Feature #19)

This example demonstrates the Web UI functionality for the Code Context Retrieval system.
Note: This requires a running FastAPI server with Web UI enabled.

Usage:
    1. Start the query service: uvicorn src.query.main:app --reload
    2. Open browser to: http://localhost:8000/login
    3. Enter a valid API key to authenticate
    4. Navigate to /search to perform queries
"""

# The Web UI provides the following endpoints:
#
# - GET /login - Login page with API key form
# - POST /login - Authenticate with API key, creates session cookie
# - GET /search - Search page (requires authentication)
# - GET /search?q=<query>&lang=<language> - Search with query and optional language filter
# - GET /logout - Logout and clear session
#
# Supported language filters: all, java, python, typescript, javascript, c, cpp
#
# Example API usage (requires valid API key):
if __name__ == "__main__":
    print("Web UI is available at:")
    print("  - Login: http://localhost:8000/login")
    print("  - Search: http://localhost:8000/search")
    print("")
    print("To test with curl:")
    print('  curl -c cookies.txt -X POST http://localhost:8000/login \\')
    print('       -d "api_key=your-api-key"')
    print('  curl -b cookies.txt "http://localhost:8000/search?q=WebClient+timeout"')
