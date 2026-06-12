# ✨ Gluzo AI Assistant (lia_bot)

Welcome to the **Gluzo AI Assistant** repository! This is a full-stack, intelligent chatbot system built using modern AI frameworks and Python web technologies.

## 🏗️ Architecture

The project consists of two main components:

1.  **FastAPI Backend (`gluzo_backend/`)**
    *   Powered by [FastAPI](https://fastapi.tiangolo.com/).
    *   Utilizes the **Agno** Agentic AI framework.
    *   Uses **ChromaDB** for vector storage and retrieval (RAG).
    *   SQLite database managed via SQLAlchemy.
    *   Fuzzy string matching for semantic caching via RapidFuzz.
2.  **Streamlit Frontend (`streamlit_ui/`)**
    *   A beautiful, responsive chatbot UI built with [Streamlit](https://streamlit.io/).
    *   Connects directly to the backend API to stream responses.

## 🚀 Getting Started

### Prerequisites
*   Python 3.9+
*   Ngrok Account (optional, for public tunneling)
*   OpenAI API Key (or equivalent LLM provider key)

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
    Create a `.env` file inside the `gluzo_backend` folder and add necessary keys (like your OpenAI API key and Ngrok Auth token if using `start_all.py`).
    ```env
    OPENAI_API_KEY=your_openai_key_here
    NGROK_AUTHTOKEN=your_ngrok_token_here
    ```

## ⚡ Running the Application

There is a handy `start_all.py` script in the root directory that boots up the entire stack (Backend + Frontend) and automatically provisions a public URL using Ngrok!

Run from the root directory:
```bash
python start_all.py
```

This will:
1. Start the FastAPI server on `http://localhost:8000`.
2. Start the Streamlit UI on `http://localhost:8501`.
3. Open an Ngrok tunnel to expose the Streamlit UI publicly.

Alternatively, you can run the backend and frontend separately:
*   **Backend:** `cd gluzo_backend && python run.py`
*   **Frontend:** `cd streamlit_ui && streamlit run app.py`

## 🛠️ Tech Stack

*   **Backend:** Python, FastAPI, Uvicorn, SQLAlchemy, ChromaDB, Agno
*   **Frontend:** Python, Streamlit
*   **Networking:** Ngrok (via `pyngrok`)

---
*Created by [SinghNitin-0703](https://github.com/SinghNitin-0703)*
