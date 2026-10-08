from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import sqlite3


load_dotenv()

llm = ChatGroq(model="openai/gpt-oss-120b")

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# chat node
def chat_node(state: ChatState):
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

connection = sqlite3.connect(database="chatbot.db",check_same_thread=False)
# Checkpointer
checkpointer = SqliteSaver(conn=connection)

graph = StateGraph(ChatState)
graph.add_node('chat_node', chat_node)
graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)

chatbot = graph.compile(checkpointer=checkpointer)

"""checkpointer.list(None) -> gives the generator object of all the checkpoints in the database of all threads 
or can give us all the checkpoints of a specific thread by passing the thread_id as an argument to the list() method."""

def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint['configurable']['thread_id'])
    return list(all_threads)