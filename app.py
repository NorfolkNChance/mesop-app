import ollama
import mesop as me
import mesop.labs as mel

def load(e: me.LoadEvent):
    me.set_theme_mode("dark")

@me.page(
    on_load=load,
    path="/",
    title="J.A.R.V.I.S.",
    security_policy=me.SecurityPolicy(
        allowed_script_srcs=[
            "self", # Allow scripts from same origin.
            "unsafe-inline",    # Allow inline scripts if needed.
            "unsafe-eval",  # Allow eval if needed for WASM.
            "blob:",    # Allow blob URLs.
            "https:",   # Allow HTTPS sources.
            "http:",    # Allow HTTP sources (consider removing in production).
            "chrome-extension:",    # Allow Chrome extensions if needed.
        ]
    ),
)

def page():
    mel.chat(transform, title="J.A.R.V.I.S.", bot_user="J.A.R.V.I.S.")

def transform(input: str, history: list[mel.ChatMessage]):
    messages = [{"role": "user", "content": message.content} for message in history]
    messages.append({"role": "user", "content": input})

    stream = ollama.chat(model='deepseek-r1:8b', messages=messages, stream=True)

    for chunk in stream:
        content = chunk.get('message', {}).get('content', '')
        if content:
            yield content

