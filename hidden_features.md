# Hidden Frontend Features

This file tracks frontend features intentionally hidden for production UI simplification.

| Feature | File | Hide Mechanism | Reason | Re-enable |
|---|---|---|---|---|
| Role selector dropdown | web/src/components/Navbar.jsx | `FEATURE_VISIBILITY.showRoleSelector = false` | Remove role-switching from production UX | Set to `true` |
| Quick Demo button | web/src/components/Navbar.jsx | `FEATURE_VISIBILITY.showQuickDemoButton = false` | Remove demo-only action from production nav | Set to `true` |
| Demo scenarios panel | web/src/pages/Dashboard.jsx | `FEATURE_VISIBILITY.showDashboardScenarios = false` | Hide non-essential demo cards | Set to `true` |
| Quick links section | web/src/pages/Dashboard.jsx | `FEATURE_VISIBILITY.showDashboardQuickLinks = false` | Reduce visual clutter | Set to `true` |
| Current role info card | web/src/pages/Dashboard.jsx | `FEATURE_VISIBILITY.showDashboardRoleCard = false` | Remove role-oriented/non-technical info | Set to `true` |
| Demo scenario selector | web/src/pages/AnalysisHub.jsx | `FEATURE_VISIBILITY.showScenarioSelector = false` | Remove demo-oriented control from analysis flow | Set to `true` |
| Judge preset button | web/src/pages/AnalysisHub.jsx | `FEATURE_VISIBILITY.showJudgePresetButton = false` | Remove demo-specific shortcut | Set to `true` |
| Telemetry utility buttons | web/src/pages/AnalysisHub.jsx | `FEATURE_VISIBILITY.showTelemetryUtilityButtons = false` | Reduce advanced utility clutter | Set to `true` |
| Cost Models tab | web/src/pages/Training.jsx | `FEATURE_VISIBILITY.showTrainingCostModelsTab = false` | Hide admin panel while keeping MARL tab visible | Set to `true` |
| Training Jobs tab | web/src/pages/Training.jsx | `FEATURE_VISIBILITY.showTrainingJobsTab = false` | Hide admin/job queue panel | Set to `true` |
| Reports Export tab | web/src/pages/Reports.jsx | `FEATURE_VISIBILITY.showReportsExportTab = false` | Hide extra export UI for production simplicity | Set to `true` |
| Download PDF button | web/src/pages/Reports.jsx | `FEATURE_VISIBILITY.showDownloadPdfButton = false` | Hide in-progress/non-core action | Set to `true` |

## Notes

- Hidden features are still present in code and can be restored via `web/src/config/featureVisibility.js`.
- Production currently enforces role capabilities using `FEATURE_VISIBILITY.enforcedRole = 'architect'` to keep core features working without exposing role selection in UI.