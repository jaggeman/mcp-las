# AI Agent Guidelines for MCP-LAS

## Core Rules & Architecture

1. **Test-Driven Development (TDD) Required**:
   - Always write unit tests in `tests/` before implementing new features or fixing bugs.
   - Run the full test suite (`.venv\Scripts\pytest.exe tests/ -v`) before making commits or deployments.
   - Zero test failures are tolerated.

2. **Legal & Chunker Determinism**:
   - Never alter statute section boundaries without running `python check_coverage.py`.
   - Ensure all 477 sections across the 8 core Swedish statutes retain 100% integrity without accidental truncation or duplicates.

3. **Security Standards**:
   - Use constant-time comparison (`hmac.compare_digest`) for API keys.
   - Enforce sliding window rate limiting.
   - Log structured JSON events via Cloud Logging.
   - Maintain non-root container user (`appuser` UID 10001) in Dockerfile.

4. **Official Sources & Precedents**:
   - Keep case law and references aligned with Arbetsdomstolen (AD) and Swedish government portals (Riksdagen, Försäkringskassan, DO, SCB).
