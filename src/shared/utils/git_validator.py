"""Git repository URL validation utility.

This module provides URL validation for Git repositories,
primarily targeting GitHub URLs with API-based existence checking.
"""

import asyncio
import aiohttp
from urllib.parse import urlparse


async def validate_git_url(url: str) -> tuple[bool, str]:
    """Validate that a Git repository URL is reachable.

    For GitHub URLs, this uses the GitHub API to verify the repository exists.
    For other URLs, it performs a basic HTTP HEAD request.

    Args:
        url: Git repository URL (HTTPS only for now)

    Returns:
        Tuple of (is_valid, error_message):
        - (True, "") if URL is valid and reachable
        - (False, "error description") if URL is invalid or unreachable
    """
    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"

    # Only support HTTPS for security
    if parsed.scheme not in ("https", "http"):
        return False, f"Unsupported URL scheme: {parsed.scheme}. Only HTTP/HTTPS are supported."

    # Must have a netloc (host)
    if not parsed.netloc:
        return False, "URL must include a host (e.g., github.com)"

    # For GitHub URLs, use the API to check if repo exists
    if "github.com" in parsed.netloc.lower():
        return await _validate_github_url(parsed)

    # For other URLs, try a HEAD request as best-effort
    return await _validate_generic_url(url)


async def _validate_github_url(parsed) -> tuple[bool, str]:
    """Validate a GitHub repository URL using the GitHub API.

    Args:
        parsed: Parsed URL object

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Extract owner/repo from URL path
    path = parsed.path.rstrip("/").strip("/")

    # Remove .git suffix if present
    if path.endswith(".git"):
        path = path[:-4]

    # Validate path format (should be owner/repo)
    parts = path.split("/")
    if len(parts) < 2:
        return False, f"Invalid GitHub repository path: {path}. Expected format: owner/repo"

    owner, repo = parts[0], parts[1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.head(api_url) as resp:
                if resp.status == 200:
                    return True, ""
                elif resp.status == 404:
                    return False, f"Repository not found: {owner}/{repo}"
                elif resp.status == 403:
                    # Rate limited - still consider URL valid format
                    return True, ""
                elif resp.status in (301, 302):
                    # Redirects - follow to check final destination
                    return True, ""
                else:
                    return False, f"GitHub API returned status {resp.status}"
    except asyncio.TimeoutError:
        return False, "Connection timed out while validating URL"
    except aiohttp.ClientError as e:
        return False, f"Failed to validate URL: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error validating URL: {str(e)}"


async def _validate_generic_url(url: str) -> tuple[bool, str]:
    """Validate a generic URL using a HEAD request.

    This is a best-effort check for non-GitHub URLs.

    Args:
        url: Full URL string

    Returns:
        Tuple of (is_valid, error_message)
    """
    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.head(url, allow_redirects=True) as resp:
                if resp.status < 400:
                    return True, ""
                return False, f"URL returned status {resp.status}"
    except asyncio.TimeoutError:
        return False, "Connection timed out while validating URL"
    except aiohttp.ClientError as e:
        return False, f"Failed to validate URL: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error validating URL: {str(e)}"
