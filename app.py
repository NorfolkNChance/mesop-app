import os
import json
import ollama
import mesop as me
import mesop.labs as mel
from datetime import datetime
from dataclasses import field

# Define a new directory for storing chat history
CHAT_DIR = "chats"
if not os.path.exists(CHAT_DIR):
    os.makedirs(CHAT_DIR)

@me.stateclass
class State:
    chat_id: str | None = None
    chats: list[str] = field(default_factory=list)

def load_chats() -> list[str]:
    """Loads the list of chats from the filesystem."""
    if not os.path.exists(CHAT_DIR):
        os.makedirs(CHAT_DIR)
    return sorted(
        [
            f.replace(".json", "")
            for f in os.listdir(CHAT_DIR)
            if f.endswith(".json")
        ],
        reverse=True,
    )

def on_load(e: me.LoadEvent):
    """Initializes the application state on load."""
    me.set_theme_mode("dark")
    state = me.state(State)
    state.chats = load_chats()
    if state.chats:
        if not state.chat_id or state.chat_id not in state.chats:
            state.chat_id = state.chats[0]
    else:
        # Create a new chat if none exist
        new_chat_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        state.chats.insert(0, new_chat_id)
        state.chat_id = new_chat_id

@me.page(
    on_load=on_load,
    path="/",
    title="J.A.R.V.I.S.",
    security_policy=me.SecurityPolicy(
        allowed_script_srcs=[
            "self", "unsafe-inline", "unsafe-eval",
            "blob:", "https:", "http:", "chrome-extension:",
        ]
    ),
)
def page():
    state = me.state(State)
    with me.box(style=me.Style(display="flex", height="100vh")):
        # Side panel for chat navigation
        with me.box(style=me.Style(width="250px", border=me.Border.all(me.BorderSide(width=1, style="solid", color="#333")))):
            with me.box(style=me.Style(padding=me.Padding.all(10))):
                me.text("Chats", style=me.Style(font_weight="bold"))
                me.button("New Chat", on_click=new_chat, type="flat")
            with me.box(style=me.Style(flex_grow=1, overflow_y="auto")):
                for chat_id in state.chats:
                    with me.box(
                        key=chat_id,
                        on_click=lambda e, chat_id=chat_id: select_chat(e, chat_id),
                        style=me.Style(
                            padding=me.Padding.all(10),
                            cursor="pointer",
                            background="#444" if chat_id == state.chat_id else "transparent",
                            border=me.Border.all(me.BorderSide(width=1, style="solid", color="#555"))
                        ),
                    ):
                        me.text(chat_id)

        # Main chat area
        # Use the chat_id as a key on the container to force re-rendering
        with me.box(style=me.Style(flex_grow=1, display="flex", flex_direction="column"), key=state.chat_id):
            if state.chat_id:
                mel.chat(
                    transform,
                    title="J.A.R.V.I.S.",
                    bot_user="J.A.R.V.I.S.",
                )

def new_chat(e: me.ClickEvent):
    """Creates a new chat session."""
    state = me.state(State)
    new_chat_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    state.chats.insert(0, new_chat_id)
    state.chat_id = new_chat_id
    # Create an empty file for the new chat
    save_chat_history(new_chat_id, [])

def select_chat(e: me.ClickEvent, chat_id: str):
    """Switches to a selected chat."""
    state = me.state(State)
    state.chat_id = chat_id

def load_chat_history(chat_id: str) -> list[mel.ChatMessage]:
    """Loads chat history from a JSON file."""
    filepath = os.path.join(CHAT_DIR, f"{chat_id}.json")
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        try:
            data = json.load(f)
            return [mel.ChatMessage(role=msg["role"], content=msg["content"]) for msg in data]
        except (json.JSONDecodeError, KeyError):
            # If the file is corrupted or empty, return an empty list
            return []

def save_chat_history(chat_id: str, history: list[mel.ChatMessage]):
    """Saves chat history to a JSON file."""
    filepath = os.path.join(CHAT_DIR, f"{chat_id}.json")
    with open(filepath, "w") as f:
        json.dump([{"role": msg.role, "content": msg.content} for msg in history], f, indent=2)

def transform(input: str, history: list[mel.ChatMessage]):
    state = me.state(State)

    # If the history is empty, this is the first interaction in a chat session.
    # Load the history from the file system.
    if not history and state.chat_id:
        history.extend(load_chat_history(state.chat_id))

    # Append user input to history
    history.append(mel.ChatMessage(role="user", content=input))

    # Prepare messages for Ollama
    messages = [{"role": h.role, "content": h.content} for h in history if h.role]

    # Get response from Ollama
    stream = ollama.chat(model='llama3.1:8b', messages=messages, stream=True)

    # Stream response and save bot's reply
    bot_response = ""
    for chunk in stream:
        content = chunk.get('message', {}).get('content', '')
        if content:
            bot_response += content
            yield content

    # Append bot's final response to history and save the entire conversation once
    history.append(mel.ChatMessage(role="assistant", content=bot_response))
    if state.chat_id:
        save_chat_history(state.chat_id, history)