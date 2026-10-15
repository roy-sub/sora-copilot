"""The rules engine. PURE: no network, no LLM, no database, no filesystem beyond the rulebase.

This package may import only the standard library, ``clingo``, ``clorm``, ``z3`` and
``pydantic``, plus ``app.domain``. It may not import ``app.services.llm``, ``anthropic``,
``httpx``, ``requests`` or anything under ``app.db``.

That is not a convention. ``tests/test_boundary.py`` walks the AST of every file in this
package and fails the build if a forbidden import ever appears. The product's claim is
that the language model never computes a determination; this package is where that claim
is kept, and the test is how it stays kept.
"""
