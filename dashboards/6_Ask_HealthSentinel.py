"""Report-grounded local question answering page."""

import streamlit as st

from src.report_store import answer_from_reports, save_feedback
from src.styling import inject_css, page_header

inject_css()

st.markdown(
    """
    <style>
    .ask-header {
        background: linear-gradient(135deg, #17324D 0%, #0F6B78 50%, #16855B 100%);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 28px;
        box-shadow: 0 8px 24px rgba(23,50,77,0.15);
        position: relative;
        overflow: hidden;
    }
    .ask-header::before {
        content: "";
        position: absolute;
        top: -50%;
        right: -20%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 70%);
        border-radius: 50%;
    }
    .ask-header-content {
        position: relative;
        z-index: 1;
    }
    .ask-header-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: white;
        margin: 0 0 6px 0;
        letter-spacing: -0.02em;
        line-height: 1.15;
    }
    .ask-header-sub {
        font-size: 0.9rem;
        color: rgba(255,255,255,0.80);
        margin: 0;
        line-height: 1.45;
    }
    .ask-header-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        margin-top: 12px;
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(4px);
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 0.68rem;
        font-weight: 700;
        color: white;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        border: 1px solid rgba(255,255,255,0.20);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="ask-header">
        <div class="ask-header-content">
            <h1 class="ask-header-title">Ask HealthSentinel</h1>
            <p class="ask-header-sub">Ask questions grounded only in generated report excerpts</p>
            <div class="ask-header-badge">🩺 RAG · Report Q&A</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

question = st.text_area("Question", placeholder="What did the generated reports say about case counts?")
top_k = st.slider("Report excerpts", min_value=1, max_value=10, value=5)

if st.button("Ask", type="primary", disabled=not question.strip()):
    with st.spinner("Searching generated reports..."):
        st.session_state["report_rag_result"] = answer_from_reports(question.strip(), top_k)
        st.session_state["report_rag_question"] = question.strip()

result = st.session_state.get("report_rag_result")
if result:
    st.markdown(result["answer"])
    if result["sources"]:
        with st.expander("Reports used", expanded=True):
            for source in result["sources"]:
                st.markdown(f"**{source.get('report_title', 'Generated report')}** · `{source['report_id']}`")
                st.caption(source["chunk_text"])
                st.caption(f"Similarity: {source.get('score', 0):.3f}")
    st.divider()
    rating = st.feedback("thumbs", key="report_rag_rating")
    comment = st.text_input("Optional comment", key="report_rag_comment")
    if rating is not None and st.button("Submit feedback", key="report_rag_submit"):
        save_feedback(
            st.session_state["report_rag_question"], result["answer"], result["sources"],
            "positive" if rating == 1 else "negative", comment,
        )
        st.success("Feedback recorded.")