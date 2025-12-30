# Canarytoken Automation Suite

This project contains scripts to automate generating `.xlsb` spreadsheets with canary tokens and to monitor those tokens.
---

## Project Files

```
.
├── token_generation.py      # Creates Canarytokens inside Excel files
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
* Required libraries: Refer `requirements.txt`

---

## Setup

### 1. Setup virtual env inside the folder and install the dependencies.
```
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 2. User Input File

Create `users_input.csv` with the following columns.

| Column Name | Description                    |
| ----------- | ------------------------------ |
| user_id     | Unique ID for the user         |
| user_name   | Full name                      |
| user_email  | Email of the user              |
| assignee    | Email to receive Canary alerts |

Place the exact details of the employees (victims to receive the phishing mail)

---

### 3. Cover Image

* Place your cover image in the project root
* Name it exactly:

```
cover.png
```

---

## How to Use

### Phase 1: Generate Excel Sheets with Canarytokens

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
Careful: 
* Do not open the generated `.xlsb` files.
* Do not change the `users_token.csv` file as it contains the unique links to manage each canary token which will be used later to generate report.

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
