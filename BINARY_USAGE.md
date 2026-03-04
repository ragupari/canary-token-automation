# 📦 User Guide: Running the Canary Automation Binary

This guide explains how to use the standalone `canary_automation` binary to orchestrate security simulations without needing to install Python or manage dependencies manually.

---

## 🚀 Getting Started

If you have downloaded the compiled binary (e.g., `canary_automation`), ensure it has execution permissions:

```bash
chmod +x canary_automation
./canary_automation
```

---

## 🛠️ Step-by-Step Workflow

### Phase 1: Campaign Generation
This phase registers tokens and creates the tracked documents.

#### 1. Prepare your Input CSV
Create a file named `targets.csv`. It should look like this:

| id | full_name | contact_email |
| :--- | :--- | :--- |
| 101 | John Doe | john.doe@example.com |
| 102 | Jane Smith | jane.smith@example.com |

#### 2. Run the Wizard
Select **`1. New Campaign (Generate Tokens)`** from the main menu.

*   **File Path**: Enter `targets.csv`.
*   **Column Mapping**: If the tool doesn't recognize your headers, it will ask:
    > "Which column contains the Email Address?" -> Select `contact_email`.
    > "Which column contains the Name?" -> Select `full_name`.
*   **Cover Image**: Choose `cover.png` to add a "Confidential" overlay to the files.
*   **Output Directory**: Specify where to save the files (e.g., `Campaign_Q1_Files`).

#### 3. Expected Outcome
*   A folder `Campaign_Q1_Files/` containing:
    *   `Confidential_101.xlsb`
    *   `Confidential_102.xlsb`
*   A file named `tracking_map.csv` in your current directory. **DO NOT DELETE THIS FILE.**

---

### Phase 2: Engagement Reporting
This phase checks who opened the documents.

#### 1. Start the Report Engine
Select **`2. Report Gen (Previous Campaigns)`** and point to your `tracking_map.csv`.

#### 2. Generate a PDF Report
Select **`Generate Complete Report (PDF)`**. This is the most professional outcome.

**Expected Outcome:** 
A file `campaign_summary.pdf` is created with:
*   **Engagement Rate**: Percentage of users who opened the file.
*   **Trigger Logs**: Exact time, Source IP, and City/Country for every open event.

#### 3. Live Search
Select **`View Specific User (Email Search)`**. 
*   **Input**: `jane.smith@example.com`
*   **Result**: The terminal will display a panel showing if Jane opened the file, and if so, how many times.

---

## 💡 Pro-Tips for the Binary

### ⏸️ Resuming a Large Campaign
If you are generating 100+ tokens and the process is interrupted (e.g., network loss), simply run the tool again. Because the tool **checkpoints every 5 users**, your `tracking_map.csv` will contain all users processed up to that point.

### 🛡️ Understanding "Hits"
*   **The 10-Second Rule**: If a user opens a file and their antivirus scans it simultaneously, the API might see two hits. The binary automatically merges these into one "engagement event" if they happen within 10 seconds, keeping your report clean.

### 📁 Managing Output
Always keep the binary in the same folder as your `cover.png` and `DOCUMENTATION.md` for the best experience.

---

## ❓ FAQ

**Q: Does the binary send data to the internet?**  
A: Yes, it connects to `canarytokens.com` to register tokens and download the templates. It does not send your local CSV data anywhere else.

**Q: Can I run this on Windows/Mac?**  
A: This specific binary is for Linux. You would need the corresponding build for other operating systems.

---
*Generated for Canary Automation Tool v1.1.0*
