import os
import streamlit as st
import mysql.connector
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import ChatMessage
from langchain_openai import ChatOpenAI

# 1. Database Setup (Using the DB Wasmer made for you)
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

# Create table if it doesn't exist
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS chat_history (id INT AUTO_INCREMENT PRIMARY KEY, role VARCHAR(20), content TEXT)")
    conn.commit()
    cursor.close()
    conn.close()
except Exception as e:
    st.error(f"DB Connection failed: {e}")

# 2. Streaming UI Handler
class StreamHandler(BaseCallbackHandler):
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        self.container.markdown(self.text)

# 3. App UI
st.title("🚀 Wasmer AI: GPT-5 Mini")

# Get API Key from Wasmer Secrets (best for iPad) or Sidebar
api_key = os.getenv("OPENROUTER_API_KEY") or st.sidebar.text_input("OpenRouter API Key", type="password")

if "messages" not in st.session_state:
    st.session_state["messages"] = [ChatMessage(role="assistant", content="Database connected. How can I help?")]

for msg in st.session_state.messages:
    st.chat_message(msg.role).write(msg.content)

if prompt := st.chat_input():
    st.session_state.messages.append(ChatMessage(role="user", content=prompt))
    st.chat_message("user").write(prompt)

    if not api_key:
        st.info("Please add your OpenRouter API key in Wasmer Secrets or the sidebar.")
        st.stop()

    with st.chat_message("assistant"):
        stream_handler = StreamHandler(st.empty())
        
        # Configure for OpenRouter + GPT-5 Mini
        llm = ChatOpenAI(
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai",
            model_name="openai/gpt-5-mini",
            streaming=True,
            callbacks=[stream_handler]
        )
        
        response = llm.invoke(st.session_state.messages)
        st.session_state.messages.append(ChatMessage(role="assistant", content=response.content))
        
        # 4. Save to Database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chat_history (role, content) VALUES (%s, %s)", ("user", prompt))
            cursor.execute("INSERT INTO chat_history (role, content) VALUES (%s, %s)", ("assistant", response.content))
            conn.commit()
            cursor.close()
            conn.close()
        except:
            pass # Silent fail if DB isn't ready
