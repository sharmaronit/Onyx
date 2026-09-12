# Frontend Pages and Features

## Global Navigation
- App shell with top navigation.
- Links to:
  - Dashboard
  - Analysis
  - Training
  - Reports
- Global role selector for user mode switching.
- Global Quick Demo button for loading a preset analysis flow.

## 1. Dashboard Page
### Purpose
- Provide the main landing page and a quick summary of the platform.

### Features
- Executive overview title and short platform summary.
- Infrastructure metrics cards showing:
  - Network nodes
  - Connections
  - Known CVEs
  - Critical assets
- Recent activity section for the latest simulation or analysis runs.
- Optional demo scenarios section.
- Optional quick links section to other main areas.
- Optional current role info card.

### Buttons and Actions
- Get Started
- New Analysis
- Run Analysis on a scenario card
- Optional quick-link cards that navigate to:
  - Run Simulation
  - Attack Analysis
  - MARL Results
  - Generate Report

## 2. Analysis Page
### Purpose
- Run simulations, scenario-based analysis, patch optimization, and replay review.

### Features
- Control panel for configuring an analysis run.
- Topology selector.
- Optional demo scenario selector.
- Episode count input.
- Data source selector.
- Telemetry weight slider.
- Tabbed analysis workspace.
- Toast messages for success, error, and info states.

### Buttons and Actions
- Run Analysis
- Clear Results
- Optional Apply Judge Hybrid Preset
- Optional Load Telemetry Sample
- Optional Telemetry Status

### Tabs and Required Content
#### Simulation Results Tab
- Show analysis source and freshness.
- Show attack success rate.
- Show total episodes.
- Show attack paths found.
- Show result summary and data source notes.

#### Attack Analysis Tab
- List top attack paths.
- Show path frequency and count.

#### Patch Optimization Tab
- Baseline episodes input.
- Evaluation episodes per patch input.
- Run Patch Optimization button.
- Results table with patch, CVE, impact, and cost.

#### Red vs Blue / MARL Tab
- Show MARL training summary.
- Show round-by-round results table.

#### Replay Timeline Tab
- Show incident replay steps.
- Present timeline entries in order.

## 3. Training Page
### Purpose
- Review MARL progress and manage training-related workflows.

### Features
- Tabbed training area.
- MARL results summary.
- Optional cost models tab.
- Optional training jobs tab.
- Toast messages for training actions.

### Buttons and Actions
- MARL Arms Race tab button
- Optional Cost Models tab button
- Optional Training Jobs tab button
- Edit cost model button
- Activate cost model button
- Create Model button
- Queue Job button

### Required Content by Tab
#### MARL Arms Race Tab
- Training status.
- Rounds completed.
- Red win rate.
- Blue win rate.
- Training convergence visualization placeholder.

#### Cost Models Tab
- List of cost models.
- Active or inactive status badges.
- Create new cost model form.
- Model name input.
- Description input.
- Edit and Activate actions per model.

#### Training Jobs Tab
- List of training jobs.
- Job status and progress bar.
- Job type selector.
- Episodes input.
- Queue new training job controls.

## 4. Reports Page
### Purpose
- Review, generate, view, and export reports based on simulations.

### Features
- Tabbed report workspace.
- Report list table.
- Report viewer.
- Optional export section.
- Toast messages for generation and export actions.

### Buttons and Actions
- Generate New Report
- View report
- Print
- Optional Download PDF
- Optional Export tab button
- Export CSV
- Export JSON
- Export PDF
- Custom Export

### Required Content by Tab
#### Report List Tab
- Table of generated reports.
- Report name.
- Topology.
- Success rate.
- Source.
- Confidence.
- Created date.
- View action for each report.

#### Viewer Tab
- Selected report header.
- Executive summary.
- Key findings list.
- Recommendations list.
- Print action.
- Optional PDF download action.

#### Export Tab
- Export format cards.
- CSV export.
- JSON export.
- PDF bundle export.
- Advanced export options with checkboxes.
- Custom Export button.

## 5. Shared UI Behavior
- Show disabled states when the current role does not allow an action.
- Show permission messages when access is restricted.
- Keep analysis and training state across pages through shared context.
- Preserve selected topology, scenario, and results during navigation where possible.
- Use toast notifications for status feedback.

## 6. Optional Feature-Gated Controls
These controls exist in the codebase but are hidden unless feature flags are enabled.
- Role selector in the navbar.
- Quick Demo button in the navbar.
- Dashboard demo scenario cards.
- Dashboard quick links section.
- Dashboard role card.
- Analysis scenario selector.
- Analysis judge preset button.
- Analysis telemetry utility buttons.
- Training cost models tab.
- Training jobs tab.
- Reports export tab.
- Reports download PDF button
