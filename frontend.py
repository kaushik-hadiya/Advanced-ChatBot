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

    
    
    
    # we will get the response from the chatbot but we will stream the response in chunks and display it in the chat message
    with st.chat_message("assistant"):
        ai_message = st.write_stream(message_chunk.content for message_chunk,metadata in chatbot.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config=CONFIG,
            stream_mode='messages'
        ))

    # adding the AI message to the session state message history
    st.session_state.message_history.append({"role": "assistant", "content": ai_message})


 