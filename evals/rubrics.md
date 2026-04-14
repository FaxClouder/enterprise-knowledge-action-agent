# Evaluation Rubrics

## Metrics
- `answer_correct`: keyword-level correctness (minimum viable heuristic).
- `citation_present`: citation exists when retrieval-based question is expected.
- `expected_skill_selected`: selected skill equals expected skill label.
- `expected_tool_path`: expected tool is present in `used_tools` path.

## Notes
- This is a baseline regression suite for project demos.
- For production, replace heuristic answer checks with LLM-as-judge + human sampling.
- Keep at least 20 cases and include all task types.
