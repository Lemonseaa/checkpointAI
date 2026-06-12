"""Workflow contract validation for external evidence imports."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ContractIssue(BaseModel):
    """One workflow contract validation issue."""

    code: str
    field: str
    severity: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ContractValidationResult(BaseModel):
    """Human-facing workflow contract validation result."""

    status: str
    issues: list[ContractIssue] = Field(default_factory=list)

    @property
    def accepted(self) -> bool:
        """Return whether ingestion can continue."""

        return self.status in {"valid", "warning"}


class WorkflowContractValidator:
    """Validate the minimum external workflow evidence contract."""

    REQUIRED_FIELDS = ("workflow_id", "run_id", "nodes", "trace", "metrics")

    def validate(self, payload: dict[str, Any]) -> ContractValidationResult:
        """Validate one raw workflow payload before normalization."""

        issues: list[ContractIssue] = []
        for field in self.REQUIRED_FIELDS:
            if field not in payload:
                issues.append(
                    ContractIssue(
                        code="workflow.required_field_missing",
                        field=field,
                        severity="error",
                        message=f"Missing required workflow contract field: {field}.",
                    )
                )
        nodes = payload.get("nodes")
        edges = payload.get("edges")
        trace = payload.get("trace")
        metrics = payload.get("metrics")
        if "nodes" in payload and not isinstance(nodes, list):
            issues.append(self._type_issue("nodes", "list"))
        if "edges" not in payload:
            issues.append(
                ContractIssue(
                    code="workflow.edges_missing",
                    field="edges",
                    severity="warning",
                    message="Workflow edges are missing; map quality will be limited.",
                )
            )
        elif not isinstance(edges, list):
            issues.append(self._type_issue("edges", "list"))
        if "trace" in payload and not isinstance(trace, list):
            issues.append(self._type_issue("trace", "list"))
        if "metrics" in payload and not isinstance(metrics, dict):
            issues.append(self._type_issue("metrics", "dict"))

        if isinstance(nodes, list):
            for node in nodes:
                if not isinstance(node, dict) or not node.get("id"):
                    issues.append(
                        ContractIssue(
                            code="workflow.node_id_missing",
                            field="nodes",
                            severity="error",
                            message="Every workflow node requires an id.",
                        )
                    )
                    continue
                metadata = node.get("metadata")
                if isinstance(metadata, dict) and (metadata.get("black_box") or metadata.get("opaque")):
                    issues.append(
                        ContractIssue(
                            code="workflow.black_box_node",
                            field="nodes",
                            severity="warning",
                            message=f"Node {node['id']} is marked as a black box.",
                            details={"node_id": str(node["id"])},
                        )
                    )

        if any(issue.severity == "error" for issue in issues):
            status = "rejected"
        elif issues:
            status = "warning"
        else:
            status = "valid"
        return ContractValidationResult(status=status, issues=issues)

    @staticmethod
    def _type_issue(field: str, expected: str) -> ContractIssue:
        return ContractIssue(
            code="workflow.invalid_type",
            field=field,
            severity="error",
            message=f"Field {field} must be a {expected}.",
            details={"expected": expected},
        )
