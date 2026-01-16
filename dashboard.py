import datetime as dt
import os
from typing import Any, Dict, List, Tuple

import httpx
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def supabase_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }


def fetch_logs(params: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    url = f"{SUPABASE_URL}/rest/v1/event_logs"
    with httpx.Client(timeout=10) as client:
        response = client.get(url, params=params, headers=supabase_headers())
        response.raise_for_status()
        return response.json()


st.set_page_config(page_title="Bridge Dashboard", layout="wide")
st.title("Chatwoot <> LinkedIn Bridge")

st.subheader("Env status")
col1, col2, col3 = st.columns(3)
col1.metric("SUPABASE_URL", "set" if SUPABASE_URL else "missing")
col2.metric("SUPABASE_SERVICE_ROLE_KEY", "set" if SUPABASE_KEY else "missing")
col3.metric("Logs", "ready" if SUPABASE_URL and SUPABASE_KEY else "disabled")

st.divider()

st.subheader("Filters")
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
chat_id = filter_col1.text_input("chat_id")
decision = filter_col2.selectbox(
    "decision",
    [
        "all",
        "sent_to_unipile",
        "blocked_echo",
        "created_incoming",
        "created_outgoing",
        "ignored_event",
        "ignored_marker",
        "error",
    ],
)
start_date = filter_col3.date_input("start_date", value=dt.date.today() - dt.timedelta(days=7))
end_date = filter_col4.date_input("end_date", value=dt.date.today())

limit = st.slider("limit", min_value=50, max_value=1000, value=200, step=50)

params: List[Tuple[str, str]] = [
    ("select", "*"),
    ("order", "created_at.desc"),
    ("limit", str(limit)),
]

if chat_id:
    params.append(("chat_id", f"eq.{chat_id}"))
if decision != "all":
    params.append(("decision", f"eq.{decision}"))
if start_date:
    start_iso = dt.datetime.combine(start_date, dt.time.min).isoformat() + "Z"
    params.append(("created_at", f"gte.{start_iso}"))
if end_date:
    end_iso = dt.datetime.combine(end_date, dt.time.max).isoformat() + "Z"
    params.append(("created_at", f"lte.{end_iso}"))

logs = fetch_logs(params)

st.subheader("Counters")
count_col1, count_col2, count_col3, count_col4 = st.columns(4)
count_col1.metric("total", str(len(logs)))
count_col2.metric(
    "sent_to_unipile",
    str(sum(1 for item in logs if item.get("decision") == "sent_to_unipile")),
)
count_col3.metric(
    "blocked_echo",
    str(sum(1 for item in logs if item.get("decision") == "blocked_echo")),
)
count_col4.metric(
    "errors",
    str(sum(1 for item in logs if item.get("decision") == "error")),
)

st.subheader("event_logs")
st.dataframe(logs, use_container_width=True)
