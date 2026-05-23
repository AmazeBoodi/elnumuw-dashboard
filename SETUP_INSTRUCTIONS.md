# Alnumuw Dashboard — Setup Guide

This guide walks you through the one-time setup needed after wiring the app to Google Drive and adding the password gate.

You will:

1. Upload your Excel workbook to Google Drive and copy its file ID
2. Add the file ID and a password to Streamlit Cloud Secrets
3. Push the updated code to GitHub
4. Test the deployed app

---

## Step 1 — Upload the Excel to Google Drive

1. Open Google Drive in your browser.
2. Upload `Alnumuw-MergedData.xlsx` (or whichever workbook your dashboard reads).
3. Right-click the file → **Share** → set access to **"Anyone with the link"** → role **"Viewer"** → click **Done**.
4. Right-click the file again → **Copy link**. The link looks like:

   ```
   https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz0123456/view?usp=sharing
   ```

5. Copy the **file ID** — it's the long string between `/d/` and `/view`. In the example above, the ID is:

   ```
   1AbCdEfGhIjKlMnOpQrStUvWxYz0123456
   ```

   Save this string — you'll paste it into Streamlit secrets in the next step.

**Important:** the share setting must be "Anyone with the link can view" or the app cannot download the file. Drive does not require sign-in for this mode, but the file is only discoverable to people who already have the file ID — which is effectively only your deployed app.

---

## Step 2 — Add secrets to Streamlit Cloud

1. Go to https://share.streamlit.io and open your app.
2. Click **⋯ → Settings → Secrets**.
3. Paste the following (replace the two placeholder values with your real ones):

   ```toml
   DRIVE_FILE_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456"
   APP_PASSWORD = "ChooseAStrongPasswordHere"
   ```

4. Click **Save**. Streamlit will automatically restart the app.

**Tip:** pick a password that's not used anywhere else. You can change it anytime by editing the secrets — no code change required.

---

## Step 3 — Push the updated code to GitHub

From your local machine, in the dashboard folder:

```bash
git add app.py requirements.txt SETUP_INSTRUCTIONS.md
git commit -m "Add password gate and Google Drive data loader"
git push
```

Streamlit Cloud detects the push and redeploys automatically (usually within 1–2 minutes).

---

## Step 4 — Test the deployed app

1. Open the Streamlit Cloud URL in a new browser tab (or incognito window so you start fresh).
2. You should see the **login screen** — enter the password you set in step 2.
3. After login, the app downloads the Excel from Drive (you'll see a "📥 Downloading latest data from Google Drive…" spinner once) and then shows the dashboard.
4. Check the **sidebar** — you should see:
   - 🔄 **Refresh data from Drive** — pulls the latest file (use this after updating the Excel on Drive)
   - ⚙️ **Upload custom file (override)** — lets you test a different file without touching Drive
   - 🚪 **Log out** — clears the password and returns to the login screen

---

## Daily workflow from now on

When you have new data to publish:

1. Open Drive, click the existing Excel file, click **⋮ → Manage versions → Upload new version** (this keeps the same file ID so nothing else needs to change).
2. Open the dashboard, click 🔄 **Refresh data from Drive** in the sidebar.
3. The new data appears immediately.

If you ever change the Excel file (delete it and upload a new one with a different ID), update `DRIVE_FILE_ID` in Streamlit secrets to the new ID.

---

## Local development

If you want to run the app on your own laptop with the same setup, create a file at `.streamlit/secrets.toml` (relative to the dashboard folder) with the same two values:

```toml
DRIVE_FILE_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456"
APP_PASSWORD = "ChooseAStrongPasswordHere"
```

Make sure `.streamlit/secrets.toml` is in your `.gitignore` so it never gets pushed to GitHub.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| "APP_PASSWORD is not configured in Streamlit secrets" | Secrets weren't saved | Re-check Settings → Secrets on Streamlit Cloud |
| "DRIVE_FILE_ID is not configured…" | Same as above for the Drive ID | Add `DRIVE_FILE_ID` to secrets |
| "Google Drive returned an empty response" | File share is set to "Restricted" | Change share to "Anyone with the link can view" |
| Old data still showing after Drive update | Cache hasn't expired (1 hour default) | Click 🔄 Refresh data from Drive in the sidebar |
| App crashes with memory error on Streamlit Cloud | Data file is too large for the free 1 GB tier | Either upgrade hosting or switch to Parquet / DuckDB (see scalability notes) |
