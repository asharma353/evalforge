"""Heuristic app type classification based on import patterns and call site analysis.

Classifies the uploaded codebase into one of:
RAG, agent, chatbot, document_processing, or general.
"""

from __future__ import annotations

from typing import TypedDict

from .patterns import APP_TYPE_SIGNALS


class AppTypeResult(TypedDict):
    """Result of app type classification."""

    type: str           # rag | agent | chatbot | document_processing | general
    confidence: float   # 0.0 to 1.0
    signals: list[str]  # Human-readable explanations for the classification


def classify_app_type(
    call_sites: list,
    file_contents: dict[str, str],
) -> AppTypeResult:
    """Classify the application type based on import patterns and call sites.

    Scans all file contents for import patterns that indicate app type.
    Scores each type from 0.0 to 1.0 and picks the highest-scoring type.
    If the highest score is below 0.3 or two types are within 0.1 of each other,
    classify as "general" with low confidence.

    Args:
        call_sites: List of detected CallSite TypedDicts.
        file_contents: Dict mapping file path to source code content.

    Returns:
        AppTypeResult with type, confidence, and signals.
    """
    # Combine all file contents for pattern matching
    all_content = "\n".join(file_contents.values())

    scores: dict[str, float] = {}
    found_signals: dict[str, list[str]] = {}

    for app_type, signals in APP_TYPE_SIGNALS.items():
        score = 0.0
        type_signals: list[str] = []
        weight = signals.get("weight", 1.0)

        for signal_group_name, signal_list in signals.items():
            if signal_group_name == "weight":
                continue
            if not isinstance(signal_list, list):
                continue

            hits = []
            for pattern in signal_list:
                if pattern in all_content:
                    hits.append(pattern)

            if hits:
                # Each matched signal group contributes to the score
                group_score = min(len(hits) / max(len(signal_list), 1), 1.0) * weight * 0.4
                score += group_score
                type_signals.append(
                    f"{signal_group_name}: found {len(hits)} signal(s) -- {', '.join(hits[:3])}"
                )

        scores[app_type] = min(score, 1.0)
        found_signals[app_type] = type_signals

    # Find the best type
    if not scores or all(v == 0.0 for v in scores.values()):
        return AppTypeResult(
            type="general",
            confidence=0.5,
            signals=["No specific framework signals detected -- defaulting to general"],
        )

    sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_type, best_score = sorted_types[0]
    second_type, second_score = sorted_types[1] if len(sorted_types) > 1 else (None, 0.0)

    # Default to general if score is too low or two types are very close
    if best_score < 0.3:
        return AppTypeResult(
            type="general",
            confidence=max(0.2, 1.0 - best_score),
            signals=[
                f"Best match was '{best_type}' with score {best_score:.2f} -- below threshold, defaulting to general",
                *found_signals.get(best_type, []),
            ],
        )

    if second_score > 0.0 and (best_score - second_score) < 0.1:
        return AppTypeResult(
            type="general",
            confidence=0.4,
            signals=[
                f"Ambiguous: '{best_type}' ({best_score:.2f}) and '{second_type}' ({second_score:.2f}) are close -- defaulting to general",
                *found_signals.get(best_type, []),
                *found_signals.get(second_type or "", []),
            ],
        )

    return AppTypeResult(
        type=best_type,
        confidence=round(min(best_score, 1.0), 2),
        signals=found_signals.get(best_type, []),
    )
