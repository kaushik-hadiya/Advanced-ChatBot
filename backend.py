from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_core.tools import tool
from dotenv import load_dotenv
import sqlite3
import requests
import os
import groq
load_dotenv()


ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")


#-----------------LLM--------------------
llm = ChatGroq(model="openai/gpt-oss-120b")

#---------------------Tools--------------------
search_wrapper = DuckDuckGoSearchAPIWrapper(region='in-en',max_results=5)
search_tool = DuckDuckGoSearchRun(name="web_search", api_wrapper=search_wrapper)

@tool
def calculator(first_num:float, second_num:float, operation:str)->dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed."}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation: {operation}"}
        
        return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}

@tool
def get_stock_price(symbol: str) -> dict:
    """
    Get the latest real-time stock price for a ticker symbol.
    Always use this tool (not web search) when the user asks for a stock price.
    Examples: 'AAPL', 'GOOGL', 'MSFT'. For Indian stocks use 'RELIANCE.BSE', 'TCS.BSE'.
    """
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


tools = [search_tool, calculator, get_stock_price]
llm_with_tools = llm.bind_tools(tools)


#----------------State--------------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


#----------------chat node------------------

SYSTEM_PROMPT = SystemMessage(content=(
    "You are a helpful assistant. "
    "For stock prices, use the get_stock_price tool. "
    "If a tool returns an error, do not retry it more than once; "
    "explain the problem to the user instead."
))

def chat_node(state: ChatState):
    messages = [SYSTEM_PROMPT] + state["messages"]
    for attempt in range(2):
        try:
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}
        except groq.APIError as e:
            if attempt == 1:
                return {"messages": [AIMessage(
                    content="Sorry, I ran into a problem while using my tools. Please try again."
                )]}

#-----------------tool node------------------
tool_node = ToolNode(tools, handle_tool_errors=True)


#------------------Checkpointer-----------------
connection = sqlite3.connect(database="chatbot.db",check_same_thread=False)
checkpointer = SqliteSaver(conn=connection)


#-----------------State Graph-----------------
graph = StateGraph(ChatState)
graph.add_node('chat_node', chat_node)
graph.add_node('tools',tool_node)


graph.add_edge(START, 'chat_node')
graph.add_conditional_edges('chat_node', tools_condition)
graph.add_edge('tools','chat_node')

chatbot = graph.compile(checkpointer=checkpointer)

"""checkpointer.list(None) -> gives the generator object of all the checkpoints in the database of all threads 
or can give us all the checkpoints of a specific thread by passing the thread_id as an argument to the list() method."""


#--------------------helper function to retrieve all threads--------------------
def retrieve_all_threads():
    all_threads = []
    for checkpoint in checkpointer.list(None):
        thread_id = checkpoint.config['configurable']['thread_id']
        if thread_id not in all_threads:
            all_threads.append(thread_id)
    return all_threads