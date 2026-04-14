# Skill: meeting_summary

## Applicable Scenarios
- Meeting transcript summarization.
- Weekly sync notes to decision/action/risk format.

## Not Applicable Scenarios
- SQL generation or policy compliance questions.
- Pure fact lookup that requires external citations only.

## Execution Steps
1. Extract objective, key decisions, risks, blockers.
2. Merge duplicated points and remove filler language.
3. Produce owner + deadline style action items where possible.
4. End with unresolved questions.

## Output Format
- `Summary`
- `Key Decisions`
- `Action Items`
- `Risks`
- `Open Questions`

## Few-Shot Example
### Input
周会讨论：A功能延期一周，原因是接口稳定性不足；李雷负责周五前给出回归报告。

### Output
Summary: Team aligned to delay feature A by one week due to API stability risk.
Key Decisions:
- Feature A launch postponed by one week.
Action Items:
- 李雷: deliver regression report by Friday.
Risks:
- API instability may impact dependent modules.
Open Questions:
- Is rollout plan for dependent modules updated?
