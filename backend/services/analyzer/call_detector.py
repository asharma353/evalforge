"""Tree-sitter based LLM call site detection.

Detects calls to OpenAI, Anthropic, LangChain, and LiteLLM SDKs
across Python, JavaScript, and TypeScript files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

from .patterns import FRAMEWORK_PATTERNS, LANGUAGE_MAP


class CallSite(TypedDict):
    """A detected LLM call site in source code."""

    file_path: str
    framework: str
    method: str
    start_line: int
    end_line: int
    source: str
    is_test: bool
    arguments_node: str  # raw text of the arguments node for prompt extraction


def _is_test_file(file_path: str) -> bool:
    """Return True if the file path indicates a test file."""
    path = Path(file_path)
    name = path.name
    parts = path.parts

    # Check directory names
    test_dirs = {"test", "tests", "__tests__", "spec", "specs"}
    for part in parts:
        if part.lower() in test_dirs:
            return True

    # Check filename patterns
    test_patterns = [
        r"_test\.py$",
        r"test_.*\.py$",
        r"\.test\.(ts|tsx|js|jsx)$",
        r"\.spec\.(ts|tsx|js|jsx)$",
    ]
    for pattern in test_patterns:
        if re.search(pattern, name):
            return True

    return False


def _get_full_attribute_chain(node) -> str:
    """Recursively get the full attribute chain text from an attribute/member node."""
    return node.text.decode("utf-8", errors="replace")


def _find_nodes(node, node_type: str) -> list:
    """Recursively find all nodes of the given type in the subtree."""
    results = []
    if node.type == node_type:
        results.append(node)
    for child in node.children:
        results.extend(_find_nodes(child, node_type))
    return results


def _detect_imports(source_code: str, language: str) -> set[str]:
    """Scan source code for framework imports and return set of framework keys."""
    found = set()
    for fw_key, fw_config in FRAMEWORK_PATTERNS.items():
        patterns = fw_config["import_patterns"].get(language, [])
        for pattern in patterns:
            if pattern in source_code:
                found.add(fw_key)
                break
    return found


def _check_call_matches_framework(
    call_text: str,
    method_name: str,
    framework_key: str,
    imported_frameworks: set[str],
) -> bool:
    """Check if a call site matches a given framework's patterns."""
    fw = FRAMEWORK_PATTERNS[framework_key]

    # Method name must be in the framework's call_methods
    if method_name not in fw["call_methods"]:
        return False

    # The call expression text must contain one of the attribute chains
    chains = fw["attribute_chains"]
    if not chains:
        # No attribute chain requirement -- check if framework is imported
        return framework_key in imported_frameworks

    for chain in chains:
        if chain in call_text:
            return True

    # Special case for litellm bare completion() calls -- method name matches
    # and litellm is imported
    if framework_key == "litellm" and method_name in ("completion", "acompletion"):
        if "litellm" in imported_frameworks:
            return True

    return False


def _detect_python_calls(
    tree,
    file_path: str,
    source_code: str,
    imported_frameworks: set[str],
) -> list[CallSite]:
    """Detect LLM call sites in a parsed Python AST."""
    call_sites: list[CallSite] = []
    is_test = _is_test_file(file_path)

    # Find all 'call' nodes
    call_nodes = _find_nodes(tree.root_node, "call")

    for call_node in call_nodes:
        func_node = call_node.child_by_field_name("function")
        if func_node is None:
            continue

        # We care about attribute calls: obj.method(...)
        if func_node.type != "attribute":
            # Could be a bare function call like completion(...)
            # Check if it matches litellm bare call
            if func_node.type == "identifier":
                method_name = func_node.text.decode("utf-8", errors="replace")
                call_text = call_node.text.decode("utf-8", errors="replace")
                if method_name in ("completion", "acompletion") and "litellm" in imported_frameworks:
                    args_node = call_node.child_by_field_name("arguments")
                    args_text = args_node.text.decode("utf-8", errors="replace") if args_node else ""
                    call_sites.append(
                        CallSite(
                            file_path=file_path,
                            framework="litellm",
                            method=method_name,
                            start_line=call_node.start_point[0] + 1,
                            end_line=call_node.end_point[0] + 1,
                            source=call_text,
                            is_test=is_test,
                            arguments_node=args_text,
                        )
                    )
            continue

        attr_node = func_node.child_by_field_name("attribute")
        if attr_node is None:
            continue

        method_name = attr_node.text.decode("utf-8", errors="replace")
        call_text = call_node.text.decode("utf-8", errors="replace")

        # Check each framework
        for fw_key in FRAMEWORK_PATTERNS:
            if _check_call_matches_framework(call_text, method_name, fw_key, imported_frameworks):
                args_node = call_node.child_by_field_name("arguments")
                args_text = args_node.text.decode("utf-8", errors="replace") if args_node else ""
                call_sites.append(
                    CallSite(
                        file_path=file_path,
                        framework=fw_key,
                        method=method_name,
                        start_line=call_node.start_point[0] + 1,
                        end_line=call_node.end_point[0] + 1,
                        source=call_text,
                        is_test=is_test,
                        arguments_node=args_text,
                    )
                )
                break  # A call site matches at most one framework

    return call_sites


def _detect_js_ts_calls(
    tree,
    file_path: str,
    source_code: str,
    imported_frameworks: set[str],
) -> list[CallSite]:
    """Detect LLM call sites in a parsed JS/TS AST."""
    call_sites: list[CallSite] = []
    is_test = _is_test_file(file_path)

    # Find all 'call_expression' nodes
    call_nodes = _find_nodes(tree.root_node, "call_expression")

    for call_node in call_nodes:
        func_node = call_node.child_by_field_name("function")
        if func_node is None:
            continue

        # We care about member expression calls: obj.method(...)
        if func_node.type != "member_expression":
            continue

        prop_node = func_node.child_by_field_name("property")
        if prop_node is None:
            continue

        method_name = prop_node.text.decode("utf-8", errors="replace")
        call_text = call_node.text.decode("utf-8", errors="replace")

        # Check each framework
        for fw_key in FRAMEWORK_PATTERNS:
            if _check_call_matches_framework(call_text, method_name, fw_key, imported_frameworks):
                args_node = call_node.child_by_field_name("arguments")
                args_text = args_node.text.decode("utf-8", errors="replace") if args_node else ""
                call_sites.append(
                    CallSite(
                        file_path=file_path,
                        framework=fw_key,
                        method=method_name,
                        start_line=call_node.start_point[0] + 1,
                        end_line=call_node.end_point[0] + 1,
                        source=call_text,
                        is_test=is_test,
                        arguments_node=args_text,
                    )
                )
                break

    return call_sites


def detect_call_sites(
    project_path: str,
    file_path: str,
    source_code: str,
) -> list[CallSite]:
    """Detect LLM call sites in a source file using tree-sitter AST parsing.

    Args:
        project_path: Root path of the project (used for context only).
        file_path: Path to the file being analyzed (relative or absolute).
        source_code: Source code content of the file.

    Returns:
        List of CallSite TypedDicts with location and metadata.
    """
    suffix = Path(file_path).suffix.lower()
    language_name = LANGUAGE_MAP.get(suffix)

    if language_name is None:
        # Unsupported language
        return []

    try:
        from tree_sitter_language_pack import get_parser  # noqa: PLC0415
    except ImportError:
        return []

    try:
        parser = get_parser(language_name)
        tree = parser.parse(source_code.encode("utf-8"))
    except Exception:
        # Parsing failed -- skip the file
        return []

    # Detect which frameworks are imported in this file
    imported_frameworks = _detect_imports(source_code, language_name)

    if language_name == "python":
        return _detect_python_calls(tree, file_path, source_code, imported_frameworks)
    else:
        return _detect_js_ts_calls(tree, file_path, source_code, imported_frameworks)
