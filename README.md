# Raahat (राहत) — AI Mental Health Companion

> **Note:** This project is currently in **Development Phase**.

---

## 📖 Overview

**Raahat** is a specialized mental health chatbot designed to provide empathetic, safe, and context-aware conversations. Unlike generic AI, Raahat utilizes a **"Sandwich Architecture"** where the LLM is guided by strict safety protocols and a curated medical knowledge base (RAG).

The goal is to bridge the gap between expensive therapy and accessible mental health support using **local-first principles** and **privacy-focused architecture**.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Language** | Python 3.10+ |
| **Brain (LLM)** | Groq API (Llama 3.3-70B) |
| **Memory (Database)** | Supabase (PostgreSQL) |
| **Interface** | Hybrid CLI → Future PWA |
| **Safety** | Custom Python Middleware + Regex Guardrails |

---

## 👥 The Team

This project is a collaborative effort with distinct engineering roles:

| Member | Role | Responsibilities |
| :--- | :--- | :--- |
| **Anshuman Awasthi** | **System Architect** | Database Design (Supabase), API Logic, User State Management, Async Architecture. |
| **Animesh Mudit** | **AI Engineer** | Model Tuning (Prompts), Safety Systems, RAG Pipeline, Crisis Detection Logic. |

---

## 📂 Project Structure

We follow a modular architecture to separate **Logic (Brain)** from **State (Memory)**.

```text
raahat-cli/
├── config/              # Configuration & Environment loading
├── core/
│   ├── brain.py         # AI Logic & Crisis Detection (Animesh)
│   ├── memory.py        # Database Interactions (Anshuman)
├── main.py              # Application Entry Point (CLI Loop)
├── requirements.txt     # Dependencies
└── .env                 # API Keys (Not tracked in Git)
```

---

## 🚀 How to Use

### 1. Prerequisites

Ensure you have your `.env` file populated with the following keys:

```env
GROQ_API_KEY=your_groq_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### 2. Launch the Backend (The Brain)

The backend must be running to handle chat requests. Open your terminal and run:

```bash
pip install -r requirements.txt
python server.py
```

The server will start at `http://127.0.0.1:8000`.
You can view the Interactive API documentation at `http://127.0.0.1:8000/docs`.

### 3. Launch the Interface

- **Modern Web UI:** Open `dashboard.html` in your browser. *(We recommend using the VS Code Live Server extension.)*
- **Legacy CLI Mode:** For a terminal-only experience, run:

```bash
python main.py
```

---

## 🛡️ Safety & Privacy

- **Crisis Detection:** Real-time scanning for keywords associated with distress or emergency.
- **Linguistic Nuance:** Filtering that understands the difference between clinical distress and casual slang.
- **Data Security:** All API keys are stored server-side; the frontend only communicates via the secured FastAPI bridge.

---

> *"Building a bridge between technology and tranquility."*
