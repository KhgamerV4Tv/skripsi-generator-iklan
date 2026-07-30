# Utils Guidance

- Keep modules in this folder independent from Streamlit so they can be tested without starting the UI.
- Prefer deterministic transformations with explicit inputs and return values.
- Do not read credentials or make network calls from utility modules.
