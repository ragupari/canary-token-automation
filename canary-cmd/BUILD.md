# 🛠️ Build Guide: Canary Automation Tool

This project can be compiled into a standalone binary for Windows, macOS, and Linux. This allows users to run the tool without having Python installed.

---

## 🚀 Quick Start: GitHub Actions (Recommended)

The easiest way to get builds for all platforms is to use the included [GitHub Action](.github/workflows/build_binaries.yml).

1.  Push this repository to GitHub.
2.  Go to the **Actions** tab.
3.  Select **"Build Multi-Platform Binaries"**.
4.  Run the workflow manually or wait for a push to `main`.
5.  Download the artifacts (binaries) once the run completes.

---

## 💻 Local Build Instructions

If you prefer to build locally, follow these steps for your operating system.

### Prerequisites

-   Python 3.8+
-   `pip`
-   (Optional) A virtual environment

### 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install pyinstaller
```

### 2. Run PyInstaller

#### **On Linux / macOS:**
```bash
pyinstaller --onefile --name canary-automation-$(uname -s | tr '[:upper:]' '[:lower:]') --add-data "DOCUMENTATION.md:." canary_automation.py
```

#### **On Windows (Command Prompt):**
```cmd
pyinstaller --onefile --name canary-automation-win --add-data "DOCUMENTATION.md;." canary_automation.py
```

#### **On Windows (PowerShell):**
```powershell
pyinstaller --onefile --name canary-automation-win --add-data "DOCUMENTATION.md;." canary_automation.py
```

---

## 📦 What's Included?

The build process:
-   Bundles all Python dependencies into a single file.
-   Includes `DOCUMENTATION.md` inside the binary for the internal help menu.
-   Creates the executable in the `dist/` folder.

**Note:** External assets like `cover.png` and `targets.csv` should be kept in the same directory as the binary for the best experience.

---

## 🧪 Testing the Binary

Once built, you can find the executable in the `dist/` directory.

```bash
cd dist
./canary-automation-linux
```

---
*Created for Canary Automation Tool v1.1.0*
