import streamlit as st
from test1 import ask_question

# عنوان الصفحة
st.set_page_config(page_title="Medical Chatbot")
st.title(" Drug dose Chatbot")

st.write("please enter your drug name below")

# Input box
drug_name = st.text_input("Enter drug name:")

# Button
if st.button("Ask"):
    if drug_name.strip() == "":
        st.warning("Please enter a drug name.")
    else:
        with st.spinner("Searching documents and generating answer..."):
            answer = ask_question(drug_name)
            st.success("Answer:")
            st.write(answer)
