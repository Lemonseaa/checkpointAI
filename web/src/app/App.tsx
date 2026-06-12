import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "../layout/Layout";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { ApprovalDetailPage } from "../features/approvals/ApprovalDetailPage";
import { ApprovalListPage } from "../features/approvals/ApprovalListPage";
import { BackupPage } from "../features/backups/BackupPage";
import { AdapterListPage } from "../features/adapters/AdapterListPage";
import { AgentConfigPage } from "../features/agents/AgentConfigPage";
import { AutonomyPage } from "../features/autonomy/AutonomyPage";
import { NewRunPage } from "../features/runs/NewRunPage";
import { RunDetailPage } from "../features/runs/RunDetailPage";
import { RunListPage } from "../features/runs/RunListPage";
import { ScenarioListPage } from "../features/scenarios/ScenarioListPage";
import { ConfigVersionPage } from "../features/config/ConfigVersionPage";
import { EvidencePage } from "../features/evidence/EvidencePage";
import { EvidenceRunDetailPage } from "../features/evidence/EvidenceRunDetailPage";
import { WorkflowListPage } from "../features/evidence/WorkflowListPage";
import { ExternalAgentPage } from "../features/external-agents/ExternalAgentPage";
import { LearningPage } from "../features/learning/LearningPage";
import { ReportsPage } from "../features/reports/ReportsPage";
import { ShadowListPage } from "../features/shadows/ShadowListPage";
import { UserProfilePage } from "../features/settings/UserProfilePage";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="approvals" element={<ApprovalListPage />} />
        <Route path="approvals/:id" element={<ApprovalDetailPage />} />
        <Route path="evidence" element={<EvidencePage />} />
        <Route path="evidence/runs/:runId" element={<EvidenceRunDetailPage />} />
        <Route path="workflows" element={<WorkflowListPage />} />
        <Route path="runs" element={<RunListPage />} />
        <Route path="runs/new" element={<NewRunPage />} />
        <Route path="runs/:id" element={<RunDetailPage />} />
        <Route path="shadows" element={<ShadowListPage />} />
        <Route path="learning" element={<LearningPage />} />
        <Route path="autonomy" element={<AutonomyPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="backup" element={<BackupPage />} />
        <Route path="scenarios" element={<ScenarioListPage />} />
        <Route path="config" element={<ConfigVersionPage />} />
        <Route path="agent-config" element={<AgentConfigPage />} />
        <Route path="adapters" element={<AdapterListPage />} />
        <Route path="external-agents" element={<ExternalAgentPage />} />
        <Route path="profile" element={<UserProfilePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
