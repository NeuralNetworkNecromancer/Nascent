"""Placeholder Chat interface page."""

import streamlit as st

st.title("💬 Data-Assistant Chat (Coming Soon)")

user_input = st.chat_input("Ask about data quality… (demo placeholder)")
if user_input:
    st.write("Assistant: This feature will integrate an LLM to answer your data questions.") 