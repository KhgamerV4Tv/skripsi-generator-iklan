# Skripsi Generator Iklan - Agent Guidelines

**Purpose:** This repository houses a Streamlit web application designed for a Skripsi Project. It serves as an AI UMKM (Usaha Mikro, Kecil, dan Menengah) Ad Generator, integrating Agentic AI with Gemini and GPT for image and text generation.

## Agent Directives and Rules

To maintain architectural integrity and prevent codebase pollution, all autonomous agents must strictly adhere to the following rules:

### 1. Historical Files
**CRITICAL:** Do NOT modify, delete, or rename historical iteration files unless the project owner explicitly identifies one as an active target.
The project owner has explicitly confirmed that **`app15.py` is the source used by the live Streamlit demo**, so scoped maintenance of `app15.py` is allowed. Other numbered files remain research snapshots unless the owner reclassifies them.

### 2. Active Development
Use these roles:

* **`app15.py`**: owner-confirmed live demo/deployment entry point (V21 Pro).
* **`app.py`**: refactored modernization/reference target for continued development.
* **Other `appXX.py` files**: historical snapshots unless explicitly reclassified by the owner.

Do not infer the active deployment file from numbering or modification timestamps; prefer the owner's explicit statement and the deployment configuration.

### 3. Folder Structure & Architecture (Proposed Refactoring)
The repository currently has a flat structure with many `appXX.py` files in the root. Moving forward, agents should organize new logic according to the following proposed structure to maintain a clean workspace. If these folders do not exist, create them as needed:

*   **`/components/`**: Strictly for Streamlit UI component functions (e.g., sidebars, custom widgets). No backend AI or API logic should be placed here.
*   **`/api/`**: For API wrappers, LLM calls (Gemini/GPT), prompt handling, and external service integrations.
*   **`/utils/`**: For helper functions, data processing, formatting (e.g., `formatter.py`), and non-UI logic.
*   **`/docs/`**: Existing folder for documentation.
*   **`/assets/`**: (If needed) For images, static assets, or generated outputs.

When you create these subfolders during refactoring or development, place an additional `AGENTS.md` file inside them containing specific local rules for that module.

### 4. Code Output
Do NOT write code or utilities meant for backend processing into frontend UI folders, and vice versa. Always check this file before writing new scripts or reorganizing directories.
