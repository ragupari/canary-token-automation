# 🛠️ Canary Security Automation - Developer Technical Reference

## 1. System Philosophy
The Canary Security Automation Tool is designed as a robust, idempotent, and user-centric platform for managing canary document lifecycles. It prioritizes **UI elegance** and **Execution reliability**.

---

## 2. Core Architecture

### 2.1 API Integration (`CanaryTokens`)
The tool interacts with the `canarytokens.com` API.
- **Base URL**: `https://canarytokens.com`
- **Default API ID**: `d3aece8093b71007b5ccfedad91ebb11`
- **Endpoints Used**:
    - `POST /{api_id}/generate`: Register a new token and associate it with a memo (CID + Name).
    - `GET /{api_id}/download`: Fetch the pre-configured `.xlsb` document.
    - `GET /{api_id}/history`: Retrieve trigger incidents for a specific token.

### 2.2 Document Injection Engine
Located primarily in `canary_automation._inject_cover_image`, this module handles the modification of Microsoft Office XLSB (Binary) containers. Since XLSB is a ZIP-based OOXML container, we treat it as such:
1. **Unzipping**: The file is extracted to a temporary directory.
2. **Schema Compliance**: Namespaces (CT, REL, DRAW, A, R) are strictly followed to ensure Excel doesn't flag the file as "Corrupted".
3. **Anchor Logic**: Images are injected using a `twoCellAnchor` set to "absolute", ensuring they behave as a static cover page across different screen sizes.

### 2.3 Resiliency Mechanics
- **Tenacity Retries**: API calls are wrapped in `tenacity` retry loops with exponential backoff (2, 4, 8... seconds) to handle network instability or rate limiting.
- **Checkpointing**: In `run_campaign_wizard`, results are written to the tracking CSV every 5 processed users. This prevents data loss in case of crashes or interruptions.
- **Temporal Deduplication**: Triggers from the same IP within a 10s gap are merged. This is critical because some Office versions or virus scanners may trigger multiple network beacons upon a single document open event.

---

## 3. Workflow Implementation Details

### Campaign Generation Pipeline
1. **Input Validation**: CSV is read using `csv.DictReader`. Mandatory email validation is performed via Regex.
2. **ID Mapping**: Sequential `Canary_ID` (format `CNRY-XXXX`) is assigned for internal tracking.
3. **API Handshake**: A `generate` call is sent for each user.
4. **Asset Procurement**: The document is downloaded and stored locally.
5. **Injection (Optional)**: If a cover image is selected, it's injected into the document.
6. **State Tracking**: `tracking_map.csv` is updated with keys: `Canary_ID`, `email`, `auth_token`, `canary_token`, `manage_url`, and `file_path`.

### Reporting Engine
1. **Batch Fetching**: Tokens are checked in parallel (polite delay used).
2. **Hit Normalization**: Raw API hits are converted to a clean dictionary format (Time, IP, City, Country, User-Agent).
3. **PDF Compilation**:
    - **Header/Footer**: Custom branding.
    - **Summary Table**: High-level status for all users.
    - **Detailed Logs**: Grouped by email, merging the first column for visual clarity.

---

## 4. Maintenance & Extensions

### Adding New Token Types
To add support for PDF or Word Canaries:
1. Update `CanarySimulationTool.generate_canary_asset` to accept a `token_type` parameter.
2. Modify `package_document` to handle different file extensions (e.g., `.docx`, `.pdf`).
3. Note: PDF injection would require a different library logic (e.g., `PyMuPDF`) compared to OOXML manipulation.

### Modifying UI Styles
All UI elements are centralized in the `UI` class. To change color palettes or rules, update the static methods within `canary_automation.py`.

---

## 5. Security & Privacy
- **No API Keys in Logs**: Sensitive API tokens (`auth_token`) are stored in `tracking_map.csv` but should never be printed in logs.
- **Local Data Privacy**: Tracking maps contain mapping between real employee emails and canary links. These files should be treated as **Highly Confidential**.

---
*Document Version: 1.1.0 | Last Updated: March 2026*
