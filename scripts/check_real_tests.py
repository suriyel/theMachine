#!/usr/bin/env python3
"""
Check real test compliance for a long-task project.

Scans test files for real test markers and checks for mock usage within
real test function bodies. Real tests verify actual external dependency
connectivity (DB, config, HTTP, filesystem) without mocking the primary
dependency.

Uses the `real_test` config from feature-list.json:
- marker_pattern: regex to identify real test markers in test files
- mock_patterns: regex patterns for mock framework calls to flag as warnings
- test_dir: directory to scan for test files

Usage:
    python check_real_tests.py <path/to/feature-list.json>
    python check_real_tests.py <path/to/feature-list.json> --feature 3
    python check_real_tests.py <path/to/feature-list.json> --json

Exit codes:
    0 — real tests found, no mock warnings (PASS)
    1 — no real tests found or critical issues (FAIL)
    2 — real tests found but mock warnings present (WARN)
"""

import argparse
import json
import os
import re
import sys


# Default feature reference pattern — {id} is replaced with the feature ID
# Matches: feature_3, feature:3, feature-3, feature 3, feature#3
# Uses negative lookahead (?!\d) so feature_1 doesn't match feature_10
DEFAULT_FEATURE_REF_PATTERN = r"feature[_:\s#-]*{id}(?!\d)"

# Default config used when feature-list.json has no real_test section
DEFAULT_REAL_TEST_CONFIG = {
    "marker_pattern": "real_test",
    "mock_patterns": ["mock\\.patch", "MagicMock", "mocker\\.patch", "@patch"],
    "test_dir": "tests",
    "feature_ref_pattern": DEFAULT_FEATURE_REF_PATTERN,
}

# File extensions to scan per language
TEST_FILE_PATTERNS = {
    "python": re.compile(r"^test_.*\.py$|^.*_test\.py$"),
    "java": re.compile(r"^.*Test\.java$|^.*Tests\.java$"),
    "javascript": re.compile(r"^.*\.test\.(js|jsx)$|^.*\.spec\.(js|jsx)$"),
    "typescript": re.compile(r"^.*\.test\.(ts|tsx)$|^.*\.spec\.(ts|tsx)$"),
    "c": re.compile(r"^test_.*\.c$|^.*_test\.c$"),
    "cpp": re.compile(r"^test_.*\.cpp$|^.*_test\.cpp$"),
    "c++": re.compile(r"^test_.*\.cpp$|^.*_test\.cpp$"),
}

# Function definition patterns per language
FUNC_DEF_PATTERNS = {
    "python": re.compile(r"^(\s*)(def\s+\w+)"),
    "java": re.compile(r"^(\s*)((?:public|private|protected|static|\s)*void\s+\w+|@Test)"),
    "javascript": re.compile(r"^(\s*)((?:it|test|describe)\s*\(|function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?(?:\(|function))"),
    "typescript": re.compile(r"^(\s*)((?:it|test|describe)\s*\(|function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?(?:\(|function))"),
    "c": re.compile(r"^(\s*)(void\s+test_\w+|TEST\s*\()"),
    "cpp": re.compile(r"^(\s*)(void\s+test_\w+|TEST\s*\(|TEST_F\s*\()"),
    "c++": re.compile(r"^(\s*)(void\s+test_\w+|TEST\s*\(|TEST_F\s*\()"),
}


def find_test_files(test_dir, language):
    """Find all test files under test_dir matching the language pattern."""
    pattern = TEST_FILE_PATTERNS.get(language)
    if not pattern:
        # Fallback: scan all common test file patterns
        pattern = re.compile(
            r"^test_.*\.\w+$|^.*_test\.\w+$|^.*Test\.\w+$|"
            r"^.*\.test\.\w+$|^.*\.spec\.\w+$"
        )

    test_files = []
    if not os.path.isdir(test_dir):
        return test_files

    for root, _dirs, files in os.walk(test_dir):
        for fname in sorted(files):
            if pattern.match(fname):
                test_files.append(os.path.join(root, fname))
    return test_files


def extract_function_name(line, language):
    """Extract function/test name from a definition line."""
    if language == "python":
        m = re.match(r"\s*def\s+(\w+)", line)
        return m.group(1) if m else None
    elif language in ("java",):
        m = re.match(r"\s*(?:public|private|protected|static|\s)*void\s+(\w+)", line)
        return m.group(1) if m else None
    elif language in ("javascript", "typescript"):
        # it('name', ...) or test('name', ...)
        m = re.match(r"\s*(?:it|test)\s*\(\s*['\"]([^'\"]+)['\"]", line)
        if m:
            return m.group(1)
        # function testName() or const testName = ...
        m = re.match(r"\s*(?:function\s+(\w+)|(?:const|let|var)\s+(\w+))", line)
        if m:
            return m.group(1) or m.group(2)
        return None
    elif language in ("c", "cpp", "c++"):
        m = re.match(r"\s*(?:void\s+(\w+)|TEST(?:_F)?\s*\(\s*(\w+)\s*,\s*(\w+))", line)
        if m:
            return m.group(1) or f"{m.group(2)}.{m.group(3)}"
        return None
    return None


def find_real_tests(test_files, marker_pattern, language):
    """
    Scan test files for real test markers.

    Returns list of dicts:
        {file, line_no, func_name, func_body_start, func_body_end, marker_line}
    """
    try:
        marker_re = re.compile(marker_pattern, re.IGNORECASE)
    except re.error:
        return []

    func_def_re = FUNC_DEF_PATTERNS.get(language)
    if not func_def_re:
        func_def_re = re.compile(r"^(\s*)(def\s+\w+|function\s+\w+|void\s+\w+)")

    real_tests = []

    for fpath in test_files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except (OSError, IOError):
            continue

        # First pass: find all lines matching marker_pattern
        marker_lines = []
        for i, line in enumerate(lines):
            if marker_re.search(line):
                marker_lines.append(i)

        if not marker_lines:
            continue

        # Second pass: find all function definitions
        func_defs = []  # (line_no, func_name, indent_level)
        for i, line in enumerate(lines):
            m = func_def_re.match(line)
            if m:
                indent = len(m.group(1).expandtabs(4))
                name = extract_function_name(line, language)
                if name:
                    func_defs.append((i, name, indent))

        # For each marker line, find the enclosing or next function
        for ml in marker_lines:
            # Strategy: marker can be on the function def line itself,
            # or on a line above (decorator/comment)
            best_func = None
            best_dist = float("inf")

            for fi, (fl, fname, findent) in enumerate(func_defs):
                # Function must be on or after the marker line
                # (marker is a decorator/comment/label above or on the def line)
                if fl >= ml and (fl - ml) < best_dist:
                    best_dist = fl - ml
                    # Function body extends to next function at same or lower indent, or EOF
                    body_end = len(lines)
                    for nfi in range(fi + 1, len(func_defs)):
                        nfl, _, nfindent = func_defs[nfi]
                        if nfindent <= findent:
                            body_end = nfl
                            break
                    best_func = {
                        "file": fpath,
                        "line_no": ml + 1,  # 1-based
                        "func_name": fname,
                        "func_body_start": fl,
                        "func_body_end": body_end,
                        "marker_line": lines[ml].rstrip(),
                    }

                # Also check if marker is inside the function body
                # (e.g. a comment within the function)
                if fl < ml:
                    # Check if marker is within this function's body
                    body_end_check = len(lines)
                    for nfi in range(fi + 1, len(func_defs)):
                        nfl, _, nfindent = func_defs[nfi]
                        if nfindent <= findent:
                            body_end_check = nfl
                            break
                    if ml < body_end_check:
                        # marker is inside this function
                        if best_func is None or fl > best_func.get("func_body_start", -1):
                            best_func = {
                                "file": fpath,
                                "line_no": ml + 1,
                                "func_name": fname,
                                "func_body_start": fl,
                                "func_body_end": body_end_check,
                                "marker_line": lines[ml].rstrip(),
                            }

            if best_func:
                # Avoid duplicates (same function matched by multiple markers)
                if not any(
                    rt["file"] == best_func["file"]
                    and rt["func_name"] == best_func["func_name"]
                    for rt in real_tests
                ):
                    real_tests.append(best_func)
            else:
                # Marker found but no enclosing function — report as standalone
                real_tests.append({
                    "file": fpath,
                    "line_no": ml + 1,
                    "func_name": "(no function found)",
                    "func_body_start": ml,
                    "func_body_end": min(ml + 50, len(lines)),
                    "marker_line": lines[ml].rstrip(),
                })

    return real_tests


def check_mock_usage(real_tests, mock_patterns, test_files_content_cache):
    """
    Check each real test function body for mock pattern usage.

    Returns list of warning dicts:
        {file, line_no, func_name, mock_pattern, matched_text}
    """
    mock_regexes = []
    for pat in mock_patterns:
        try:
            mock_regexes.append((pat, re.compile(pat, re.IGNORECASE)))
        except re.error:
            continue

    warnings = []

    for rt in real_tests:
        fpath = rt["file"]
        if fpath not in test_files_content_cache:
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    test_files_content_cache[fpath] = f.readlines()
            except (OSError, IOError):
                continue

        lines = test_files_content_cache[fpath]
        body_lines = lines[rt["func_body_start"]:rt["func_body_end"]]

        for pat_str, pat_re in mock_regexes:
            for i, line in enumerate(body_lines):
                if pat_re.search(line):
                    warnings.append({
                        "file": rt["file"],
                        "line_no": rt["func_body_start"] + i + 1,
                        "func_name": rt["func_name"],
                        "mock_pattern": pat_str,
                        "matched_text": line.strip(),
                    })
                    break  # One warning per pattern per function

    return warnings


def build_feature_ref_regex(pattern_template, feature_id):
    """Build a compiled regex for matching a specific feature ID reference."""
    pattern = pattern_template.replace("{id}", str(feature_id))
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error:
        return None


def associate_real_tests_to_features(
    real_tests, active_features, feature_ref_pattern, test_files_content_cache
):
    """
    Associate real tests to features by scanning file names and function bodies.

    Scans marker lines, function definitions, docstrings, and comments for
    feature references matching the feature_ref_pattern (with {id} replaced).

    Returns dict: feature_id → list of associated real test func_names
    """
    per_feature = {}

    for feat in active_features:
        fid = feat.get("id")
        per_feature[fid] = []
        ref_re = build_feature_ref_regex(feature_ref_pattern, fid)
        if not ref_re:
            continue

        for rt in real_tests:
            fpath = rt["file"]

            # Check file name
            fname = os.path.basename(fpath)
            if ref_re.search(fname):
                per_feature[fid].append(rt["func_name"])
                continue

            # Check function body (includes marker line, def line, docstrings, comments)
            if fpath not in test_files_content_cache:
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as fobj:
                        test_files_content_cache[fpath] = fobj.readlines()
                except (OSError, IOError):
                    continue

            lines = test_files_content_cache[fpath]
            # Scan from marker line through function body end
            scan_start = min(rt["line_no"] - 1, rt["func_body_start"])
            body_lines = lines[scan_start:rt["func_body_end"]]

            for line in body_lines:
                if ref_re.search(line):
                    per_feature[fid].append(rt["func_name"])
                    break

    return per_feature


def check_real_tests(path, feature_id=None):
    """
    Main check function.

    Args:
        path: Path to feature-list.json
        feature_id: Optional feature ID to filter check

    Returns:
        dict with keys:
            verdict: "PASS" | "WARN" | "FAIL"
            project: str
            test_dir: str
            marker_pattern: str
            language: str
            test_files_scanned: int
            active_features: int
            real_tests: list of {file, line_no, func_name}
            mock_warnings: list of {file, line_no, func_name, mock_pattern}
            issues: list of str
    """
    result = {
        "verdict": "FAIL",
        "project": "",
        "test_dir": "",
        "marker_pattern": "",
        "feature_ref_pattern": "",
        "language": "",
        "test_files_scanned": 0,
        "active_features": 0,
        "real_tests": [],
        "mock_warnings": [],
        "per_feature": {},
        "features_without_real_tests": [],
        "issues": [],
    }

    # Load feature-list.json
    if not os.path.isfile(path):
        result["issues"].append(f"File not found: {path}")
        return result

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        result["issues"].append(f"Failed to read {path}: {e}")
        return result

    if not isinstance(data, dict):
        result["issues"].append("feature-list.json root must be an object")
        return result

    # Extract config
    result["project"] = data.get("project", "unknown")
    language = data.get("tech_stack", {}).get("language", "python")
    if language in ("c++",):
        language = "cpp"
    result["language"] = language

    rt_config = data.get("real_test", DEFAULT_REAL_TEST_CONFIG)
    if not isinstance(rt_config, dict):
        result["issues"].append("real_test config must be an object")
        return result

    marker_pattern = rt_config.get("marker_pattern", DEFAULT_REAL_TEST_CONFIG["marker_pattern"])
    mock_patterns = rt_config.get("mock_patterns", DEFAULT_REAL_TEST_CONFIG["mock_patterns"])
    test_dir = rt_config.get("test_dir", DEFAULT_REAL_TEST_CONFIG["test_dir"])

    result["marker_pattern"] = marker_pattern
    result["test_dir"] = test_dir

    # Resolve test_dir relative to feature-list.json location
    base_dir = os.path.dirname(os.path.abspath(path))
    abs_test_dir = os.path.join(base_dir, test_dir)

    if not os.path.isdir(abs_test_dir):
        result["issues"].append(f"Test directory not found: {test_dir}")
        return result

    # Count active features
    features = data.get("features", [])
    if feature_id is not None:
        features = [f for f in features if f.get("id") == feature_id]
        if not features:
            result["issues"].append(f"Feature {feature_id} not found")
            return result

    active_features = [
        f for f in features
        if not f.get("deprecated", False)
    ]
    result["active_features"] = len(active_features)

    # Find test files
    test_files = find_test_files(abs_test_dir, language)
    result["test_files_scanned"] = len(test_files)

    if not test_files:
        result["issues"].append(f"No test files found in {test_dir}")
        if active_features:
            result["verdict"] = "FAIL"
        else:
            result["verdict"] = "PASS"
        return result

    # Find real tests
    real_tests = find_real_tests(test_files, marker_pattern, language)
    result["real_tests"] = [
        {"file": os.path.relpath(rt["file"], base_dir), "line_no": rt["line_no"], "func_name": rt["func_name"]}
        for rt in real_tests
    ]

    if not real_tests and active_features:
        result["issues"].append(
            f"No real tests found (marker: {marker_pattern}) but {len(active_features)} active features exist"
        )
        result["verdict"] = "FAIL"
        return result

    if not real_tests and not active_features:
        result["verdict"] = "PASS"
        return result

    # Check mock usage in real test bodies
    content_cache = {}
    mock_warnings = check_mock_usage(real_tests, mock_patterns, content_cache)
    result["mock_warnings"] = [
        {
            "file": os.path.relpath(w["file"], base_dir),
            "line_no": w["line_no"],
            "func_name": w["func_name"],
            "mock_pattern": w["mock_pattern"],
        }
        for w in mock_warnings
    ]

    # Per-feature real test association
    feature_ref_pattern = rt_config.get(
        "feature_ref_pattern", DEFAULT_FEATURE_REF_PATTERN
    )
    result["feature_ref_pattern"] = feature_ref_pattern

    if active_features and real_tests:
        per_feature = associate_real_tests_to_features(
            real_tests, active_features, feature_ref_pattern, content_cache
        )
        result["per_feature"] = {str(k): v for k, v in per_feature.items()}
        result["features_without_real_tests"] = [
            fid for fid, tests in per_feature.items() if not tests
        ]

        # When --feature N is used, require per-feature association
        if feature_id is not None:
            matched_ids = [f["id"] for f in active_features]
            if feature_id in matched_ids and not per_feature.get(feature_id, []):
                ref_example = feature_ref_pattern.replace("{id}", str(feature_id))
                result["issues"].append(
                    f"No real tests associated with feature {feature_id} "
                    f"(add reference matching: {ref_example})"
                )
                result["verdict"] = "FAIL"
                return result

    # Determine verdict
    if mock_warnings:
        result["verdict"] = "WARN"
    else:
        result["verdict"] = "PASS"

    return result


def format_text_output(result):
    """Format result as human-readable text."""
    lines = []
    project = result["project"] or "unknown"
    lines.append(f"Real Test Check — {project}")
    lines.append("═" * max(30, len(lines[0])))

    lines.append(
        f"Scanned: {result['test_dir']}/ "
        f"(marker: {result['marker_pattern']}, "
        f"{result['test_files_scanned']} test files)"
    )
    lines.append(f"Active features: {result['active_features']}")
    lines.append("")

    # Issues
    if result["issues"]:
        for issue in result["issues"]:
            lines.append(f"  ✗ {issue}")
        lines.append("")

    # Real tests found
    real_tests = result["real_tests"]
    lines.append(f"Real tests found: {len(real_tests)}")
    for rt in real_tests:
        lines.append(f"  {rt['file']:<40} :: {rt['func_name']:<40} (line {rt['line_no']})")

    if not real_tests:
        lines.append("  (none)")
    lines.append("")

    # Per-feature coverage
    per_feature = result.get("per_feature", {})
    if per_feature:
        missing = result.get("features_without_real_tests", [])
        lines.append("Per-feature real test coverage:")
        for fid_str in sorted(per_feature.keys(), key=lambda x: int(x)):
            tests = per_feature[fid_str]
            fid = int(fid_str)
            count = len(tests)
            marker = " ← MISSING" if fid in missing else ""
            lines.append(f"  Feature {fid}: {count} real tests{marker}")
            for t in tests:
                lines.append(f"    - {t}")
        lines.append("")

    # Mock warnings
    mock_warnings = result["mock_warnings"]
    if mock_warnings:
        lines.append(f"Mock warnings ({len(mock_warnings)}):")
        for w in mock_warnings:
            lines.append(
                f"  ⚠ {w['file']}:{w['line_no']} :: {w['func_name']} "
                f"— \"{w['mock_pattern']}\" found in function body"
            )
        lines.append("")

    # Verdict
    verdict = result["verdict"]
    if verdict == "PASS":
        summary = f"PASS — {len(real_tests)} real tests found, no mock warnings"
    elif verdict == "WARN":
        summary = (
            f"WARN — {len(real_tests)} real tests found, "
            f"{len(mock_warnings)} mock warnings require LLM review"
        )
    else:
        summary = f"FAIL — {', '.join(result['issues']) if result['issues'] else 'no real tests found'}"

    lines.append(f"Result: {summary}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Check real test compliance for a long-task project"
    )
    parser.add_argument("path", help="Path to feature-list.json")
    parser.add_argument(
        "--feature", type=int, default=None,
        help="Check a specific feature by ID"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output as JSON (for LLM parsing)"
    )

    args = parser.parse_args()

    result = check_real_tests(args.path, feature_id=args.feature)

    if args.json_output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_text_output(result))

    # Exit code
    if result["verdict"] == "PASS":
        sys.exit(0)
    elif result["verdict"] == "WARN":
        sys.exit(2)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
