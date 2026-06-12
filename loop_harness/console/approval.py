"""Unified approval inbox for V5 control surfaces."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from loop_harness.evidence import ReviewDecisionStatus, ReviewPackageDecisionStore
from loop_harness.optimization import (
    ParameterSuggestionStatus,
    ParameterSuggestionStore,
)
from loop_harness.prompt import (
    PromptProposalStatus,
    PromptProposalStore,
    ProposalStatus,
    ProposalStore,
)
from loop_harness.recommendation import RecommendationStatus, VersionRecommendationStore


class ApprovalItem(BaseModel):
    """One human-actionable item in the approval inbox."""

    id: str
    scenario_id: str
    item_type: str
    source_id: str
    title: str
    summary: str
    status: str
    recommended_action: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalInbox:
    """Aggregate and resolve human-actionable V5 items."""

    def __init__(self, db_path: str | Path) -> None:
        self.prompt_proposals = PromptProposalStore(db_path)
        self.generic_proposals = ProposalStore(db_path)
        self.recommendations = VersionRecommendationStore(db_path)
        self.parameter_suggestions = ParameterSuggestionStore(db_path)
        self.review_decisions = ReviewPackageDecisionStore(db_path)

    def list_items(self, scenario_id: str | None = None) -> list[ApprovalItem]:
        """List pending items across proposal and recommendation stores."""

        items: list[ApprovalItem] = []
        for proposal in self.prompt_proposals.list(scenario_id=scenario_id):
            if proposal.status not in {PromptProposalStatus.PROPOSED, PromptProposalStatus.APPROVED}:
                continue
            if proposal.status == PromptProposalStatus.APPROVED and not proposal.metadata.get(
                "awaiting_human_confirmation"
            ):
                continue
            items.append(
                ApprovalItem(
                    id=proposal.id,
                    scenario_id=proposal.scenario_id,
                    item_type="prompt_proposal",
                    source_id=proposal.id,
                    title=f"Prompt patch: {proposal.agent_id}.{proposal.patch.slot.value}",
                    summary=proposal.reason,
                    status=proposal.status.value,
                    recommended_action="review_prompt_patch",
                    created_at=proposal.created_at,
                )
            )
        for generic_proposal in self.generic_proposals.list(scenario_id=scenario_id):
            if generic_proposal.status not in {ProposalStatus.PROPOSED, ProposalStatus.APPROVED}:
                continue
            items.append(
                ApprovalItem(
                    id=generic_proposal.id,
                    scenario_id=generic_proposal.scenario_id,
                    item_type=f"{generic_proposal.proposal_kind.value}_proposal",
                    source_id=generic_proposal.id,
                    title=f"{generic_proposal.proposal_kind.value}: {generic_proposal.target_id}",
                    summary=generic_proposal.reason,
                    status=generic_proposal.status.value,
                    recommended_action="review_proposal",
                    created_at=generic_proposal.created_at,
                )
            )
        for recommendation in self.recommendations.list(scenario_id=scenario_id):
            if recommendation.status != RecommendationStatus.OPEN:
                continue
            items.append(
                ApprovalItem(
                    id=recommendation.id,
                    scenario_id=recommendation.scenario_id,
                    item_type="recommendation",
                    source_id=recommendation.id,
                    title=f"Recommendation: {recommendation.target_id}",
                    summary=recommendation.reason,
                    status=recommendation.status.value,
                    recommended_action=recommendation.recommended_action,
                    created_at=recommendation.created_at,
                )
            )
        for suggestion in self.parameter_suggestions.list(scenario_id=scenario_id):
            if suggestion.status != ParameterSuggestionStatus.OPEN:
                continue
            items.append(
                ApprovalItem(
                    id=suggestion.id,
                    scenario_id=suggestion.scenario_id,
                    item_type="parameter_suggestion",
                    source_id=suggestion.id,
                    title=f"Parameter suggestion: {suggestion.parameter_name}",
                    summary=suggestion.reason,
                    status=suggestion.status.value,
                    recommended_action="review_parameter_suggestion",
                    created_at=suggestion.created_at,
                )
            )
        for decision in self.review_decisions.list(
            scenario_id=scenario_id,
            status=ReviewDecisionStatus.PENDING,
        ):
            items.append(
                ApprovalItem(
                    id=decision.decision_id,
                    scenario_id=decision.scenario_id,
                    item_type="evidence_review_package",
                    source_id=decision.decision_id,
                    title=f"Evidence review package: {decision.package_id}",
                    summary=decision.reason,
                    status=decision.status.value,
                    recommended_action=decision.recommended_action,
                    created_at=decision.created_at,
                )
            )
        return sorted(items, key=lambda item: item.created_at)

    def approve(self, source_id: str, reason: str) -> bool:
        """Approve one item by source id."""

        _ = reason
        if self.prompt_proposals.get(source_id) is not None:
            return self.prompt_proposals.update_status(source_id, PromptProposalStatus.APPROVED)
        if self.generic_proposals.get(source_id) is not None:
            proposal = self.generic_proposals.get(source_id)
            if proposal is None:
                return False
            proposal.status = ProposalStatus.APPROVED
            return self.generic_proposals.save(proposal)
        if self.recommendations.get(source_id) is not None:
            return self.recommendations.update_status(source_id, RecommendationStatus.ACCEPTED)
        if self.parameter_suggestions.get(source_id) is not None:
            return self.parameter_suggestions.update_status(source_id, ParameterSuggestionStatus.ACCEPTED)
        if self.review_decisions.get(source_id) is not None:
            self.review_decisions.update_status(source_id, ReviewDecisionStatus.APPROVED, reason)
            return True
        return False

    def reject(self, source_id: str, reason: str) -> bool:
        """Reject one item by source id."""

        _ = reason
        if self.prompt_proposals.get(source_id) is not None:
            return self.prompt_proposals.update_status(source_id, PromptProposalStatus.REJECTED)
        if self.generic_proposals.get(source_id) is not None:
            proposal = self.generic_proposals.get(source_id)
            if proposal is None:
                return False
            proposal.status = ProposalStatus.REJECTED
            return self.generic_proposals.save(proposal)
        if self.recommendations.get(source_id) is not None:
            return self.recommendations.update_status(source_id, RecommendationStatus.REJECTED)
        if self.parameter_suggestions.get(source_id) is not None:
            return self.parameter_suggestions.update_status(source_id, ParameterSuggestionStatus.REJECTED)
        if self.review_decisions.get(source_id) is not None:
            self.review_decisions.update_status(source_id, ReviewDecisionStatus.REJECTED, reason)
            return True
        return False
