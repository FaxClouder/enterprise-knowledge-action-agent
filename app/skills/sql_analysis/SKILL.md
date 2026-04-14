# Skill: sql_analysis

## Applicable Scenarios
- User asks for SQL draft, schema-based analytics, KPI query templates.
- Read-only analysis with safe SELECT statements.

## Not Applicable Scenarios
- Policy-only explanation without data intent.
- Requests to UPDATE/DELETE/INSERT production tables.
- Tasks without table/schema context when assumptions cannot be made.

## Execution Steps
1. Confirm analysis goal, metric definition, and time window.
2. Infer table joins and dimensions from provided schema names.
3. Generate read-only SQL with clear assumptions.
4. Add validation queries and edge-case notes.

## Output Format
- `Intent Understanding`
- `Suggested SQL` (single block, read-only)
- `Assumptions`
- `Validation Tips`

## Few-Shot Example
### Input
根据 sales_orders(order_id, order_date, amount, region) 查 2026年3月华南 GMV。

### Output
Intent Understanding: Calculate GMV in South China for March 2026.
Suggested SQL:
```sql
SELECT SUM(amount) AS gmv
FROM sales_orders
WHERE order_date >= '2026-03-01'
  AND order_date < '2026-04-01'
  AND region = 'South China';
```
Assumptions:
- `amount` is gross order amount in CNY.
Validation Tips:
- Compare row count and total amount against finance dashboard snapshot.
