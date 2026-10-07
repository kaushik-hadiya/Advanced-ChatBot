import streamlit as st
from backend import chatbot
from langchain_core.messages import HumanMessage

CONFIG = {'configurable':{'thread_id':'thread_1'}}

# st.session_state -- to store the conversation history
if "message_history" not in st.session_state:
    st.session_state.message_history = []

# loading the conversation history 
for message in st.session_state.message_history:
    with st.chat_message(message["role"]):
        st.text(message["content"])

# {'role': 'user', 'content': 'Hello!'}
# {'role': 'assistant', 'content': 'Hello! How can I assist you today}


user_input = st.chat_input("Type your message here...")


if user_input:
    # first add the message to the session state message history
    st.session_state.message_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.text(user_input)

    # we will get the response from the chatbot
    response = chatbot.invoke({"messages": [HumanMessage(content=user_input)]},config=CONFIG)
    ai_message = response["messages"][-1].content  # get the last message from the response

    # adding the AI message to the session state message history
    st.session_state.message_history.append({"role": "assistant", "content": ai_message})
    with st.chat_message("assistant"):
        st.text(ai_message)


 