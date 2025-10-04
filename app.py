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
    input: str = ""

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
        save_chat_history(new_chat_id, [])


@me.page(
    on_load=on_load,
    path="/",
    title="J.A.R.V.I.S.",
    security_policy=me.SecurityPolicy(
        dangerously_disable_trusted_types=True,
    ),
)
def page():
    state = me.state(State)
    with me.box(style=me.Style(display="flex", height="100vh")):
        # Side panel for chat navigation
        with me.box(style=me.Style(width="300px", border=me.Border.all(me.BorderSide(width=1, style="solid", color="#333")), display="flex", flex_direction="column")):
            with me.box(style=me.Style(padding=me.Padding.all(10), border=me.Border(bottom=me.BorderSide(width=1, style="solid", color="#333")))):
                me.text("Chats", style=me.Style(font_weight="bold", font_size=20))
                me.button("New Chat", on_click=new_chat, type="flat")
            with me.box(style=me.Style(flex_grow=1, overflow_y="auto")):
                for chat_id in state.chats:
                    with me.box(
                        key=chat_id,
                        style=me.Style(
                            padding=me.Padding.all(15),
                            cursor="pointer",
                            background="#444" if chat_id == state.chat_id else "transparent",
                            border=me.Border(bottom=me.BorderSide(width=1, style="solid", color="#555")),
                            display="flex",
                            align_items="center",
                            justify_content="space-between",
                        ),
                    ):
                        with me.box(on_click=lambda e, cid=chat_id: select_chat(e, cid), style=me.Style(flex_grow=1)):
                            me.text(chat_id, style=me.Style(font_size=16))
                        with me.box(on_click=lambda e, cid=chat_id: delete_chat(e, cid)):
                            me.icon("delete")

        # Main chat area
        with me.box(style=me.Style(flex_grow=1, display="flex", flex_direction="column", height="100vh")):
            # Chat messages area
            with me.box(style=me.Style(flex_grow=1, overflow_y="auto", padding=me.Padding.all(20))):
                if state.chat_id:
                    history = load_chat_history(state.chat_id)
                    for msg in history:
                        with me.box(style=me.Style(
                            margin=me.Margin(bottom=15),
                            padding=me.Padding.all(15),
                            border_radius=10,
                            background="#333" if msg.role == "user" else "#444",
                            box_shadow="0 2px 4px rgba(0,0,0,0.1)"
                        )):
                            me.markdown(f"**{msg.role.capitalize()}**")
                            me.markdown(msg.content)

            # Chat input area
            with me.box(style=me.Style(padding=me.Padding.all(20), border=me.Border(top=me.BorderSide(width=1, style="solid", color="#333")))):
                with me.box(style=me.Style(display="flex")):
                    me.input(
                        label="Enter your prompt",
                        value=state.input,
                        on_input=on_input,
                        on_enter=send_message,
                        style=me.Style(flex_grow=1, margin=me.Margin(right=10)),
                    )
                    me.button("Send", on_click=send_message)


def on_input(e: me.InputEvent):
    state = me.state(State)
    state.input = e.value

def send_message(e: me.ClickEvent):
    state = me.state(State)
    if not state.input.strip():
        return

    if state.chat_id:
        history = load_chat_history(state.chat_id)
        history.append(mel.ChatMessage(role="user", content=state.input))
        save_chat_history(state.chat_id, history)

        # Prepare messages for Ollama
        messages = [{"role": h.role, "content": h.content} for h in history if h.role]

        # Get response from Ollama
        stream = ollama.chat(model='llama3.1:8b', messages=messages, stream=True)

        bot_response = ""
        for chunk in stream:
            content = chunk.get('message', {}).get('content', '')
            if content:
                bot_response += content

        history.append(mel.ChatMessage(role="assistant", content=bot_response))
        save_chat_history(state.chat_id, history)

    # Clear the input field
    state.input = ""


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

def delete_chat(e: me.ClickEvent, chat_id: str):
    """Deletes a chat session."""
    state = me.state(State)

    # Remove the chat file
    filepath = os.path.join(CHAT_DIR, f"{chat_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)

    # Remove from the chats list
    if chat_id in state.chats:
        state.chats.remove(chat_id)

    # If the deleted chat was the active one, select another chat
    if state.chat_id == chat_id:
        if state.chats:
            state.chat_id = state.chats[0]
        else:
            # If no chats are left, create a new one
            new_chat(e)

def load_chat_history(chat_id: str) -> list[mel.ChatMessage]:
    """Loads chat history from a JSON file."""
    filepath = os.path.join(CHAT_DIR, f"{chat_id}.json")
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        try:
            data = json.load(f)
            # Handle the case where the file is empty
            if not data:
                return []
            return [mel.ChatMessage(role=msg["role"], content=msg["content"]) for msg in data]
        except (json.JSONDecodeError, KeyError):
            # If the file is corrupted or empty, return an empty list
            return []

def save_chat_history(chat_id: str, history: list[mel.ChatMessage]):
    """Saves chat history to a JSON file."""
    filepath = os.path.join(CHAT_DIR, f"{chat_id}.json")
    with open(filepath, "w") as f:
        json.dump([{"role": msg.role, "content": msg.content} for msg in history], f, indent=2)