# Lovable Prompt: Onyx UI Redesign

*Copy and paste the text below into Lovable to generate the frontend layout.*

---

**Prompt:**

Build a professional, deep-analysis cybersecurity platform dashboard called "Onyx". This is a "War Game Dreamer" tool that simulates thousands of attacks to find the best vulnerabilities to patch. 

Do not focus on specific colors or themes; focus strictly on layout, structure, and professional data visualization components. The application must support a responsive sidebar navigation and a top header.

The application must cater to Role-Based Access Control (RBAC), meaning different roles (Executive, SOC Analyst, Security Architect) will see different primary views or have certain actions restricted.

Include the following pages, sections, and UI components:

### 1. Global Layout & Navigation
*   **Sidebar Navigation:** Links to Dashboard, Network Map, War Game Simulations, Patch Optimizer, and Telemetry Feed. 
*   **Top Header:** Contains a global search bar (for CVEs or IP addresses), a live "Active Alerts" ticker, and a Role Selector dropdown (Executive, SOC Analyst, Security Architect) to preview different RBAC states.

### 2. Executive Dashboard (Default view for 'Executive' role)
*   **Overview Widgets:** High-level metrics such as "Current Network Risk Score", "Overnight Simulations Run", "Attack Success Rate", and "Critical Assets Compromised".
*   **ROI Summary Chart:** A chart showing the estimated risk reduction versus engineering effort for the top recommended patches.
*   **Recent Reports Feed:** A list of the latest generated Morning Reports with download buttons.
*   *RBAC Note:* This view should hide complex simulation controls and focus only on high-level outcomes and reporting.

### 3. Network Topology & Live Analysis (For Analysts & Architects)
*   **Interactive Graph Canvas:** The central piece of this page is a large area for visualizing network nodes and edges.
*   **Node Inspector Panel:** A detailed, collapsible right-side panel that opens when a node is clicked. It should display Node ID, Type, Critical Asset toggle, and a list of attached CVE vulnerabilities with their CVSS scores and attack vectors.
*   **Topology Builder:** A drag-and-drop interface area/toolbar on the left side of the canvas allowing users to drag new nodes (servers, firewalls, routers) onto the canvas and connect them to build custom topologies.

### 4. War Game Simulation Center (For Analysts & Architects)
*   **Simulation Controls:** A control panel to configure and launch simulations. Includes inputs for "Number of Episodes", "Data Source" (Simulation vs Live Telemetry), and a "Telemetry Weighting" slider.
*   **Progress Dashboard:** A real-time progress bar and a live chart showing the Red Agent (Attacker) vs Blue Agent (Defender) win rates over time.
*   **Attack Replay Viewer:** A dedicated section featuring an interactive timeline slider to step forward and backward through a simulated attack episode frame-by-frame, highlighting the compromised nodes on a mini-map.
*   *RBAC Note:* The 'Run Simulation' button should be disabled for the Executive role.

### 5. Patch Optimization & ROI (For Architects)
*   **Prioritized Action Table:** A dense, professional data grid listing the top recommended patches. Columns should include: Rank, Node, CVE ID, CVSS Score, Simulation Impact (Risk Reduction %), Effort (Hours), and ROI Score.
*   **Explainability Cards:** Clicking a row in the table expands a card below it that justifies the recommendation (e.g., "This node appears in 80% of top attack paths", "Critical asset bottleneck").
*   *RBAC Note:* Only the Security Architect role can adjust the "Cost Model" parameters (Node type effort hours, Critical asset multipliers) via a settings modal on this page.

### 6. Telemetry & Data Ingestion (For Analysts)
*   **Live Event Feed:** A scrolling, terminal-like or dense table feed of live network events (e.g., process creation, network connections, firewall blocks).
*   **Agent Status Grid:** A small grid showing connected laptops/sensors (e.g., "Sysmon Forwarder - Laptop B") and their last heartbeat timestamp.
*   **Data Health Metrics:** Counters for "Events Ingested Today" and "Blocked Attacks".

Make the interface feel like a dense, high-tier cybersecurity tool used in enterprise SOCs (Security Operations Centers). Use robust data tables, clear metric cards, collapsible sidebars, and dedicated spaces for complex graphs.
