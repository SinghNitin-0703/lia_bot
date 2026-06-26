# ✨ Gluzo AI Assistant (lia_bot)

Welcome to the **Gluzo AI Assistant** repository! This is a state-of-the-art, full-stack, intelligent e-commerce chatbot system specifically designed for a premium skincare platform. Built using modern AI frameworks and Python web technologies, Gluzo features a highly scalable, multi-agent architecture.

## 🌟 Key Features

*   **Multi-Agent Architecture (powered by Agno):**
    *   **Supervisor/Router Agent:** Intelligently routes user requests to the appropriate specialized sub-agent.
    *   **Product Search Agent:** Handles product queries, budget math, and allergen filtering.
    *   **Customer Support Agent:** Manages order tracking, returns, and human escalation.
    *   **Skincare Consultation Agent:** Provides personalized routine advice and product layering guides.
*   **Advanced AI Optimizations:**
    *   **Prompt Caching(Automatecally done by GPT-4.1-mini):** Optimizes system instructions to significantly reduce LLM latency and token costs via Azure OpenAI.
    *   **Semantic Caching:** An in-memory cache mechanism (with future Redis support via RedisVL) that bypasses AI processing for previously answered questions.
*   **Persistent Memory System:**
    *   **Long-Term Memory:** Extracts and saves user preferences (like skin type and issues) to a SQLite database, providing hyper-personalized future interactions.
    *   **Short-Term Memory:** Retains the recent chat history within the active session for seamless conversation continuity.
    *   **Contextual Upselling:** Proactively analyzes the user's active cart to recommend complementary products.
*   **Multimodal Capabilities:**
    *   **Voice-to-Text:** Multilingual audio transcription using Deepgram (Model: `nova-2`).
    *   **Image Extraction:** Document and image-to-text capabilities powered by Azure OpenAI Vision (Model: `gpt-4.1-mini-2`).
*   **Advanced RAG (Retrieval-Augmented Generation):**
    *   **Hybrid Search Engine:** Combines **Vector Search** (Semantic understanding via ChromaDB & OpenAI Embeddings) with **Lexical Search** (Keyword matching via BM25) for highly accurate product retrieval.
    *   **Reciprocal Rank Fusion (RRF):** Mathematically merges scores from both vector and lexical searches to surface the absolute best product matches.
    *   **Dynamic Sorting & Filtering:** Supports strict runtime allergen exclusion, hard budget constraints, and dynamic sorting by relevance, price, or popularity.

## 🧰 Agent Tools & Capabilities

The agents are equipped with specialized tools to perform real-world actions:
*   **External Search Tool (Tavily):** Researches competitor products online to extract their active ingredients and automatically finds the best alternative in our catalog based on ingredient overlap.
*   **Product Search Tools:** Interfaces with the custom `HybridSearchEngine` to query the vector database and lexical index simultaneously. Can dynamically filter out allergens and apply complex budget math before returning results.
*   **Customer Support Tools:** Interfaces with the backend to check order statuses, process returns, verify inventory, provide shipping estimates, and gracefully escalate issues to a human agent.

# 🏗️ Project Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                     USER (Browser)                          │
│              Types / Sends Audio / Image                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         STREAMLIT FRONTEND (Port 8501)                      │
│         streamlit_ui/app.py                                 │
│                                                             │
│  • Login with phone number                                  │
│  • Chat UI with image & audio upload                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                    HTTP Requests
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           FASTAPI BACKEND (Port 8000)                       │
│              gluzo_backend/                                 │
│                                                             │
│ routers/chat.py                                             │
│        │                                                    │
│        ▼                                                    │
│ services/chat_service.py                                    │
│        │                                                    │
│        ▼                                                    │
│ ┌───────────────────────────────┐                           │
│ │      Supervisor Agent         │                           │
│ │      agents/router.py         │                           │
│ └───────┬──────────┬────────────┘                           │
│         │          │                                        │
│         │          │                                        │
│         ▼          ▼                  ▼                     │
│ Product Search  Customer Support  Skincare Consultation     │
│     Agent            Agent               Agent              │
│  search.py        support.py      consultation.py           │
│         │              │                                    │
│         ▼              ▼                                    │
│ search_engine.py  support_tools.py                          │
│ (Vector + BM25)  (escalate_to_human)                        │
│         │                                                   │
│         ▼                                                   │
│  ChromaDB + SQLite                                          │
│         ▲                                                   │
│         │                                                   │
│   data/ (CSV Products)                                      │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
                🌍 NGROK Public Tunnel
          (Exposes Streamlit to the Internet)
```

---

## 🤖 There are 3 Sub-Agents + 1 Supervisor Agent = 4 Agents Total

```text
┌──────────────────────────────────────────────────────────┐
│              TOTAL AGENTS IN THIS PROJECT                │
│                                                          │
│   1 Supervisor Agent  (the boss)                         │
│   +                                                      │
│   3 Sub-Agents        (the specialists)                  │
│   ═══════════════════════════════════════════════════     │
│   4 Agents Total                                         │
└──────────────────────────────────────────────────────────┘
```

---

## 🏗️ Full Agent Map with Tools

```text
                    ┌──────────────────────────────┐
                    │    Gluzo_Supervisor_Agent    │
                    │       (router.py)            │
                    │                              │
                    │  Tools:                      │
                    │  ├── search_products_expert  │
                    │  ├── customer_support_expert │
                    │  ├── skincare_consult_expert │
                    │  ├── update_user_profile     │
                    │  └── add_to_cart             │
                    └───────────┬──────────────────┘
                                │ delegates to
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│ Product_Search   │  │ Customer_Support │  │ Skincare_Consultation│
│    Agent         │  │    Agent         │  │      Agent           │
│  (search.py)     │  │  (support.py)    │  │  (consultation.py)   │
│                  │  │                  │  │                      │
│  Tools:          │  │  Tools:          │  │  Tools:              │
│  ├─ match_       │  │  └─ escalate_    │  │  └─ NONE ❌          │
│  │  product_term │  │     to_human     │  │  (Pure AI advice)    │
│  ├─ optimize_    │  │                  │  │                      │
│  │  budget_      │  │                  │  │                      │
│  │  combinations │  │                  │  │                      │
│  ├─ find_        │  │                  │  │                      │
│  │  competitor_  │  │                  │  │                      │
│  │  alternative  │  │                  │  │                      │
│  └─ add_to_cart  │  │                  │  │                      │
└──────────────────┘  └──────────────────┘  └──────────────────────┘
```

## Components

### 👤 User
- Interacts through a web browser.
- Can:
  - Send text messages
  - Upload images
  - Upload audio

---

### 🎨 Frontend (Streamlit)

**Location:** `streamlit_ui/app.py`

Responsibilities:
- User authentication (phone number login)
- Chat interface
- Image upload
- Audio upload
- Sends HTTP requests to the backend

Runs on:

```
http://localhost:8501
```

---

### ⚙️ Backend (FastAPI)

**Location:** `gluzo_backend/`

Runs on:

```
http://localhost:8000
```

Main request flow:

```
routers/chat.py
        │
        ▼
services/chat_service.py
        │
        ▼
Supervisor Agent
```

---

## 🤖 Multi-Agent System

The **Supervisor Agent** decides which specialized agent should handle the user's request.

### 1. Product Search Agent

**File**

```
agents/search.py
```

Uses:

- `search_engine.py`
- Vector Search
- BM25 Search

Database:

- ChromaDB
- SQLite
- Product CSV files

---

### 2. Customer Support Agent

**File**

```
agents/support.py
```

Uses:

- `support_tools.py`
- Human escalation
- Customer support workflows

---

### 3. Skincare Consultation Agent

**File**

```
agents/consultation.py
```

Handles:

- Skin-related questions
- Product recommendations
- Consultation workflows

---

## 🗄️ Data Layer

Storage components include:

- ChromaDB (Vector Database)
- SQLite
- Product CSV files located in:

```
data/
```

---

## 🌐 Public Access

The Streamlit application is exposed to the internet using:

```
NGROK
```

This creates a secure public URL that forwards traffic to the local Streamlit server.

---

# 🔄 Overall Flow

```text
User
   │
   ▼
Streamlit UI
   │
HTTP Request
   ▼
FastAPI Backend
   │
Chat Service
   │
Supervisor Agent
   │
   ├── Product Search Agent
   ├── Customer Support Agent
   └── Skincare Consultation Agent
            │
            ▼
     ChromaDB + SQLite
            │
            ▼
        Response
            │
            ▼
       Streamlit UI
            │
            ▼
           User
```

## 🚀 Getting Started

### Prerequisites
*   Python 3.9+
*   Azure OpenAI credentials (or standard OpenAI key if modifying the model client)
*   Optional APIs for extended features (Tavily, Deepgram, Azure OpenAI Vision)

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
    pip install -r requirements.txt
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

    # Public Deployment Tunnel
    NGROK_AUTHTOKEN=your_ngrok_token_here
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
3. Automatically launch a secure Ngrok tunnel, providing you with a Public URL to instantly share your live app over the internet!

Alternatively, you can run the backend and frontend separately:
*   **Backend:** `cd gluzo_backend && uvicorn app.main:app --reload` *(or whatever your run script is)*
*   **Frontend:** `cd streamlit_ui && streamlit run app.py`

## 🛠️ Tech Stack

*   **Backend:** Python, FastAPI, Uvicorn, SQLAlchemy, ChromaDB, Agno, Pytest
*   **Frontend:** Python, Streamlit
*   **AI/LLM:** Azure OpenAI, Deepgram, Tavily
*   **Deployment:** Ngrok

---
*Created by [SinghNitin-0703](https://github.com/SinghNitin-0703)*



