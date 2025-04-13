# streamlit_app.py
import streamlit as st
import os

import os
import sys

# Add the 'src' folder to the system path so that modules under src can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from website_automation import main as crew_main

st.title("📄🤖 Automated Dev Team - Demo")
st.write("Upload requirement documents and describe the website you'd like to build:")

# File uploader for requirements (multiple files allowed)
uploaded_files = st.file_uploader("Upload requirements (PDF/DOC):", type=['pdf', 'doc', 'docx'], accept_multiple_files=True)

# Text input for high-level prompt
user_prompt = st.text_area("Website Description / High-Level Requirements:")

if st.button("Run Automation"):
    if not user_prompt:
        st.warning("Please enter a prompt describing the desired website.")
        st.stop()
    # Save uploaded files to knowledge folder
    docs_path = "src/website_automation/knowledge"
    os.makedirs(docs_path, exist_ok=True)
    if uploaded_files:
        for file in uploaded_files:
            file_path = os.path.join(docs_path, file.name)
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
        st.write(f"Saved {len(uploaded_files)} files to knowledge base.")
    # Run the crew with the provided prompt
    with st.spinner("Running AI agents... This may take a while."):
        result = crew_main.run(user_prompt, docs_folder=docs_path)
    st.success("Crew finished execution.")
    # Display key outputs:
    # 1. Display user stories JSON (if available)
    try:
        with open(os.path.join(docs_path, "user_stories.json"), "r") as uf:
            stories_json = uf.read()
        st.subheader("Generated User Stories")
        st.code(stories_json, language="json")
    except FileNotFoundError:
        st.write("User stories JSON not found (it might be in the agent output above).")
    # 2. Display test results from final output
    if result:
        st.subheader("Test Results")
        st.write(result.raw if hasattr(result, 'raw') else str(result))
    st.info("Check the 'design' and 'output' folders for design document and code files.")
