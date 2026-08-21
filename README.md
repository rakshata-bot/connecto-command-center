# Connecto Command Center — Streamlit

A daily video production dashboard that reads your Google Sheet and shows what's happening today, what's stuck, and what needs attention.

**Read-only** — no changes to your existing sheet or workflow.

---

## What you'll set up

1. GitHub account (2 min — you don't have one yet)
2. Upload this code to a private GitHub repo (5 min, all through the browser)
3. Streamlit Cloud account (2 min — free)
4. Deploy the app (2 min)
5. Paste secrets (3 min)

**Total: ~15 minutes.** Zero code editing. Zero terminal commands. Everything through your browser.

You'll also need the Google service account JSON file you already have from the earlier Vercel attempt.

---

## Part 1 — Create a GitHub account

1. Open **https://github.com/signup**
2. Enter your email → **Continue**
3. Create a password → **Continue**
4. Pick a username (e.g. `rakshata-connecto`) — this becomes part of your URL
5. Uncheck email marketing → **Continue**
6. Solve the picture puzzle → **Create account**
7. Enter the code sent to your email → **Continue**
8. On the "Welcome" screen, skip the survey questions (there's a "Skip personalization" link at the bottom)

You now have a GitHub account.

---

## Part 2 — Create a repository

A "repository" (or "repo") is just a folder that holds your code.

1. In the top-right, click the **+** icon → **New repository**
2. **Repository name:** `connecto-command-center`
3. **Description:** leave empty (or type "Video production dashboard")
4. Select **Private** (very important — this is your internal tool)
5. Check **Add a README file**
6. Click **Create repository**

You'll land on the empty repo page.

---

## Part 3 — Upload the app files

1. On the repo page, click **Add file** → **Upload files** (near the top-right)
2. In a separate window, unzip the `connecto-streamlit.zip` I sent (double-click on Mac)
3. Open the unzipped folder — you should see:
   - `app.py`
   - `requirements.txt`
   - `.gitignore`
   - `README.md`
   - a `.streamlit` folder (hidden on Mac — hit **Cmd+Shift+.** in Finder to show it)
4. **Drag ALL these files AND the .streamlit folder** into the GitHub upload area
5. Wait for them to upload (should show green checkmarks)
6. Scroll down → click the green **Commit changes** button

You should now see the files in your repo. If you see `app.py`, `requirements.txt` and a `.streamlit` folder listed on the page, you're good.

**If the `.streamlit` folder didn't upload:** on Mac, hidden folders (starting with `.`) don't upload via drag-and-drop by default. To fix:
   - Click **Add file** → **Create new file**
   - In the filename box, type: `.streamlit/config.toml`
   - Copy-paste the contents of `.streamlit/config.toml` from the unzipped folder (open it with TextEdit)
   - Click **Commit changes**

---

## Part 4 — Create a Streamlit Cloud account

1. Go to **https://share.streamlit.io/**
2. Click **Sign up** or **Continue with GitHub**
3. Authorize Streamlit to access your GitHub → **Authorize streamlit**
4. Fill out any survey questions (or skip)

You're in the Streamlit Cloud dashboard.

---

## Part 5 — Deploy the app

1. Click **Create app** (or **Deploy an app**) — top-right
2. Choose **Deploy a public app from GitHub** (even though your repo is private — Streamlit handles both)
3. Fill in:
   - **Repository:** `<your-username>/connecto-command-center`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** pick something like `connecto-command-center` (this becomes `connecto-command-center.streamlit.app`)
4. Click **Advanced settings** (small link near the deploy button)
5. In the **Secrets** section, paste this whole block (see Part 6 for exact format):

```toml
SHEET_ID = "1MwxvWyUzjW3ARdp_BbBtZPQZalJG15xI0sogdqPqEk0"
SHEET_TAB = "August Connecto"
BASIC_AUTH_USER = "editor"
BASIC_AUTH_PASS = "connecto2026"

GOOGLE_CREDENTIALS_JSON = """
{paste the entire contents of your JSON file here}
"""
```

For the GOOGLE_CREDENTIALS_JSON section, see the detailed steps below.

6. **Don't click Deploy yet** — finish Part 6 first.

---

## Part 6 — Paste your Google credentials into secrets

The Google service account JSON file lives in your Downloads folder (name like `connecto-dashboard-XXXXX.json`).

1. Open **Finder** → **Downloads**
2. Right-click the JSON file → **Open With** → **TextEdit**
3. In TextEdit, click anywhere in the text → **Cmd+A** (select all) → **Cmd+C** (copy)
4. Back in the Streamlit Cloud secrets box, click into the `GOOGLE_CREDENTIALS_JSON = """` block
5. Position your cursor **between the triple quotes** (`"""` and `"""`)
6. Replace `{paste the entire contents of your JSON file here}` with your copied JSON

The final secrets should look like this (with your actual JSON):

```toml
SHEET_ID = "1MwxvWyUzjW3ARdp_BbBtZPQZalJG15xI0sogdqPqEk0"
SHEET_TAB = "August Connecto"
BASIC_AUTH_USER = "editor"
BASIC_AUTH_PASS = "connecto2026"

GOOGLE_CREDENTIALS_JSON = """
{
  "type": "service_account",
  "project_id": "connecto-dashboard",
  "private_key_id": "bbd92f78...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvg...\n-----END PRIVATE KEY-----\n",
  "client_email": "connecto-dashboard-reader@connecto-dashboard.iam.gserviceaccount.com",
  ...
  "universe_domain": "googleapis.com"
}
"""
```

**No escaping needed. No copy-paste headaches. TOML triple-quotes preserve everything.**

Once the secrets look right, click **Deploy!**

---

## Part 7 — Wait for the build

Streamlit will:
1. Clone your repo
2. Install dependencies from `requirements.txt`
3. Run `streamlit run app.py`

You'll see build logs on the right. This takes ~2–3 minutes the first time.

When it's done, the app appears at `https://<your-app-name>.streamlit.app`.

---

## Part 8 — Log in

1. On the app page, you'll see the login screen
2. Enter:
   - **Username:** `editor`
   - **Password:** `connecto2026` (or whatever you set)
3. Click **Sign in**

The dashboard loads.

---

## Bookmark and share

- Bookmark the URL on your desktop and mobile
- Share the URL + login with your Senior Editor

That's it.

---

## Monthly maintenance (2 min on the 1st of each month)

You need to do two things at the start of every month:

### 1. Update SHEET_TAB in Streamlit Cloud secrets

1. Go to your Streamlit Cloud dashboard
2. Click your app → **Settings** → **Secrets**
3. Find the line `SHEET_TAB = "August Connecto"` and change to the new month (e.g. `"September Connecto"`)
4. Click **Save**
5. The app will auto-restart with the new value

### 2. Update monthly targets in `app.py`

1. In your GitHub repo, click on **app.py**
2. Click the pencil icon (top-right of the file) to edit
3. Find the `TARGETS` dictionary (around line 60)
4. Update `month_label`, `by_language`, and `by_type` for the new month
5. Scroll down → click **Commit changes**
6. Streamlit Cloud auto-redeploys within ~30 seconds

Or just tell me the new targets and I'll give you the updated `app.py` to paste.

---

## Updating the app code

Any change to `app.py` in your GitHub repo triggers an auto-redeploy in Streamlit Cloud. You never need to touch a terminal.

To edit code in the browser:
1. Go to your repo → click the file → click the pencil icon
2. Make changes → **Commit changes**
3. Wait ~30 seconds for auto-redeploy

---

## Troubleshooting

**"Couldn't load the sheet: Tab X not found"** — Your `SHEET_TAB` value doesn't match a tab in the Google Sheet. Check the tab name in Google Sheets and update the secret.

**"Wrong username or password"** — Check `BASIC_AUTH_USER` and `BASIC_AUTH_PASS` in secrets.

**Numbers look stale** — Click the **🔄 Refresh data** button in the top-right of the dashboard. The app caches sheet data for 5 minutes to keep things fast.

**App is slow to load the first time each day** — Streamlit Cloud apps go to sleep after inactivity. Waking up takes ~10 seconds. Normal.

**Sheet permission error** — Make sure the sheet is shared with your service account email (`connecto-dashboard-reader@connecto-dashboard.iam.gserviceaccount.com`) as a Viewer.

---

## What's in the app

- **Top strip** — added today, delivered today, in-flight, month-so-far vs target, days left
- **Insight line** — one-sentence auto-generated summary
- **Today's priorities** — top 5 auto-ranked action items (target gaps > backlog > aged > type pacing)
- **Editor workload** — per-editor today, this month, in-flight, 7d avg, status
- **Language production** — per-language today, this month, target, pace gap
- **Needs attention** — every in-flight video older than 2 days with editor and days aged
- **Recent activity** — last 7 days delivered counts + top language + top editor

All math is deterministic (no AI). Data cached 5 min. Refresh button clears cache.
