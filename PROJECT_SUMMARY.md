# PROJECT_SUMMARY

## 1. What This Project Solves
This project builds an enterprise-oriented Agent system (not a generic chat bot) for:
- enterprise knowledge/policy Q&A,
- meeting note summarization,
- safe SQL suggestion,
- user preference memory,
- read-only MCP resource/tool access.

## 2. Architecture Highlights
- **Base Agent**: LangChain v1 `create_agent`.
- **Workflow**: LangGraph nodes with retrieval retry loop and shared persistence endpoint.
- **RAG**: decide retrieval -> retrieve -> grade -> rewrite loop (max retries) -> citation output.
- **Skills**: registry + loader + 3 skills (`policy_qa`, `sql_analysis`, `meeting_summary`).
- **Memory**:
  - short-term: thread-scoped checkpoint + recent message summary.
  - long-term: structured store for preferences / terms / task summaries.
- **MCP**: adapter-based optional external server + local fallback to keep demo runnable.
- **Observability**: LangSmith tracing env wiring + eval pipeline.

## 3. Minimal Demo Script
1. `python scripts/ingest_docs.py`
2. `python -m app.main --interactive --user-id demo_user --thread-id demo_thread`
3. Run demo questions for knowledge, SQL skill, memory, MCP resource.
4. `python evals/run_eval.py` for baseline report.

## 4. Evaluation Coverage
- Dataset size: 20 cases.
- Metrics:
  - `answer_correct`
  - `citation_present`
  - `expected_skill_selected`
  - `expected_tool_path`

## 5. Explicit TODO
- TODO: Complete real MCP tool invocation lifecycle for configured external servers.
- TODO: Add MCP server endpoint mode to expose this project to other clients.
- TODO: Improve answer scoring from keyword heuristic to LLM judge + human calibration.
