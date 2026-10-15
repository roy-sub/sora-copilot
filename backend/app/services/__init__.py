"""Application services: orchestration, persistence, geometry, documents, the LLM.

``llm.py`` is the only module here allowed to import ``anthropic``, and it has no import
path to the engine. See docs/ARCHITECTURE.md.
"""
