import streamlit as st

st.title("💬 Chat")
st.write("Ask your assistant anything about the connected systems.")
prompt = st.text_input("Enter your prompt:")
if st.button("Submit"):
    st.write("🔍 Processing your query...")
    # Add RAG logic here
