import streamlit as st
import requests
import uuid
import os

# Set page config
st.set_page_config(
    page_title="Gluzo AI Assistant",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Custom CSS for extra colorful styling
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    .stTextInput input {
        border-radius: 10px;
    }
    .chat-bubble {
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        color: white;
    }
    .user-bubble {
        background: linear-gradient(90deg, #ff007f 0%, #7928ca 100%);
        align-self: flex-end;
    }
    .bot-bubble {
        background: linear-gradient(90deg, #00c6ff 0%, #0072ff 100%);
        align-self: flex-start;
    }
    h1 {
        background: -webkit-linear-gradient(#ff007f, #00c6ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

st.title("✨ Gluzo AI Assistant")

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state["messages"] = []

API_URL = "http://localhost:8000/api"

def display_chat():
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.write(msg["content"])
                if "image_urls" in msg and msg["image_urls"]:
                    for img_url in msg["image_urls"]:
                        st.image(img_url)

display_chat()

# Sidebar for file uploads
with st.sidebar:
    st.header("🎨 Media Upload")
    st.markdown("Upload images or audio to interact with the AI.")
    
    uploaded_image = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])
    uploaded_audio = st.file_uploader("Upload Audio", type=["mp3", "wav", "m4a", "ogg"])
    
    if st.button("Send Image") and uploaded_image is not None:
        with st.spinner("Processing image..."):
            files = {"file": (uploaded_image.name, uploaded_image.getvalue(), uploaded_image.type)}
            data = {"session_id": st.session_state["session_id"]}
            try:
                response = requests.post(f"{API_URL}/chat/image", data=data, files=files)
                response_data = response.json()
                st.session_state["messages"].append({"role": "user", "content": f"[Sent an Image: {uploaded_image.name}]"})
                st.session_state["messages"].append({
                    "role": "assistant", 
                    "content": response_data.get("reply", "No reply received."),
                    "image_urls": response_data.get("image_urls", [])
                })
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("Send Audio") and uploaded_audio is not None:
        with st.spinner("Processing audio..."):
            files = {"file": (uploaded_audio.name, uploaded_audio.getvalue(), uploaded_audio.type)}
            data = {"session_id": st.session_state["session_id"]}
            try:
                response = requests.post(f"{API_URL}/chat/audio", data=data, files=files)
                response_data = response.json()
                st.session_state["messages"].append({"role": "user", "content": f"[Sent Audio: {uploaded_audio.name}]"})
                st.session_state["messages"].append({
                    "role": "assistant", 
                    "content": response_data.get("reply", "No reply received."),
                    "image_urls": response_data.get("image_urls", [])
                })
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# Text input at the bottom
if prompt := st.chat_input("Type your message here..."):
    # Add user message to state
    st.session_state["messages"].append({"role": "user", "content": prompt})
    
    # Show user message immediately
    with st.chat_message("user", avatar="👤"):
        st.write(prompt)
        
    with st.spinner("Thinking..."):
        try:
            response = requests.post(
                f"{API_URL}/chat", 
                json={"session_id": st.session_state["session_id"], "message": prompt}
            )
            response_data = response.json()
            reply = response_data.get("reply", "No reply received.")
            images = response_data.get("image_urls", [])
            
            st.session_state["messages"].append({
                "role": "assistant",
                "content": reply,
                "image_urls": images
            })
            st.rerun()
        except Exception as e:
            st.error(f"Error connecting to backend: {e}")
