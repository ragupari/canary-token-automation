# Canarytoken Automation Suite

This project helps you **create, deploy, and monitor MS Excel Canarytokens at scale**. It automates token creation, adds a **Confidential-looking cover image** to make files more believable, and produces **clear audit reports** when a file is opened.

---

## What This Tool Does

In simple terms:

* Generates **unique Excel Canarytoken files** for multiple users
* Makes the files look **legitimate and sensitive** by adding a Confidential cover image
* Monitors when a file is opened
* Produces a **clean report** showing who triggered which file, when, and from where

---

## Key Features

* **Batch Generation**
  Create Excel Canarytokens for many users automatically.

* **Confidential Cover Image**
  Injects a full-page cover image into Excel files to increase open rates.

* **Reliable API Handling**
  Uses retry logic to handle network issues or API rate limits.

* **Clean Audit Reports**
  Logs timestamps and source IPs, removing duplicate triggers from the same IP in a short time window.

* **CSV-Based Tracking**
  All progress and results are stored in CSV files for easy review and automation.

---

## Project Files

```
.
├── token_generation.py      # Creates Canarytokens and Excel files
├── report_generation.py     # Checks which tokens were triggered
├── users_input.csv          # Input list of users (required)
├── cover.png                # Confidential cover image (required)
├── users_token.csv          # Generated token details (auto-created)
├── triggered_report.csv     # Final trigger report (auto-created)
└── generated_tokens/        # Output Excel files
```

---

## Requirements

* Python **3.8 or higher**
* Required libraries:

```
pip install requests lxml tenacity urllib3
```

---

## Setup

### 1. API Key

Open both Python scripts and set your Canarytokens API key:

```
API_ID = "YOUR_CANARY_API_KEY"
```

### 2. User Input File

Create `users_input.csv` with the following columns:

| Column Name | Description                    |
| ----------- | ------------------------------ |
| user_id     | Unique ID for the user         |
| user_name   | Full name                      |
| assignee    | Email to receive Canary alerts |

---

### 3. Cover Image

* Place your cover image in the project root
* Name it exactly:

```
cover.png
```

---

## How to Use

### Phase 1: Generate Excel Canarytokens

Run:

```
python token_generation.py
```

What happens:

* Calls the Canarytokens API
* Downloads the Excel Canarytoken file
* Unzips the Excel file
* Injects the Confidential cover image
* Repackages the file

Output:

* Excel files are saved in:

```
generated_tokens/
```

* Token details are saved in:

```
users_token.csv
```

---

### Phase 2: Monitor for Triggers

Run:

```
python report_generation.py
```

What happens:

* Reads token data from `users_token.csv`
* Queries the Canarytokens management API
* Deduplicates multiple triggers from the same IP within 10 seconds

Output:

* Results are written to:

```
triggered_report.csv
```

Each entry shows:

* Whether the file was opened (`true / false`)
* Timestamp(s)
* Source IP address(es)

---

## How It Works (High-Level)

### Excel Modification

Excel files are ZIP archives. The script:

* Registers the cover image in `[Content_Types].xml`
* Links the image via Excel drawing relationships
* Places the image as a **fixed full-page cover** that cannot move or resize

---

### Trigger Analysis

* Multiple opens from the **same IP within 10 seconds** count as one event
* A small delay is added between API calls to avoid rate limits

---

## Legal & Ethical Notice

This tool is intended for:

* Authorized security testing
* Internal audits
* Education and research

**Do not use this tool without explicit permission.** Unauthorized deployment of Canarytokens may violate laws or organizational policies.

---

## Summary

This suite provides a **simple, reliable, and professional way** to:

* Deploy Excel-based Canarytokens in bulk
* Increase realism with visual camouflage
* Monitor access with clean, actionable reports
