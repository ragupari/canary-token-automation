# Canary Security Automation Tool - System Documentation

## 1. System Overview
The Canary Security Automation Tool is a high-performance, terminal-based utility designed to orchestrate simulated phishing and insider-threat detection campaigns with professional-grade reporting.

The system leverages the CanaryTokens API to dynamically generate unique, heavily-tracked Microsoft Excel documents (`.xlsb`) for an arbitrary list of target users. Each target receives a personalized file. If a target opens the document, an invisible network beacon (hit) is triggered and silently dispatched to the CanaryTokens servers alongside data like their IP address, location, and user-agent string.

The tool manages two distinct operational phases:
1. **Campaign Generation**: Takes an input CSV of targets, registers tracking tokens via the API, injects them into an Office document template, and outputs ready-to-distribute files alongside a critical Master List (`tracking_map.csv`).
2. **Report Generation**: Reads the Master List, safely queries the API for live trigger histories, and generates actionable analytical reports (PDF/CSV/Terminal summaries).

---

## 2. Clear Examples & Workflows

### Phase A: Launching a New Campaign
If you want to create a new campaign:
1. **Execution**: Run the standalone binary: `./dist/canary_automation` (or `python3 canary_automation.py` if in dev).
2. Prepare an input CSV (e.g., `users_input.csv`) with columns: `id`, `name`, `email`.
    - **Header Mapping & Validation**: If your headers are different (e.g. `User_email` or `Email2`), the tool will automatically prompt you to map the correct field.
    - **Email Validation**: The tool strictly validates that values in the selected column are legitimate email addresses (supports `xx.xx@xx.xx`).
3. Select **1. New Campaign (Generate Tokens)**.
4. Follow the interactive prompts:
   - Provide the path to your CSV file.
   - **Internal ID Standard**: The tool automatically generates its own sequential **`Canary_ID`** (e.g., `CNRY-0001`, `CNRY-0002`...) for reliable internal tracking.
   - Supply a default **Assignee Email** (REQUIRED if not in CSV).
   - **Cover Image Injection**: Use the autocomplete prompt to select `cover.png` or `none` to skip.
   - Choose an output directory and base filename (e.g., `Confidential_Salary_Review`).
5. **Output**: The tool generates personalized `.xlsb` files for each user and securely saves the `tracking_map.csv`.

### Phase B: Generating Engagement Reports
To analyze a campaign that was launched previously:
1. Select **2. Report Gen (Previous Campaigns)** and provide the `tracking_map.csv` path.
2. Choose a report type:
   - **Generate Complete Report (PDF)**: (RECOMMENDED) Generates a professional PDF featuring:
     - **Executive Summary**: High-level stats and engagement rates.
     - **Consolidated Logs**: Detailed trigger events (IP, Time, Location) grouped and merged by user email for maximum readability.
   - **Overall Summary**: Prints a visual performance panel directly in the terminal.
   - **View Specific User (Email Search)**: Search strictly by user email using the interactive autocomplete search to see a specific person's trigger history.

---

## 3. Resilience & Engine Mechanics
- **Robust Exception Handling**: Major modules are wrapped in fail-safe logic. Errors are displayed via the UI and silently logged to `canary_automation.log` with full diagnostic details.
- **Master List Checkpointing**: Generating tokens is saved incrementally (every 5 users). If the process is interrupted, your progress is preserved in the tracking CSV.
- **Smart Tracking Map**: `Canary_ID` and `email` are mandatory for all exports. If you map a column during input, that original redundant column is automatically hidden from selection to keep your reports clean.
- **Temporal Gap Deduplication**: The engine automatically strips redundant hits. Multiple triggers from the same IP within a 10-second window are treated as a single engagement instance.
