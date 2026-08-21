"""
Connecto Command Center — Daily video production dashboard.

Reads the delivery sheet and shows:
- Today's counters
- Priorities (auto-ranked)
- Editor workload
- Language production vs targets
- In-flight items aged >2 days
- Recent activity

All configuration lives in Streamlit secrets (.streamlit/secrets.toml locally
or the Streamlit Cloud secrets UI). See README for setup.
"""

import calendar
import json
from collections import Counter
from datetime import date, datetime, timedelta

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials


# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Connecto Command Center",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Minimal CSS to tighten spacing and warm up the palette
st.markdown(
    """
<style>
.main .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px;}
h1 {font-weight: 500 !important;}
h2 {font-weight: 500 !important; font-size: 1.15rem !important; margin-top: 0.5rem !important;}
[data-testid="stMetric"] {
    background: #FFFFFF; border-radius: 8px; padding: 0.9rem 1rem;
    border: 1px solid #E8E6E0;
}
[data-testid="stMetricValue"] {font-size: 1.5rem; font-weight: 500;}
[data-testid="stMetricLabel"] {color: #6B6862; font-size: 0.8rem;}
[data-testid="stMetricDelta"] {font-size: 0.75rem;}
div[data-testid="stExpander"] {border: 1px solid #E8E6E0;}
</style>
    """,
    unsafe_allow_html=True,
)


# ============================================================================
# MONTHLY TARGETS
# Update these at the start of each month.
# ============================================================================

LANGUAGES = ["Hindi", "Bengali", "Tamil", "Kannada", "Telugu", "Malayalam"]

TARGETS = {
    "month_label": "August 2026",
    "by_language": {
        "Hindi": 340, "Bengali": 25, "Tamil": 330,
        "Kannada": 335, "Telugu": 335, "Malayalam": 305,
    },
    "by_type": {
        "Faceswap": 100,
        "UGC": 110,
        "AI-Agency": 110,
        "AI-Inhouse": 670,
        "Purple Bell": 80,
        "Format Experimentation": 50,
        "Static": 110,
        "Agency": 0,
    },
    # As displayed on the sheet's total row (Static row is understated).
    "month_total_as_shown": 1120,
    # Mathematically-correct total if Static In-House is summed per-language.
    "month_total_corrected": 1560,
}


# ============================================================================
# AUTHENTICATION
# ============================================================================

def check_auth() -> bool:
    """Simple username/password gate stored in st.secrets."""
    if st.session_state.get("auth_ok"):
        return True

    st.title("Connecto Command Center")
    st.write("Please sign in.")
    with st.form("login", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign in", type="primary")
        if submit:
            if (
                username == st.secrets.get("BASIC_AUTH_USER")
                and password == st.secrets.get("BASIC_AUTH_PASS")
            ):
                st.session_state["auth_ok"] = True
                st.rerun()
            else:
                st.error("Wrong username or password.")
    return False


# ============================================================================
# SHEET LOADING
# ============================================================================

@st.cache_data(ttl=300, show_spinner="Loading data from Google Sheet…")
def load_sheet_rows():
    """
    Fetch rows from the current-month tab.
    Cached for 5 minutes. Manual refresh clears the cache.
    Returns (rows_list, actual_tab_title).
    """
    creds_json = json.loads(st.secrets["GOOGLE_CREDENTIALS_JSON"])
    creds = Credentials.from_service_account_info(
        creds_json,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(st.secrets["SHEET_ID"])

    # Auto-find the tab: handles whitespace/case differences.
    wanted = st.secrets["SHEET_TAB"].strip().lower()
    tab = None
    for ws in sh.worksheets():
        if ws.title.strip().lower() == wanted:
            tab = ws
            break
    if tab is None:
        # Fallback: substring match
        for ws in sh.worksheets():
            if wanted in ws.title.strip().lower():
                tab = ws
                break
    if tab is None:
        available = [ws.title for ws in sh.worksheets()]
        raise ValueError(
            f"Tab '{st.secrets['SHEET_TAB']}' not found. "
            f"Available tabs: {available}"
        )

    rows = tab.get_all_records(head=1, default_blank="")
    return rows, tab.title


def parse_date(s):
    """Parse DD-MM-YYYY. Return None on any oddity."""
    if not s:
        return None
    try:
        return datetime.strptime(str(s).strip(), "%d-%m-%Y").date()
    except (ValueError, AttributeError):
        return None


def normalize_rows(raw_rows):
    """Clean and normalize sheet rows into a list of dicts we can analyze."""
    out = []
    skipped = 0
    for r in raw_rows:
        d = parse_date(r.get("Date"))
        if not d:
            skipped += 1
            continue
        editor = str(r.get("Video Editor", "")).strip() or None
        status_raw = str(r.get("Video Status", "")).strip().lower()
        out.append({
            "date": d,
            "type": str(r.get("Type", "")).strip(),
            "language": str(r.get("Language", "")).strip(),
            "editor": editor,
            "script": str(r.get("Script name", "")).strip() or "(no script name)",
            "status": "Delivered" if status_raw == "delivered" else "in-flight",
        })
    return out, skipped


# ============================================================================
# ANALYTICS
# ============================================================================

def days_between(later, earlier):
    return (later - earlier).days


def in_same_month(row, today):
    return row["date"].year == today.year and row["date"].month == today.month


def compute_today_counts(rows, today):
    yesterday = today - timedelta(days=1)
    month_rows = [r for r in rows if in_same_month(r, today)]
    month_delivered = sum(1 for r in month_rows if r["status"] == "Delivered")

    added_today = sum(1 for r in rows if r["date"] == today)
    delivered_today = sum(1 for r in rows if r["date"] == today and r["status"] == "Delivered")
    delivered_yday = sum(1 for r in rows if r["date"] == yesterday and r["status"] == "Delivered")

    inflight = [r for r in rows if r["status"] == "in-flight"]
    inflight_total = len(inflight)
    inflight_urgent = sum(1 for r in inflight if days_between(today, r["date"]) > 4)

    # 7-day average delivered
    seven_day = 0
    for i in range(7):
        d = today - timedelta(days=i)
        seven_day += sum(1 for r in rows if r["date"] == d and r["status"] == "Delivered")
    avg_7d = round(seven_day / 7, 1)

    # Month pacing
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_left = max(0, days_in_month - today.day)
    target = TARGETS["month_total_as_shown"]
    remaining = max(0, target - month_delivered)
    daily_required = -(-remaining // max(1, days_left))  # ceil

    return {
        "added_today": added_today,
        "delivered_today": delivered_today,
        "delivered_yday": delivered_yday,
        "inflight_total": inflight_total,
        "inflight_urgent": inflight_urgent,
        "month_delivered": month_delivered,
        "month_target": target,
        "days_left": days_left,
        "daily_required": daily_required,
        "avg_7d": avg_7d,
    }


def compute_editor_workload(rows, today):
    editors = sorted({r["editor"] for r in rows if r["editor"]})
    result = []
    for e in editors:
        mine = [r for r in rows if r["editor"] == e]
        today_ct = sum(1 for r in mine if r["date"] == today and r["status"] == "Delivered")
        month = sum(1 for r in mine if in_same_month(r, today) and r["status"] == "Delivered")
        inflight = sum(1 for r in mine if r["status"] == "in-flight")
        seven_day = 0
        for i in range(7):
            d = today - timedelta(days=i)
            seven_day += sum(1 for r in mine if r["date"] == d and r["status"] == "Delivered")
        avg_7d = round(seven_day / 7, 1)
        result.append({
            "editor": e, "today": today_ct, "month": month,
            "inflight": inflight, "avg_7d": avg_7d, "status": "on-track",
        })
    # Team-average based status
    if result:
        team_avg = sum(e["inflight"] for e in result) / len(result)
        for e in result:
            if team_avg > 0 and e["inflight"] >= team_avg * 1.75:
                e["status"] = "backlog"
            elif team_avg > 0 and e["inflight"] >= team_avg * 1.3:
                e["status"] = "watching"
    return result


def compute_language_production(rows, today):
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    day_of_month = today.day
    result = []
    for lang in LANGUAGES:
        mine = [r for r in rows if r["language"] == lang]
        today_ct = sum(1 for r in mine if r["date"] == today and r["status"] == "Delivered")
        month = sum(1 for r in mine if in_same_month(r, today) and r["status"] == "Delivered")
        target = TARGETS["by_language"].get(lang, 0)
        pace_expected = round(target * day_of_month / days_in_month) if target else 0
        pace_gap = month - pace_expected
        seven_day = 0
        for i in range(7):
            d = today - timedelta(days=i)
            seven_day += sum(1 for r in mine if r["date"] == d and r["status"] == "Delivered")
        avg_7d = round(seven_day / 7, 1)
        severity = "ok"
        if target > 0 and pace_expected > 0:
            pct = month / pace_expected
            if pct < 0.4: severity = "urgent"
            elif pct < 0.7: severity = "warning"
            elif pct < 0.85: severity = "attention"
        result.append({
            "language": lang, "today": today_ct, "month": month,
            "target": target, "pace_expected": pace_expected,
            "pace_gap": pace_gap, "avg_7d": avg_7d, "severity": severity,
        })
    return result


def compute_stuck(rows, today):
    inflight = [r for r in rows if r["status"] == "in-flight"]
    stuck = []
    for r in inflight:
        aged = days_between(today, r["date"])
        if aged <= 2:
            continue
        stuck.append({
            "script": r["script"],
            "type": r["type"] or "(no type)",
            "language": r["language"] or "(no language)",
            "editor": r["editor"] or "—",
            "days_aged": aged,
            "severity": "urgent" if aged > 4 else "warning",
        })
    stuck.sort(key=lambda s: -s["days_aged"])
    return stuck


def compute_recent_activity(rows, today, n_days=7):
    result = []
    for i in range(n_days):
        d = today - timedelta(days=i)
        delivered = [r for r in rows if r["date"] == d and r["status"] == "Delivered"]

        by_lang = Counter(r["language"] for r in delivered)
        top_lang = by_lang.most_common(1)
        top_lang_str = f"{top_lang[0][0]} ({top_lang[0][1]})" if top_lang else "—"

        by_editor = Counter(r["editor"] for r in delivered if r["editor"])
        top_ed = by_editor.most_common(1)
        top_ed_str = f"{top_ed[0][0]} ({top_ed[0][1]})" if top_ed else "—"

        if d == today:
            label = f"Today · {d.strftime('%d %b')}"
        elif d == today - timedelta(days=1):
            label = f"Yesterday · {d.strftime('%d %b')}"
        else:
            label = d.strftime("%A · %d %b")

        result.append({
            "date": label, "delivered": len(delivered),
            "top_language": top_lang_str, "top_editor": top_ed_str,
        })
    return result


def compute_priorities(rows, today, languages, editors, stuck):
    """
    Ranking priority (per user):
    1. Language target gaps
    2. Editor backlog concentration
    3. Aged in-flight
    4. Type pacing
    """
    items = []

    def sev_rank(s):
        return {"urgent": 0, "warning": 1, "attention": 2}.get(s, 3)

    # 1. Language target gaps
    for l in languages:
        if l["severity"] == "ok" or l["target"] == 0:
            continue
        items.append({
            "severity": l["severity"],
            "title": f"{l['language']} behind pace by {abs(l['pace_gap'])}",
            "detail": f"{l['month']} of {l['target']} delivered · expected {l['pace_expected']} by now · avg {l['avg_7d']}/day",
            "rank": 1000 + sev_rank(l["severity"]) * 100 + (100 - min(99, abs(l["pace_gap"]))),
        })

    # 2. Editor backlog concentration
    for e in editors:
        if e["status"] == "backlog":
            items.append({
                "severity": "warning",
                "title": f"{e['editor']} has a big backlog",
                "detail": f"{e['inflight']} in-flight — nearly 2× the team average.",
                "rank": 2000 + (100 - min(99, e["inflight"])),
            })
        elif e["status"] == "watching":
            items.append({
                "severity": "attention",
                "title": f"{e['editor']}'s in-flight is climbing",
                "detail": f"{e['inflight']} in-flight vs team average.",
                "rank": 2100 + (100 - min(99, e["inflight"])),
            })

    # 3. Aged in-flight
    urgent_stuck = sum(1 for s in stuck if s["severity"] == "urgent")
    warning_stuck = sum(1 for s in stuck if s["severity"] == "warning")
    if urgent_stuck > 0:
        items.append({
            "severity": "urgent",
            "title": f"{urgent_stuck} video{'s' if urgent_stuck != 1 else ''} in-flight for 4+ days",
            "detail": "See Needs Attention below for the exact list.",
            "rank": 3000,
        })
    elif warning_stuck >= 5:
        items.append({
            "severity": "warning",
            "title": f"{warning_stuck} videos in-flight for 3+ days",
            "detail": "See Needs Attention below for the exact list.",
            "rank": 3100,
        })

    # 4. Type pacing
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    day_of_month = today.day
    for tname, target in TARGETS["by_type"].items():
        if target == 0:
            continue
        delivered = sum(
            1 for r in rows
            if r["type"] == tname and r["status"] == "Delivered" and in_same_month(r, today)
        )
        expected = round(target * day_of_month / days_in_month)
        if expected == 0:
            continue
        pct = delivered / expected
        if pct < 0.7:
            sev = "warning" if pct < 0.5 else "attention"
            remaining = max(0, target - delivered)
            days_rem = max(1, days_in_month - day_of_month)
            per_day = -(-remaining // days_rem)  # ceil
            items.append({
                "severity": sev,
                "title": f"{tname} type behind pace",
                "detail": f"{delivered} of {target} target · needs ~{per_day}/day.",
                "rank": 4000 + sev_rank(sev) * 100 + (100 - min(99, round((1 - pct) * 100))),
            })

    items.sort(key=lambda x: x["rank"])
    return items[:5]


def compute_insight(today_counts, languages, editors):
    parts = []
    if today_counts["avg_7d"] > 0:
        pct = round((today_counts["delivered_today"] - today_counts["avg_7d"])
                    / today_counts["avg_7d"] * 100)
        if pct >= 10:
            parts.append(f"Today's pace is {pct}% above the 7-day average of {today_counts['avg_7d']}")
        elif pct <= -10:
            parts.append(f"Today's pace is {abs(pct)}% below the 7-day average of {today_counts['avg_7d']}")
        else:
            parts.append(f"Today's pace is on par with the 7-day average of {today_counts['avg_7d']}")

    behind = sorted(
        [l for l in languages if l["severity"] in ("urgent", "warning")],
        key=lambda l: l["pace_gap"],
    )[:2]
    if behind:
        names = " and ".join(l["language"] for l in behind)
        verb = "are" if len(behind) > 1 else "is"
        parts.append(f"{names} {verb} pulling the month behind plan")

    top_editor = max(editors, key=lambda e: e["month"]) if editors else None
    if top_editor and top_editor["month"] > 0:
        parts.append(f"{top_editor['editor']} leads the month at {top_editor['month']}")

    return ". ".join(parts) + "." if parts else "Not enough data yet to summarize the day."


# ============================================================================
# UI HELPERS
# ============================================================================

SEV_EMOJI = {"urgent": "🔴", "warning": "🟠", "attention": "🟡", "ok": "🟢",
             "backlog": "🔴", "watching": "🟠", "on-track": "🟢"}


def render_priorities(items):
    st.subheader("Today's priorities")
    if not items:
        st.info("Nothing above the priority threshold. The month is on pace and no unusual backlogs detected.")
        return
    for p in items:
        with st.container(border=True):
            st.markdown(f"**{SEV_EMOJI[p['severity']]} {p['title']}**")
            st.caption(p["detail"])


def render_editor_table(editors):
    st.subheader("Editor workload")
    if not editors:
        st.caption("No editor-tagged rows found in the sheet yet this month.")
        return
    df = pd.DataFrame([
        {
            "Editor": e["editor"],
            "Today": e["today"],
            "This month": e["month"],
            "In-flight": e["inflight"],
            "7d avg": e["avg_7d"],
            "Status": f"{SEV_EMOJI[e['status']]} {e['status'].replace('-', ' ')}",
        }
        for e in editors
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_language_table(languages):
    st.subheader("Language production vs target")
    df = pd.DataFrame([
        {
            "Language": l["language"],
            "Today": l["today"],
            "This month": l["month"],
            "Target": l["target"],
            "Pace gap": f"+{l['pace_gap']}" if l["pace_gap"] >= 0 else f"−{abs(l['pace_gap'])}",
            "7d avg": l["avg_7d"],
            "Status": SEV_EMOJI[l["severity"]],
        }
        for l in languages
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_stuck_table(stuck):
    st.subheader(f"Needs attention · in-flight >2 days ({len(stuck)} total)")
    if not stuck:
        st.info("Nothing stuck. Every in-flight video was added in the last 2 days.")
        return
    df = pd.DataFrame([
        {
            "Script": s["script"],
            "Type · Language": f"{s['type']} · {s['language']}",
            "Editor": s["editor"],
            "Days": f"{SEV_EMOJI[s['severity']]} {s['days_aged']}",
        }
        for s in stuck[:15]
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
    if len(stuck) > 15:
        st.caption(f"Showing 15 of {len(stuck)}. Older items are further down the list.")


def render_activity_table(activity):
    st.subheader("Recent activity · last 7 days")
    df = pd.DataFrame([
        {
            "Date": d["date"],
            "Delivered": d["delivered"],
            "Top language": d["top_language"],
            "Top editor": d["top_editor"],
        }
        for d in activity
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================================
# MAIN
# ============================================================================

def main():
    if not check_auth():
        return

    # Load data
    try:
        raw_rows, tab_title = load_sheet_rows()
    except Exception as e:
        st.error(f"Couldn't load the sheet: {e}")
        st.info(
            "Check that GOOGLE_CREDENTIALS_JSON, SHEET_ID, and SHEET_TAB are all set "
            "correctly in secrets, and that the sheet is shared with the service account email."
        )
        return

    rows, skipped = normalize_rows(raw_rows)
    today = date.today()

    # Header row
    hcol1, hcol2 = st.columns([4, 1])
    with hcol1:
        st.title("Connecto command center")
        st.caption(
            f"{today.strftime('%A, %d %B %Y')} · reading '{tab_title}' · "
            f"{len(rows)} rows{f' · {skipped} skipped' if skipped else ''}"
        )
    with hcol2:
        st.write("")
        if st.button("🔄 Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Compute all metrics
    today_counts = compute_today_counts(rows, today)
    editors = compute_editor_workload(rows, today)
    languages = compute_language_production(rows, today)
    stuck = compute_stuck(rows, today)
    activity = compute_recent_activity(rows, today, n_days=7)
    priorities = compute_priorities(rows, today, languages, editors, stuck)
    insight = compute_insight(today_counts, languages, editors)

    # Top metric row
    st.markdown("&nbsp;")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Added today", today_counts["added_today"],
                  delta=f"7d avg {today_counts['avg_7d']}", delta_color="off")
    with c2:
        diff = today_counts["delivered_today"] - today_counts["delivered_yday"]
        st.metric("Delivered today", today_counts["delivered_today"],
                  delta=f"{'+' if diff >= 0 else ''}{diff} vs yday")
    with c3:
        st.metric("In-flight", today_counts["inflight_total"],
                  delta=f"{today_counts['inflight_urgent']} aged >4d",
                  delta_color="inverse" if today_counts["inflight_urgent"] else "off")
    with c4:
        st.metric("This month", today_counts["month_delivered"],
                  delta=f"of {today_counts['month_target']} target", delta_color="off")
    with c5:
        st.metric("Days left", today_counts["days_left"],
                  delta=f"{today_counts['daily_required']}/day needed",
                  delta_color="inverse" if today_counts["daily_required"] > today_counts["avg_7d"] * 1.2 else "off")

    # Insight line
    st.info(insight, icon="💡")

    # Data notes warning if the Static target mismatch is present
    corrected = TARGETS.get("month_total_corrected")
    as_shown = TARGETS.get("month_total_as_shown")
    if corrected and corrected != as_shown:
        with st.expander("📋 Data notes"):
            st.warning(
                f"Monthly target as printed on the sheet is **{as_shown}**, but "
                f"per-cell sum is **{corrected}** — the Static row appears mis-summed. "
                "Fix the sheet or update targets in `app.py`."
            )

    # Two-column body
    st.markdown("&nbsp;")
    left, right = st.columns([1, 1])
    with left:
        render_priorities(priorities)
        render_editor_table(editors)
    with right:
        render_language_table(languages)
        render_stuck_table(stuck)

    # Full-width bottom
    render_activity_table(activity)

    # Footer
    st.caption(
        f"Cache TTL 5 min · press Refresh for the latest · "
        f"last synced {datetime.now().strftime('%H:%M')}"
    )


main()
