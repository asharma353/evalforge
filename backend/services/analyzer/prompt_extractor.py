"""Prompt extraction from LLM call site AST nodes.

Extracts string literals, templates, and dynamic values from
the arguments of detected LLM call sites.
"""

from __future__ import annotations

from typing import TypedDict

from .call_detector import CallSite
from .patterns import LANGUAGE_MAP


class Prompt(TypedDict):
    """An extracted prompt from a call site."""

    role: str        # system | user | assistant | few_shot | unknown
    content: str     # extracted text or expression description
    is_dynamic: bool # True if could not extract static text
    source_line: int # line number where the prompt appears


def _extract_string_value(node) -> tuple[str, bool]:
    """Extract text from a string/template node.

    Returns:
        (content, is_dynamic) tuple.
        is_dynamic=True means we couldn't get the static value.
    """
    if node is None:
        return ("dynamic", True)

    node_type = node.type
    text = node.text.decode("utf-8", errors="replace") if node.text else ""

    # String literal (Python: string, JS/TS: string)
    if node_type in ("string", "string_literal", "string_content"):
        # Strip quotes
        if len(text) >= 2 and text[0] in ('"', "'") and text[-1] in ('"', "'"):
            return (text[1:-1], False)
        # Triple-quoted
        if len(text) >= 6 and text[:3] in ('"""', "'''") and text[-3:] in ('"""', "'''"):
            return (text[3:-3], False)
        return (text, False)

    # F-strings (Python)
    if node_type in ("f_string", "fstring"):
        return (text, True)  # dynamic -- template with placeholders

    # Concatenated strings
    if node_type == "concatenated_string":
        return (text, True)

    # Template literal (JS/TS)
    if node_type == "template_string":
        return (text, True)

    # Identifier or attribute -- dynamic reference
    if node_type in ("identifier", "attribute", "subscript", "call"):
        return (text, True)

    # Any other node -- treat as dynamic
    return (text, True)


def _find_nodes_by_type(node, types: set[str]) -> list:
    """Find all descendant nodes matching any of the given types."""
    results = []
    if node.type in types:
        results.append(node)
    for child in node.children:
        results.extend(_find_nodes_by_type(child, types))
    return results


def _extract_from_messages_list(messages_node, source_line: int) -> list[Prompt]:
    """Extract prompts from a messages=[...] list node."""
    prompts: list[Prompt] = []

    if messages_node is None:
        return prompts

    # Walk through list elements looking for dict-like objects with role/content
    # Works for both Python dicts and JS/TS object literals
    dict_nodes = _find_nodes_by_type(
        messages_node,
        {"dictionary", "object", "object_pattern"},
    )

    for d in dict_nodes:
        role_value = None
        content_value = None

        # Python dict: keyword pairs as pairs/pair nodes
        # JS/TS: pair nodes or property nodes
        pair_nodes = _find_nodes_by_type(d, {"pair", "property_identifier"})

        # Simpler approach: look for the text of the dict/object
        d_text = d.text.decode("utf-8", errors="replace") if d.text else ""

        # Extract role
        role_str = "unknown"
        for role_name in ("system", "user", "assistant", "developer", "few_shot"):
            if f'"role": "{role_name}"' in d_text or f"'role': '{role_name}'" in d_text or f'"role":"{role_name}"' in d_text:
                role_str = role_name
                break
            if f'role: "{role_name}"' in d_text or f"role: '{role_name}'" in d_text:
                role_str = role_name
                break

        # Extract content -- look for content key
        content_str = "dynamic"
        is_dynamic = True

        # Find content value in the dict
        if '"content"' in d_text or "'content'" in d_text or "content:" in d_text:
            # Try to find the content node value
            # Look for string children near "content" key
            for child in d.children:
                if child.type in ("pair",):
                    key_node = child.child_by_field_name("key") if hasattr(child, "child_by_field_name") else None
                    val_node = child.child_by_field_name("value") if hasattr(child, "child_by_field_name") else None
                    if key_node and val_node:
                        key_text = key_node.text.decode("utf-8", errors="replace") if key_node.text else ""
                        if "content" in key_text:
                            content_str, is_dynamic = _extract_string_value(val_node)

            if content_str == "dynamic":
                # Fallback: extract between content: and end
                content_str = "dynamic (extracted from call site)"
                is_dynamic = True

        prompts.append(
            Prompt(
                role=role_str,
                content=content_str,
                is_dynamic=is_dynamic,
                source_line=d.start_point[0] + 1 if hasattr(d, "start_point") else source_line,
            )
        )

    # If we found no dict nodes but the node has text, treat as dynamic
    if not prompts and messages_node.text:
        messages_text = messages_node.text.decode("utf-8", errors="replace")
        if messages_text.strip() not in ("[]", "()", ""):
            prompts.append(
                Prompt(
                    role="unknown",
                    content="dynamic",
                    is_dynamic=True,
                    source_line=source_line,
                )
            )

    return prompts


def _find_keyword_arg(args_text: str, arg_name: str) -> str | None:
    """Find the value of a keyword argument in args text (simple regex approach)."""
    import re  # noqa: PLC0415

    # Python: arg_name=value or arg_name = value
    # JS/TS: arg_name: value
    patterns = [
        rf'{arg_name}\s*=\s*(["\'])(.*?)\1',  # Python keyword with string
        rf'{arg_name}\s*:\s*(["\'])(.*?)\1',   # JS/TS property with string
    ]
    for pattern in patterns:
        match = re.search(pattern, args_text, re.DOTALL)
        if match:
            return match.group(2)
    return None


def extract_prompts(call_site: CallSite, source_code: str) -> list[Prompt]:
    """Extract prompt content from a call site's arguments.

    Args:
        call_site: The detected call site.
        source_code: Full source code of the file (for context).

    Returns:
        List of Prompt TypedDicts with role, content, and metadata.
    """
    prompts: list[Prompt] = []
    args_text = call_site.get("arguments_node", "")
    source_line = call_site.get("start_line", 1)

    if not args_text:
        return prompts

    suffix = "." + call_site.get("file_path", "x.py").rsplit(".", 1)[-1].lower()
    language_name = LANGUAGE_MAP.get(suffix, "python")

    # Try to parse the arguments region for structured extraction
    try:
        from tree_sitter_language_pack import get_parser  # noqa: PLC0415

        parser = get_parser(language_name)

        # Wrap args in a valid expression to parse
        if language_name == "python":
            wrapper = f"f({args_text})"
        else:
            wrapper = f"f({args_text})"

        tree = parser.parse(wrapper.encode("utf-8"))
        root = tree.root_node

        # Find the argument list / arguments node
        call_nodes_types = {"call", "call_expression"}
        arg_list_types = {"argument_list", "arguments"}

        def find_first(node, types):
            if node.type in types:
                return node
            for child in node.children:
                result = find_first(child, types)
                if result:
                    return result
            return None

        call_node = find_first(root, call_nodes_types)
        if call_node:
            args_node = call_node.child_by_field_name("arguments")
        else:
            args_node = None

        if args_node:
            # Look for keyword arguments
            for child in args_node.children:
                if child.type in ("keyword_argument",):
                    key = child.child_by_field_name("name")
                    value = child.child_by_field_name("value")
                    if key is None or value is None:
                        continue
                    key_text = key.text.decode("utf-8", errors="replace") if key.text else ""

                    if key_text == "messages":
                        # Extract from messages list
                        msg_prompts = _extract_from_messages_list(value, source_line)
                        prompts.extend(msg_prompts)

                    elif key_text == "system":
                        # Anthropic system parameter
                        content, is_dynamic = _extract_string_value(value)
                        prompts.append(
                            Prompt(
                                role="system",
                                content=content,
                                is_dynamic=is_dynamic,
                                source_line=value.start_point[0] + 1 if hasattr(value, "start_point") else source_line,
                            )
                        )

                    elif key_text == "prompt":
                        # Legacy OpenAI / LiteLLM prompt parameter
                        content, is_dynamic = _extract_string_value(value)
                        prompts.append(
                            Prompt(
                                role="user",
                                content=content,
                                is_dynamic=is_dynamic,
                                source_line=value.start_point[0] + 1 if hasattr(value, "start_point") else source_line,
                            )
                        )

                # JS/TS pair nodes (object properties)
                elif child.type in ("pair",):
                    key = child.child_by_field_name("key")
                    value = child.child_by_field_name("value")
                    if key is None or value is None:
                        continue
                    key_text = key.text.decode("utf-8", errors="replace").strip('"\'') if key.text else ""

                    if key_text == "messages":
                        msg_prompts = _extract_from_messages_list(value, source_line)
                        prompts.extend(msg_prompts)
                    elif key_text == "system":
                        content, is_dynamic = _extract_string_value(value)
                        prompts.append(
                            Prompt(
                                role="system",
                                content=content,
                                is_dynamic=is_dynamic,
                                source_line=source_line,
                            )
                        )

    except Exception:
        # Fallback: regex-based extraction from args text
        pass

    # Fallback regex extraction if AST parsing found nothing
    if not prompts:
        import re  # noqa: PLC0415

        # Look for messages=[...] or messages: [...]
        messages_match = re.search(
            r'messages\s*[=:]\s*\[([^\]]*(?:\[[^\]]*\][^\]]*)*)\]',
            args_text,
            re.DOTALL,
        )
        if messages_match:
            messages_content = messages_match.group(0)
            # Extract role/content pairs from the text
            role_content_matches = re.findall(
                r'["\']role["\']\s*[=:]\s*["\'](\w+)["\'].*?["\']content["\']\s*[=:]\s*["\']([^"\']*)["\']',
                messages_content,
                re.DOTALL,
            )
            for role, content in role_content_matches:
                prompts.append(
                    Prompt(
                        role=role,
                        content=content,
                        is_dynamic=False,
                        source_line=source_line,
                    )
                )

            if not role_content_matches:
                # Dynamic messages
                prompts.append(
                    Prompt(
                        role="unknown",
                        content="dynamic",
                        is_dynamic=True,
                        source_line=source_line,
                    )
                )

        # Look for system= keyword
        system_match = re.search(r'system\s*=\s*["\']([^"\']+)["\']', args_text)
        if system_match:
            prompts.append(
                Prompt(
                    role="system",
                    content=system_match.group(1),
                    is_dynamic=False,
                    source_line=source_line,
                )
            )

        # Look for prompt= keyword (legacy)
        prompt_match = re.search(r'\bprompt\s*=\s*["\']([^"\']+)["\']', args_text)
        if prompt_match:
            prompts.append(
                Prompt(
                    role="user",
                    content=prompt_match.group(1),
                    is_dynamic=False,
                    source_line=source_line,
                )
            )

    return prompts
