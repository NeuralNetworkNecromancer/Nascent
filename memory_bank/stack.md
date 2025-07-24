# Stack

| Concern          | Choice                | Note                                                     |
|------------------|-----------------------|----------------------------------------------------------|
| Language         | Python 3.10+          | Conda or venv                                            |
| Analysis         | Pandas + NumPy        | Sufficient for all checks; no SQL layer needed           |
| Scripting        | Python CLIs (scripts/) | Batch enrichment, merge utilities                        |
| Vector Store     | (TBD)                 | Future RAG stretch goal – consider DuckDB/Faiss          |
| Containerisation | Docker / Compose      | Encapsulates Qdrant + optional helper services           |
| Visualization    | Streamlit             | Interactive dashboard replacing EDA notebook             |
