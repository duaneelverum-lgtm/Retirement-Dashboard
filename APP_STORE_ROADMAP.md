# 📱 Technical Strategy & Roadmap
### For: The Retirement Dashboard Project
**Date:** January 23, 2026
**Status:** Professional Prototype (Version 28)
**Current Phase:** User Validation / Logic Lockdown

---

## 1. Executive Summary
The project has successfully reached **Version 28**, a milestone that marks the completion of the core logic engine. We now have a "Financial Digital Twin" that accurately models sophisticated retirement scenarios.

**Key Achievement:** We have successfully separated the application into a **Launchable Demo** (for safe sharing) and a **Private Dashboard** (for personal data).

---

## 2. Current Capabilities (The "Logic Engine")
We have built a robust mathematical core that is superior to most standard banking apps.

### ✅ Completed & Tested Features:
*   **Net Worth Tracking:** Automatic asset vs. liability calculation.
*   **"How Long Will It Last?" Engine:** 
    *   *Real-time simulation* of drawdown across 60+ years.
    *   *Sophisticated Inputs:* Handles variable monthly expenses, inflation, and market returns.
    *   *Event Injection:* Successfully models future one-time cash events (Inheritance) and recurring income streams (CPP/OAS).
*   **Demo Mode:** A privacy-first version of the app (`dashboard_demo.py`) that resets on reload.

### 🚧 Technical Debt (To Address Later):
*   **Platform Limit:** Currently running on Streamlit (Python). Good for prototyping, not for App Store (yet).
*   **Local Data:** Data is stored in `finance.json`. A production app will need Cloud/Keychain storage.

---

## 3. The Roadmap: Path to App Store
We are currently in **Phase 2**.

### Phase 1: Logic & Prototyping (COMPLETED ✅)
*   **Goal:** Build a calculator that *actually works*.
*   **Status:** Done (Version 28).

### Phase 2: User Validation / "The Grandma Test" (CURRENT 📍)
*   **Objective:** Confirm that the "Number" makes emotional sense to users.
*   **Action:** Deploy the **Demo Version** to a private URL and send it to trusted testers.

### Phase 3: The Native Build (Future)
*   **Objective:** Convert into a native iOS Application (Swift).

---

## 4. How to Launch the Web Pilot (Get a URL)

This is the exact sequence to get your prototype into testers' hands *today*.

### 🛠 Step-by-Step Guide

Follow these exact steps to get a URL (e.g., `https://my-app.streamlit.app`) you can text to people.

1.  **Prepare the Code:**
    *   Locate `financial_dashboard/dashboard_demo.py` (which we created for you).
    *   *Alternatively:* Open `dashboard.py`, change Line 22 to `DEMO_MODE = True`, and save.
    
2.  **Create GitHub Account (The "Storage" Locker):**
    *   Go to `github.com` -> Sign Up (Free).
    *   Click the **+** icon (top right) -> "New Repository".
    *   Repository name: `my-retirement-app`.
    *   Scroll down -> Click **Create repository**.
    *   Click "uploading an existing file" link.
    *   Drag and drop these files (from your `financial_dashboard` folder):
        *   `dashboard_demo.py` (Rename this to `dashboard.py` after uploading, or just select `dashboard.py` if you edited it).
        *   `requirements.txt` (This is in the main folder).
        *   `file_parser.py`
        *   `csv_parser.py`
    *   Click **Commit changes**.

3.  **Deploy to Streamlit Community Cloud (The "Server"):**
    *   Go to `share.streamlit.io` -> Sign Up with GitHub.
    *   Click **New App**.
    *   "Repository": Select `my-retirement-app`.
    *   "Main file path": `dashboard.py` (or `dashboard_demo.py` if you uploaded that).
    *   Click **Deploy!**

4.  **Send the Link:**
    *   In 2 minutes, you will see your app on the screen.
    *   Copy the URL/Link at the top.
    *   Text it to your tester. "Click this. Tell me what you feel."

5.  **Safety Check:**
    *   Because `DEMO_MODE = True`, they CANNOT save their data or see your data. It resets every time they refresh. It is safe.
