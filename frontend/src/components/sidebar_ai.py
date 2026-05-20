"""AI analysis sidebar (FR-003, FR-012)."""

from __future__ import annotations

import streamlit as st

from api_client import AnalysisAPIError, post_analysis


ANALYSIS_TYPE_LABELS = {
    "question": "Question",
    "prediction": "Prediction",
    "summary": "Summary",
}


def render_sidebar(context_payload: dict) -> None:
    collapsed = st.session_state.get("sidebar_collapsed", False)
    if st.sidebar.button("Toggle AI panel"):
        st.session_state["sidebar_collapsed"] = not collapsed
        st.rerun()

    if st.session_state.get("sidebar_collapsed"):
        return

    st.sidebar.header("AI Analysis")
    prompt = st.sidebar.text_area("Ask about customer health and risk", height=120)
    analysis_type = st.sidebar.selectbox("Type", list(ANALYSIS_TYPE_LABELS.keys()), format_func=lambda k: ANALYSIS_TYPE_LABELS[k])
    retry_key = st.session_state.get("ai_retry_prompt")

    col1, col2 = st.sidebar.columns(2)
    analyze = col1.button("Analyze", type="primary")
    retry = col2.button("Retry")

    if retry and retry_key:
        prompt = retry_key
        analyze = True

    if not analyze or not prompt.strip():
        return

    has_selection = bool(
        context_payload.get("selected_customer") or context_payload.get("selected_customer_id")
    )
    body = {
        "prompt": prompt.strip(),
        "analysis_type": analysis_type,
        "context_scope": "table_selection" if has_selection else "dashboard",
        "context_payload": context_payload,
    }

    with st.sidebar.spinner("Analyzing..."):
        try:
            result = post_analysis(body)
        except AnalysisAPIError as exc:
            st.sidebar.error(str(exc))
            if exc.error_code == "gemini_quota":
                st.sidebar.info("Quota limits are per API key. Wait, upgrade billing, or use a new key in `.env`.")
            elif exc.error_code == "gemini_auth":
                st.sidebar.info("Update `GEMINI_API_KEY` in the project root `.env` and restart the API server.")
            st.session_state["ai_retry_prompt"] = prompt.strip()
            return
        except Exception as exc:  # noqa: BLE001
            st.sidebar.error(f"Request failed: {exc}")
            st.session_state["ai_retry_prompt"] = prompt.strip()
            return

    if result.get("status") == "timeout" or isinstance(result.get("detail"), dict) and result["detail"].get("error") == "analysis_timeout":
        st.sidebar.error("AI analysis exceeded the 10 second limit. Please retry.")
        st.session_state["ai_retry_prompt"] = prompt.strip()
        return

    st.session_state.pop("ai_retry_prompt", None)
    res = result.get("result") or {}
    content = res.get("content", "")
    st.sidebar.markdown(content)
    history = st.session_state.get("analysis_history", [])
    history.insert(0, {"prompt": prompt[:80], "status": result.get("status")})
    st.session_state["analysis_history"] = history[:5]
