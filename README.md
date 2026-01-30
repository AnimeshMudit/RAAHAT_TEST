# Raahat (राहत) - AI Mental Health Companion

> **Note:** This project is currently in the **CLI Development Phase**.

## 📖 Overview
**Raahat** is a specialized mental health chatbot designed to provide empathetic, safe, and context-aware conversations. Unlike generic AI, Raahat utilizes a "Sandwich Architecture" where the LLM is guided by strict safety protocols and a curated medical knowledge base (RAG).

The goal is to bridge the gap between expensive therapy and accessible mental health support using local-first principles and privacy-focused architecture.

## 🛠️ Tech Stack
* **Language:** Python 3.10+
* **Brain (LLM):** Groq API (Llama 3.2 / 3-8B)
* **Memory (Database):** Supabase (PostgreSQL)
* **Interface:** Hybrid CLI (Command Line) -> Future PWA
* **Safety:** Custom Python Middleware + Regex Guardrails

## 👥 The Team
This project is a collaborative effort with distinct engineering roles:

| Member | Role | Responsibilities |
| :--- | :--- | :--- |
| **Anshuman Awasthi** | **System Architect** | Database Design (Supabase), API Logic, User State Management, Async Architecture. |
| **Animesh Mudit** | **AI Engineer** | Model Tuning (Prompts), Safety Systems, RAG Pipeline, Crisis Detection Logic. |

## 📂 Project Structure
We follow a modular architecture to separate Logic (Brain) from State (Memory).

```text
raahat-cli/
├── config/              # Configuration & Environment loading
├── core/
│   ├── brain.py         # AI Logic & Crisis Detection (Animesh)
│   ├── memory.py        # Database Interactions (Anshuman)
├── main.py              # Application Entry Point (CLI Loop)
├── requirements.txt     # Dependencies
└── .env                 # API Keys (Not tracked in Git)