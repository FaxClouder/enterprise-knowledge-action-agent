from __future__ import annotations

from app.rag.grading import grade_documents
from app.rag.rewrite import rewrite_query
from app.rag.schemas import RetrievedDocument


def test_grade_documents_relevant() -> None:
    docs = [
        RetrievedDocument(source="policy.md", content="差旅 报销 policy reimbursement", score=0.7),
        RetrievedDocument(source="leave.md", content="请假 审批 流程", score=0.4),
    ]
    relevant, rescored, _ = grade_documents("报销 policy", docs, threshold=0.1)
    assert relevant is True
    assert rescored[0].source == "policy.md"


def test_rewrite_query() -> None:
    out = rewrite_query("报销流程是怎样的")
    assert "reimbursement" in out
