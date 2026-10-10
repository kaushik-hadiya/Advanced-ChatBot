import streamlit as st
from backend import chatbot, retrieve_all_threads
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.errors import GraphRecursionError
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
    if thread_id in st.session_state.chat_threads:
        st.session_state.chat_threads.remove(thread_id)
    st.session_state.chat_threads.insert(0,thread_id)  # newest at top

def load_conversation(thread_id):
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
    return state.values.get("messages", [])

def show_tools_box(tools):
    """Draw a collapsed status box listing the tools used for one answer."""
    unique_tools = ", ".join(dict.fromkeys(tools))
    with st.status(
        f"✅ Used {len(tools)} tool call(s): {unique_tools}",
        state="complete",
        expanded=False,
    ):
        for t in tools:
            st.write(f"🔧 `{t}`")

#------------------------- session setup -------------------------
# st.session_state -- to store the conversation history
if "message_history" not in st.session_state:
    st.session_state.message_history = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = retrieve_all_threads()

#add_thread(st.session_state.thread_id)

#---------------------------sidebar ui ---------------------------

st.sidebar.title("LangGraph Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("Past Conversations")

for thread_id in st.session_state.chat_threads:
    if st.sidebar.button(thread_id):
        st.session_state.thread_id = thread_id
        messages = load_conversation(thread_id)
 
        # rebuild the chat, including which tools were used for each answer
        temp_messages = []
        pending_tools = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                temp_messages.append({"role": "user", "content": msg.content})
                pending_tools = []
            elif isinstance(msg, AIMessage):
                if msg.tool_calls:
                    pending_tools.extend(tc["name"] for tc in msg.tool_calls)
                if msg.content:
                    temp_messages.append(
                        {"role": "assistant", "content": msg.content, "tools": pending_tools}
                    )
                    pending_tools = []
        st.session_state.message_history = temp_messages



#----------------loading the conversation history-----------
for message in st.session_state.message_history:
    with st.chat_message(message["role"]):
        tools = message.get("tools")
        if tools:
            show_tools_box(tools)
        st.text(message["content"])

# {'role': 'user', 'content': 'Hello!'}
# {'role': 'assistant', 'content': 'Hello! How can I assist you today}


#------------new message input and response generation----------------

user_input = st.chat_input("Type your message here...")


if user_input:
    add_thread(st.session_state.thread_id)
 
    st.session_state.message_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.text(user_input)
 
    CONFIG = {
        "configurable": {"thread_id": st.session_state.thread_id},
        "run_name": "chat_turn",
    }
 
    with st.chat_message("assistant"):
        status_holder = {"box": None}
        tools_used = []
 
        def ai_only_stream():
            try:
                for message_chunk, metadata in chatbot.stream(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=CONFIG,
                    stream_mode="messages",
                ):
                    # show which tool is being called, before it runs
                    if isinstance(message_chunk, AIMessage) and getattr(message_chunk, "tool_call_chunks", None):
                        for tc in message_chunk.tool_call_chunks:
                            tool_name = tc.get("name")
                            if tool_name:  # only the first chunk of each call has the name
                                tools_used.append(tool_name)
                                if status_holder["box"] is None:
                                    status_holder["box"] = st.status(
                                        f"🔧 Using `{tool_name}` …", expanded=True
                                    )
                                else:
                                    status_holder["box"].update(
                                        label=f"🔧 Using `{tool_name}` …",
                                        state="running",
                                        expanded=True,
                                    )
                                # write the tool inside the dropdown so it stays listed
                                status_holder["box"].write(f"🔧 `{tool_name}`")
 
                    # stream only the assistant's text
                    if isinstance(message_chunk, AIMessage):
                        yield message_chunk.content
 
            except GraphRecursionError:
                yield "Sorry, I tried several times but couldn't complete this request. Please try rephrasing it."
 
        ai_message = st.write_stream(ai_only_stream())
 
        # final label lists the tools, visible even when collapsed
        if status_holder["box"] is not None:
            unique_tools = ", ".join(dict.fromkeys(tools_used))
            status_holder["box"].update(
                label=f"✅ Used {len(tools_used)} tool call(s): {unique_tools}",
                state="complete",
                expanded=False,
            )
 
    # save the tools with the message so they survive reruns
    st.session_state.message_history.append(
        {"role": "assistant", "content": ai_message, "tools": tools_used}
    )
 
    # redraw so the new chat appears in the sidebar right away
    st.rerun()