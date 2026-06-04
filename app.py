import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import os
import json
from omni_agent import UniversalAgent

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="S.M.A.R.T. AI")

# 2. Authentication Setup
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'], config['cookie']['name'], 
    config['cookie']['key'], config['cookie']['expiry_days']
)

authenticator.login()

if st.session_state["authentication_status"]:
    # --- INITIALIZATION ---
    if "agent" not in st.session_state:
        # Pass your Hugging Face Access Token ('hf_...') here to authorize serverless API queries
        st.session_state.agent = UniversalAgent("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")
    if "sessions" not in st.session_state:
        st.session_state.sessions = {"Chat 1": []}
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = "Chat 1"

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("S.M.A.R.T. AI Hub")
        if st.button("➕ New Session"):
            new_id = f"Chat {len(st.session_state.sessions) + 1}"
            st.session_state.sessions[new_id] = []
            st.session_state.current_chat = new_id
            st.rerun()
        
        st.divider()
        for chat_name in st.session_state.sessions.keys():
            if st.button(chat_name, key=chat_name, use_container_width=True):
                st.session_state.current_chat = chat_name
                st.rerun()
        
        st.divider()
        authenticator.logout('Logout', 'sidebar')

    # --- MAIN INTERFACE ---
    st.title(f"🤖 {st.session_state.current_chat}")

    # Render History with Download Logic
    for msg in st.session_state.sessions[st.session_state.current_chat]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # The button only appears if 'file_path' exists in the message data
            if "file_path" in msg and os.path.exists(msg["file_path"]):
                with open(msg["file_path"], "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download {os.path.basename(msg['file_path'])}",
                        data=f,
                        file_name=os.path.basename(msg["file_path"]),
                        mime="application/octet-stream"
                    )

    # Chat Input
    if prompt := st.chat_input("Initiate command..."):
        st.session_state.sessions[st.session_state.current_chat].append({"role": "user", "content": prompt})
        
        # Call agent and parse the JSON string response
        json_response = st.session_state.agent.handle_request(prompt)
        data = json.loads(json_response)
        
        # Extract message and path
        response_text = data.get("message", "Request processed.")
        file_path = data.get("file_path")
            
        msg_data = {"role": "assistant", "content": response_text}
        if file_path:
            msg_data["file_path"] = file_path
            
        st.session_state.sessions[st.session_state.current_chat].append(msg_data)
        st.rerun()

elif st.session_state["authentication_status"] is False:
    st.error("Username/password is incorrect")
elif st.session_state["authentication_status"] is None:
    st.warning("Please enter your credentials to access S.M.A.R.T. AI")