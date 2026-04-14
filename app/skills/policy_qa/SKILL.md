# Skill: policy_qa

## Applicable Scenarios
- Enterprise reimbursement, leave, travel, procurement, and compliance policy Q&A.
- Questions requiring policy boundary explanation and reference-aware answers.

## Not Applicable Scenarios
- SQL generation, schema analysis, or data metric calculation.
- Meeting transcript summarization tasks.
- High-risk write operations or legal final advice.

## Execution Steps
1. Restate user question in one sentence and identify policy topic.
2. Use retrieved citations if available; if none, clearly say evidence is limited.
3. Provide policy answer with constraints, exceptions, and escalation path.
4. End with a short checklist for user action.

## Output Format
- `Policy Answer`: concise answer.
- `Evidence`: bullet list with citation names.
- `Action Checklist`: 2-4 bullets.

## Few-Shot Example
### Input
员工出差打车发票丢了还能报销吗？

### Output
Policy Answer: Missing invoice reimbursement is generally not standard, but exception workflow may apply for approved emergency cases.
Evidence:
- travel_expense_policy.md
Action Checklist:
- Ask direct manager for exception approval.
- Submit alternative proof (ride record + payment screenshot).
- Attach explanation in reimbursement form.
