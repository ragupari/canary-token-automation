# 🦅 Canary Automation Tool (`canary-cmd`)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tooling: Rich](https://img.shields.io/badge/UI-Rich-brightgreen.svg)](https://github.com/Textualize/rich)

> **The Canary Automation Tool** is a high-performance orchestration engine designed for security professionals to conduct simulated phishing and insider-threat detection campaigns using professional-grade CanaryTokens.

---

## 📦 Quick Start: Running the Standalone Binary

The Canary Automation Tool is available as a standalone binary for Linux, allowing you to run campaigns without managing Python environments.

### 🚀 Execution
Ensure the binary has execution permissions:
```bash
chmod +x canary_automation
./canary_automation
```

### 🛠️ Workflow Summary
1.  **Prepare Input CSV**: Create a `targets.csv` with the following structure:
    | id | full_name | contact_email |
    | :--- | :--- | :--- |
    | 101 | John Doe | john.doe@example.com |
2.  **Run the Wizard**: Select `1. New Campaign` and follow the prompts for mapping and cover image injection.
3.  **Outcome**: Personalized `.xlsb` files and a critical `tracking_map.csv`.
4.  **Reporting**: Use Option 2 to view live triggers or export a professional **PDF Report**.

> 💡 **Tip**: The engine **checkpoints progress every 5 users**, so you can safely resume interrupted campaigns.


---

## 🌟 Key Features


### 🏗️ Campaign Orchestration
- **Dynamic Token Generation**: Interacts with the CanaryTokens API to create unique tracking tokens on the fly.
- **OOXML Injection**: Automatically embeds tracking beacons into Microsoft Excel (`.xlsb`) templates.
- **Custom Cover Branding**: Supports programmatic injection of cover images (e.g., `Confidential` banners) into generated documents.
- **Fault-Tolerant Pipelines**: Sequential `Canary_ID` generation and incremental checkpointing (saves progress every 5 users).

### 📊 Advanced Reporting
- **Live Monitoring**: Safely queries API trigger histories in real-time.
- **Intelligent Deduplication**: Filters redundant hits from the same IP within 10-second windows to prevent noise.
- **Professional PDF Exports**: Generates executive summaries with engagement rates and consolidated compromise logs.
- **Terminal UI**: Premium interactive interface powered by `Rich` and `Questionary`.

---

## 📸 Interface Preview

```text
  _____  _     _     _              _        __ 
 |  __ \| |   (_)   | |            | |  _   / / 
 | |__) | |__  _ ___| |__   ___  __| | (_) | |  
 |  ___/| '_ \| / __| '_ \ / _ \/ _` |     | |  
 | |    | | | | \__ \ | | |  __/ (_| |  _  | |  
 |_|    |_| |_|_|___/_| |_|\___|\__,_| (_) | |  
                                            \_\ 
                                                
   Create and manage canary tokens
```

---

## ⚙️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-username/canary-cmd.git
cd canary-cmd
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Build/Run (Development)
```bash
python canary_automation.py
```

### 4. Install as a Command
```bash
python setup.py install
# Then run anywhere using:
canary-cmd
```

---

## 🚀 Workflow Guide

### Phase A: Launching a Campaign
1. **Prepare Data**: Create a `users_input.csv` with target details (e.g., `id`, `name`, `email`).
2. **Select Option 1**: Follow the **Campaign Wizard**.
3. **Map Columns**: If your CSV headers differ, the tool will invite you to map the `email` and `name` fields interactively.
4. **Deploy**: The tool generates unique `.xlsb` files and a `tracking_map.csv` (store this securely!).

### Phase B: Analyzing Engagement
1. **Select Option 2**: Provide the `tracking_map.csv`.
2. **Review Triggers**: View a terminal summary or generate a **PDF Report**.
3. **Deep Dive**: Search for specific users to see their exact trigger timestamps and locations.

---

## 🛠️ Technical Architecture

### Core Engine
The system is built on a modular architecture:
- **`UI`**: Consistent, premium terminal experience.
- **`CanarySimulationTool`**: The functional heart, handling API sessions, retries, and document packaging.
- **`PDFReport`**: Custom FPDF wrapper for high-quality analytical output.

### The Injection Process
The tool utilizes `lxml` to perform low-level XML manipulation on the OOXML structure of `.xlsb` files:
1. Extracts the template.
2. Registers new content types in `[Content_Types].xml`.
3. Injects the media asset into `xl/media/`.
4. Updates drawing relationships and XML anchors to place the image as a full-screen cover.

### Deduplication Logic
To maintain report integrity, the engine uses a **Temporal Windowing Algorithm**:
- Hits are grouped by Source IP.
- If multiple hits from the same IP occur within a **10-second threshold**, they are merged into a single event, reflecting a single user opening the document (and potentially triggering multiple beacons).

---

## 📂 Project Structure

| File | Description |
| :--- | :--- |
| `canary_automation.py` | Main entry point & orchestration engine. |
| `DOCUMENTATION.md` | Internal help reference accessible via the tool. |
| `setup.py` | Package configuration and entry point definitions. |
| `requirements.txt` | Project dependencies. |
| `token_generation.py` | (Legacy/Standalone) Token generation logic. |
| `report_generation.py` | (Legacy/Standalone) Reporting logic. |

---

## 🛡️ Security & Ethics
This tool is intended for **authorized security awareness simulations** and **insider threat detection** only. Unauthorized use against targets without explicit consent is illegal. Users are responsible for complying with local regulations and privacy laws.

---

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📝 License
Distributed under the MIT License. See `LICENSE` for more information.

---

**Developed with ❤️ by [Parishith Ragumar](mailto:ragupari07@gmail.com)**
