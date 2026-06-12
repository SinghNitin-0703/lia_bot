# ✨ Gluzo AI Assistant (lia_bot)

Welcome to the **Gluzo AI Assistant** repository! This is a state-of-the-art, full-stack, intelligent e-commerce chatbot system specifically designed for a premium skincare platform. Built using modern AI frameworks and Python web technologies, Gluzo features a highly scalable, multi-agent architecture.

## 🌟 Key Features

*   **Multi-Agent Architecture (powered by Agno):**
    *   **Supervisor/Router Agent:** Intelligently routes user requests to the appropriate specialized sub-agent.
    *   **Product Search Agent:** Handles product queries, budget math, and allergen filtering.
    *   **Customer Support Agent:** Manages order tracking, returns, and human escalation.
    *   **Skincare Consultation Agent:** Provides personalized routine advice and product layering guides.
*   **Advanced AI Optimizations:**
    *   **Prompt Caching:** Optimizes system instructions to significantly reduce LLM latency and token costs via Azure OpenAI.
    *   **Semantic Caching:** An in-memory cache mechanism (with future Redis support via RedisVL) that bypasses AI processing for previously answered questions.
*   **Persistent Memory System:**
    *   **Long-Term Memory:** Extracts and saves user preferences (like skin type and issues) to a SQLite database, providing hyper-personalized future interactions.
    *   **Short-Term Memory:** Retains the recent chat history within the active session for seamless conversation continuity.
    *   **Contextual Upselling:** Proactively analyzes the user's active cart to recommend complementary products.
*   **Multimodal Capabilities:**
    *   **Voice-to-Text:** Multilingual audio transcription using Deepgram.
    *   **Image Extraction:** Document and image-to-text capabilities powered by Azure Mistral.
*   **RAG (Retrieval-Augmented Generation):**
    *   Uses **ChromaDB** for efficient vector storage and semantic retrieval of the product catalog.

## 🏗️ Architecture

The project consists of two main components:

1.  **FastAPI Backend (`gluzo_backend/`)**
    *   Powered by [FastAPI](https://fastapi.tiangolo.com/) and Uvicorn.
    *   Utilizes the **Agno** Agentic AI framework.
    *   Uses **ChromaDB** for vector storage.
    *   SQLite database managed via SQLAlchemy for user profiling.
    *   Fuzzy string matching for caching via RapidFuzz and `cachetools`.
2.  **Streamlit Frontend (`streamlit_ui/`)**
    *   A beautiful, responsive chatbot UI built with [Streamlit](https://streamlit.io/).
    *   Connects directly to the backend API to stream responses.

## 🚀 Getting Started

### Prerequisites
*   Python 3.9+
*   Azure OpenAI credentials (or standard OpenAI key if modifying the model client)
*   Optional APIs for extended features (Tavily, Deepgram, Azure Mistral)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/SinghNitin-0703/lia_bot.git
    cd lia_bot
    ```

2.  **Install Backend Dependencies:**
    ```bash
    cd gluzo_backend
    pip install -r requirements.txt
    ```

3.  **Install Frontend Dependencies:**
    ```bash
    cd ../streamlit_ui
    pip install streamlit requests
    ```

4.  **Environment Variables:**
    Create a `.env` file inside the `gluzo_backend` folder and add necessary keys. Here is an example of the configuration:
    ```env
    # Core LLM API Keys
    OPENAI_API_KEY=your_openai_key_here
    AZURE_OPENAI_API_KEY=your_azure_openai_key
    AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/

    # Search & Tool APIs
    TAVILY_API_KEY=your_tavily_key

    # Multimodal Features
    DEEPGRAM_API_KEY=your_deepgram_key
    AZURE_MISTRAL_API_KEY=your_azure_mistral_key
    ```

## ⚡ Running the Application

There is a handy `start_all.py` script in the root directory that boots up the entire stack (Backend + Frontend) locally.

Run from the root directory:
```bash
python start_all.py
```

This will:
1. Start the FastAPI server on `http://localhost:8000`.
2. Start the Streamlit UI on `http://localhost:8501`.

Alternatively, you can run the backend and frontend separately:
*   **Backend:** `cd gluzo_backend && uvicorn app.main:app --reload` *(or whatever your run script is)*
*   **Frontend:** `cd streamlit_ui && streamlit run app.py`

## 🛠️ Tech Stack

*   **Backend:** Python, FastAPI, Uvicorn, SQLAlchemy, ChromaDB, Agno
*   **Frontend:** Python, Streamlit
*   **AI/LLM:** Azure OpenAI, Deepgram, Mistral, Tavily

---
*Created by [SinghNitin-0703](https://github.com/SinghNitin-0703)*
