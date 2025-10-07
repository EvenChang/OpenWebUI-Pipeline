# OpenWebUI-Pipeline
A Manifold RAG pipeline integrating Chroma and LLMs with multi-model routing, conversation memory, and intelligent API parameter recovery.

## 🧠 Overview

This pipeline extends the traditional **RAG (Retrieval-Augmented Generation)** workflow with **intelligent API integration**.  
When an MCP API call fails due to missing parameters, the pipeline uses an **LLM reasoning layer** to:

- Infer missing parameters from conversation history.
- Ask the user for clarification — instead of simply returning a 422 error.


---

## ⚙️ Key Features

✅ **RAG Integration**            – Uses Chroma vector database for semantic search.  
✅ **Ollama / OpenAI Compatible** – Fully compatible with local or remote LLMs.  
✅ **Multi-Model Routing**        – Dynamically switch between models (Ollama, DeepSeek, OpenAI).  
✅ **Conversation Memory**        – Keeps short-term memory (window size = 1) for contextual reasoning.  
✅ **Smart API Recovery**         – When an API returns 422, the LLM analyzes error details and infers or requests parameters.  

---

```mermaid
flowchart TD
    A[User Input] --> B[Vector Retrieval]
    B --> C{Similarity High?}
    
    C -->|No| I[Use Original LLM]
    I --> D[Return API Result to User]
    
    C -->|Yes| B2[RAG Semantic Search]
    B2 --> C2[MCP API Caller]
    C2 -->|Success| D[Return API Result to User]
    C2 -->|422 Error| E[LLM Reasoner]
    E --> F[Infer or Request Params]
    F --> G[Re-call MCP API]
    G --> H[Return Final Result to User]

```


## How to Run

1. Deploy this pipeline in your OpenWebUI environment.
2. Make sure your Chroma server is running on port `7777` and contains your `documents_api_collection` collection name.
3. Verify that the Chroma Server has the MCPO Server configured for connection.
