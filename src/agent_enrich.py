"""agent_enrich.py

Placeholder module for LLM-based row-level enrichment.

Planned flow:
1. Accept DataFrame rows that failed checks.
2. Construct JSON prompt for LLM (OpenAI GPT-4o).
3. Parse responses and merge back into DataFrame.

TODO:
    - implement prompt construction
    - integrate OpenAI client
    - add Qdrant vector-store persistence
""" 