# Stack

| Concern          | Choice                | Note                                                     |
|------------------|-----------------------|----------------------------------------------------------|
| Language         | Python 3.10+          | Conda or venv                                            |
| Analysis         | Pandas + NumPy        | Sufficient for all checks; no SQL layer needed           |
| Notebooks        | JupyterLab / VS Code  | `.ipynb` tracked with nbstripout                         |
| LLM (enrich)     | OpenAI GPT‑4o         | Used by `agent_enrich.py`                                |
| Vector DB        | Qdrant (via Docker)   | `docker-compose.yml` spins up a reproducible local store |
| Containerisation | Docker / Compose      | Encapsulates Qdrant + optional helper services           |
| Visualization    | Streamlit             | Interactive dashboard replacing EDA notebook             |
