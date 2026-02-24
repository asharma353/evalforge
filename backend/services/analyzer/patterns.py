"""Framework detection patterns for LLM call site identification.

Covers OpenAI, Anthropic, LangChain, and LiteLLM across Python/JS/TS.
"""

from __future__ import annotations

# Maps file extension to tree-sitter language name
LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}

# Framework detection patterns. Each entry:
#   name: display name
#   import_patterns: dict[language -> list[import substring to look for]]
#   call_methods: list of method names that indicate an LLM call
#   attribute_chains: list of attribute chain substrings that must appear
#                     in the full call expression (to avoid false positives)
FRAMEWORK_PATTERNS: dict[str, dict] = {
    "openai": {
        "name": "OpenAI",
        "import_patterns": {
            "python": [
                "from openai import",
                "import openai",
                "from openai.types",
            ],
            "javascript": [
                'from "openai"',
                "from 'openai'",
                'require("openai")',
                "require('openai')",
            ],
            "typescript": [
                'from "openai"',
                "from 'openai'",
                'require("openai")',
                "require('openai')",
            ],
        },
        "call_methods": ["create"],
        "attribute_chains": [
            "chat.completions.create",
            "completions.create",
            "ChatCompletion.create",  # legacy v0.x
        ],
    },
    "anthropic": {
        "name": "Anthropic",
        "import_patterns": {
            "python": [
                "from anthropic import",
                "import anthropic",
            ],
            "javascript": [
                'from "@anthropic-ai/sdk"',
                "from '@anthropic-ai/sdk'",
                'require("@anthropic-ai/sdk")',
                "require('@anthropic-ai/sdk')",
            ],
            "typescript": [
                'from "@anthropic-ai/sdk"',
                "from '@anthropic-ai/sdk'",
                'require("@anthropic-ai/sdk")',
                "require('@anthropic-ai/sdk')",
            ],
        },
        "call_methods": ["create"],
        "attribute_chains": [
            "messages.create",
        ],
    },
    "langchain": {
        "name": "LangChain",
        "import_patterns": {
            "python": [
                "from langchain",
                "import langchain",
                "from langchain_core",
                "from langchain_openai",
                "from langchain_anthropic",
                "from langchain_community",
            ],
            "javascript": [
                'from "langchain"',
                "from 'langchain'",
                'from "@langchain/',
                "from '@langchain/",
            ],
            "typescript": [
                'from "langchain"',
                "from 'langchain'",
                'from "@langchain/',
                "from '@langchain/",
            ],
        },
        "call_methods": ["invoke", "ainvoke", "run", "from_messages"],
        "attribute_chains": [
            ".invoke",
            ".ainvoke",
            ".run",
            "ChatPromptTemplate.from_messages",
            "from_messages",
        ],
    },
    "litellm": {
        "name": "LiteLLM",
        "import_patterns": {
            "python": [
                "import litellm",
                "from litellm import",
            ],
            "javascript": [],
            "typescript": [],
        },
        "call_methods": ["completion", "acompletion"],
        "attribute_chains": [
            "litellm.completion",
            "litellm.acompletion",
            # Also matches bare completion() / acompletion() when litellm is imported
        ],
    },
}

# App type classification signals.
# Each entry maps to a list of import/pattern substrings that indicate that type.
APP_TYPE_SIGNALS: dict[str, dict] = {
    "rag": {
        "vector_db_imports": [
            "chromadb",
            "pinecone",
            "faiss",
            "qdrant",
            "weaviate",
            "milvus",
            "pgvector",
            "from langchain_community.vectorstores",
            "from langchain.vectorstores",
            "VectorStore",
            "Chroma",
            "FAISS",
        ],
        "embedding_imports": [
            "OpenAIEmbeddings",
            "HuggingFaceEmbeddings",
            "embeddings",
            "embed_query",
            "embed_documents",
            "create_embedding",
        ],
        "retriever_patterns": [
            "retriever",
            "Retriever",
            "DocumentLoader",
            "BaseLoader",
            "TextLoader",
            "similarity_search",
            "as_retriever",
        ],
        "weight": 1.0,
    },
    "agent": {
        "tool_patterns": [
            "@tool",
            "Tool(",
            "tools=[",
            "function_definitions",
            "functions=[",
            "tool_choice",
            "AgentExecutor",
            "create_react_agent",
            "create_tool_calling_agent",
        ],
        "framework_imports": [
            "langgraph",
            "crewai",
            "autogen",
            "AgentExecutor",
            "from langgraph",
            "from crewai",
            "from autogen",
            "StateGraph",
            "CompiledGraph",
        ],
        "weight": 1.0,
    },
    "chatbot": {
        "conversation_patterns": [
            "chat_history",
            "conversation_history",
            "message_history",
            "ConversationChain",
            "ConversationBufferMemory",
            "ConversationSummaryMemory",
            "MessagesPlaceholder",
            "session_id",
            "multi_turn",
        ],
        "memory_patterns": [
            "Memory(",
            "memory=",
            "chat_memory",
            "BaseMemory",
            "RunnableWithMessageHistory",
        ],
        "weight": 1.0,
    },
    "document_processing": {
        "parser_imports": [
            "pypdf",
            "PyPDF",
            "python-docx",
            "docx",
            "unstructured",
            "pdfplumber",
            "PyMuPDF",
            "fitz",
            "PDFMiner",
            "pdfminer",
        ],
        "batch_patterns": [
            "batch_process",
            "process_documents",
            "DocumentProcessor",
            "for doc in",
            "for document in",
            "bulk_",
            "batch_",
        ],
        "weight": 1.0,
    },
}
