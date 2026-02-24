from __future__ import annotations

from pydantic import BaseModel


class ScanRequest(BaseModel):
    path: str
    project_name: str


class FileNode(BaseModel):
    name: str
    path: str  # relative to project root
    is_dir: bool
    children: list[FileNode] | None = None
    extension: str | None = None


class ScanResponse(BaseModel):
    project_name: str
    root_path: str
    file_tree: list[FileNode]
    total_files: int
    supported_files: int


# --- Analysis schemas ---

class PromptInfo(BaseModel):
    role: str           # system | user | assistant | few_shot | unknown
    content: str        # extracted text or expression
    is_dynamic: bool    # True if could not extract static value


class CallSiteInfo(BaseModel):
    file_path: str
    framework: str
    method: str
    start_line: int
    end_line: int
    source: str
    is_test: bool
    prompts: list[PromptInfo]


class AppTypeInfo(BaseModel):
    type: str           # rag | agent | chatbot | document_processing | general
    confidence: float   # 0.0 to 1.0
    signals: list[str]  # Human-readable explanations


class AnalysisSummary(BaseModel):
    total_files_analyzed: int
    files_with_calls: int
    total_call_sites: int


class AnalyzeRequest(BaseModel):
    project_path: str
    file_paths: list[str]


class AnalysisResponse(BaseModel):
    call_sites: list[CallSiteInfo]
    app_type: AppTypeInfo
    summary: AnalysisSummary


# --- Question schemas ---

class QuestionOption(BaseModel):
    value: str
    label: str


class Question(BaseModel):
    id: str
    text: str
    category: str
    type: str
    options: list[QuestionOption] | None = None
    default: str | list[str] = ""
    placeholder: str | None = None
    context_hint: str | None = None


class GenerateQuestionsRequest(BaseModel):
    analysis_result: dict


class GenerateQuestionsResponse(BaseModel):
    questions: list[Question]
    generation_source: str  # "llm" or "static_fallback"


class SubmitAnswersRequest(BaseModel):
    analysis_result: dict
    answers: dict[str, str | list[str]]
    skipped: list[str] = []


class IntentModel(BaseModel):
    app_type: str
    app_type_confidence: float
    frameworks: list[str]
    call_site_count: int
    prompt_summary: list[dict]
    quality_criteria: list[str]
    failure_concerns: list[str]
    domain_context: str
    expected_behaviors: list[dict]
    skipped_questions: list[str]
    generation_hints: dict


class IntentModelResponse(BaseModel):
    intent_model: dict
