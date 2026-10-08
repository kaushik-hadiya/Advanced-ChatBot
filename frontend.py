import streamlit as st
from backend import chatbot
from langchain_core.messages import HumanMessage
import uuid

#----------------------------utility functions -------------------

def generate_thread_id():
    thread_id = str(uuid.uuid4())
    return thread_id

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state.thread_id = thread_id
    #add_thread(st.session_state.thread_id)
    st.session_state.message_history = []

def add_thread(thread_id):
    if thread_id not in st.session_state.chat_threads:
        st.session_state.chat_threads.append(thread_id)

def load_conversation(thread_id):
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
    return state.values.get("messages", [])

#------------------------- session setup -------------------------
# st.session_state -- to store the conversation history
if "message_history" not in st.session_state:
    st.session_state.message_history = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = []

#add_thread(st.session_state.thread_id)

#---------------------------sidebar ui ---------------------------

st.sidebar.title("LangGraph Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("Past Conversations")

for thread_id in st.session_state.chat_threads[::-1]:  # Display threads in reverse order (most recent first)
    if st.sidebar.button(thread_id):
        st.session_state.thread_id = thread_id
        messages = load_conversation(thread_id)

        temp_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            else:
                role = "assistant"
            temp_messages.append({"role": role, "content": msg.content})
        st.session_state.message_history = temp_messages



# loading the conversation history 
for message in st.session_state.message_history:
    with st.chat_message(message["role"]):
        st.text(message["content"])

# {'role': 'user', 'content': 'Hello!'}
# {'role': 'assistant', 'content': 'Hello! How can I assist you today}


user_input = st.chat_input("Type your message here...")


if user_input:
    add_thread(st.session_state.thread_id)  # Ensure the current thread is added to the list of threads
    # first add the message to the session state message history
    st.session_state.message_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.text(user_input)

    
    CONFIG = {'configurable':{'thread_id': st.session_state.thread_id}}
    
    # we will get the response from the chatbot but we will stream the response in chunks and display it in the chat message
    with st.chat_message("assistant"):
        ai_message = st.write_stream(message_chunk.content for message_chunk,metadata in chatbot.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config=CONFIG,
            stream_mode='messages'
        ))

    # adding the AI message to the session state message history
    st.session_state.message_history.append({"role": "assistant", "content": ai_message})


 