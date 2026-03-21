"""
PDF-Pal Streamlit Application.

This module serves as the primary entry point for the Streamlit web interface. 
It integrates the conversational RAG pipeline (PDF_Pal_App) with a user-friendly 
chat interface, allowing users to upload PDFs and ask questions about their content.
"""

import streamlit as st
import uuid
import datetime
from pathlib import Path
from src.PDF_Pal import PDF_Pal_App
from src.logger import logger

def initialize_session_state() -> None:
    # Initialize global app instance
    if "pdf_pal_app" not in st.session_state:
        try:
            st.session_state.pdf_pal_app = PDF_Pal_App()
            logger.info("PDF_Pal_App instance created and stored in session state.")
        except Exception as e:
            st.error(f"Error initializing app: {e}")
            logger.error(f"Error initializing app: {e}")
            st.stop()

    if "sessions" not in st.session_state:
        # Start with one default session
        initial_id = str(uuid.uuid4())
        st.session_state.sessions = {
            initial_id: {
                "name": "New Chat",
                "history": [],
                "created_at": datetime.datetime.now(),
                "docs_processed": False,
                "files": []
            }
        }
        st.session_state.current_session_id = initial_id

def inject_chat_css():
    css_file = Path("styles.css")
    if css_file.exists():
        st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)

def main() -> None:
    logger.info("Application started. Setting Streamlit page config.")

    st.set_page_config(
        page_title="PDF-Pal",
        page_icon="📄",
        layout="centered",
        initial_sidebar_state="expanded"
    )

    initialize_session_state()
    inject_chat_css()

    # Handle global flash alerts with a beautiful CSS fading banner
    if "flash_msg" in st.session_state:
        msg_type, msg_text = st.session_state.flash_msg
        banner_class = "flash-success" if msg_type == "success" else "flash-error"
        
        # Strictly inject a uniquely hashed keyframe animation overlay to fully bypass Streamlit's React DOM mutation batching
        div_id = str(uuid.uuid4()).replace("-", "")[:8]
        
        banner_html = f"""
        <style>
        @keyframes slide_{div_id} {{
            0% {{ top: -50px; opacity: 0; }}
            10% {{ top: 30px; opacity: 1; }}
            80% {{ top: 30px; opacity: 1; }}
            100% {{ top: -50px; opacity: 0; display: none; }}
        }}
        .anim-{div_id} {{
            animation: slide_{div_id} 5s ease-in-out forwards;
        }}
        </style>
        <div id="banner-{div_id}" class="flash-banner {banner_class} anim-{div_id}">{msg_text}</div>
        """
        st.markdown(banner_html, unsafe_allow_html=True)
        del st.session_state.flash_msg

    # --- Sidebar: Session Management ---
    with st.sidebar:
        st.title("📄 PDF-Pal")
        
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            new_id = str(uuid.uuid4())
            st.session_state.sessions[new_id] = {
                "name": "New Chat",
                "history": [],
                "created_at": datetime.datetime.now(),
                "docs_processed": False,
                "files": []
            }
            st.session_state.current_session_id = new_id
            st.session_state.flash_msg = ("success", "✅ New empty chat session successfully created!")
            st.rerun()

        st.divider()
        st.subheader("Recent Chats")
        
        # Session List
        sessions_sorted = sorted(st.session_state.sessions.items(), key=lambda x: x[1]['created_at'], reverse=True)
        for sid, sdata in sessions_sorted:
            
            label = sdata["name"]
            if sid == st.session_state.current_session_id:
                label = f"🟢 {label}"
            
            # Wrap the columns in a container
            with st.container():
                # We inject an empty HTML tag that acts as a hook for our CSS!
                st.markdown('<span class="sidebar-chat-btn-row"></span>', unsafe_allow_html=True)
                
                # Re-add columns, keep the ratios
                col_name, col_file, col_del = st.columns([0.7, 0.15, 0.15], vertical_alignment="center")

                with col_name:
                    if st.button(label, key=f"session_btn_{sid}", use_container_width=True):
                        st.session_state.current_session_id = sid
                        st.rerun()
                        
                with col_file:
                    toggle_key = f"toggle_upload_{sid}"
                    btn_ph = st.empty()
                    if btn_ph.button("📂", key=f"file_btn_{sid}", help="View/Upload Files", type="tertiary"):
                        st.session_state[toggle_key] = not st.session_state.get(toggle_key, False)
                        st.rerun()

                with col_del:
                    if st.button("🗑️", key=f"del_btn_{sid}", help="Delete chat", type="tertiary"):
                        # ... (Keep your existing delete logic here)
                        deleted_name = st.session_state.sessions[sid]["name"]
                        del st.session_state.sessions[sid]
                        # If active session was deleted, switch context
                        if st.session_state.current_session_id == sid:
                            if len(st.session_state.sessions) > 0:
                                st.session_state.current_session_id = sorted(
                                    st.session_state.sessions.items(), 
                                    key=lambda x: x[1]['created_at'], 
                                    reverse=True
                                )[0][0]
                            else:
                                new_id = str(uuid.uuid4())
                                st.session_state.sessions[new_id] = {
                                    "name": "New Chat", "history": [], "created_at": datetime.datetime.now(),
                                    "docs_processed": False, "files": []
                                }
                                st.session_state.current_session_id = new_id
                                
                        st.session_state.flash_msg = ("success", f"✅ Chat '{deleted_name}' successfully deleted!")
                        st.rerun()
            
            # Close the CSS grid wrapper
            st.markdown('</div>', unsafe_allow_html=True)

    # --- Main Chat Area Background Context ---
    # Retrieve current session data
    current_session_id = st.session_state.current_session_id
    current_session = st.session_state.sessions[current_session_id]

    st.markdown(f'<h1 class="sticky-title">{current_session["name"]}</h1>', unsafe_allow_html=True)

    if not current_session.get("docs_processed", False) and len(current_session["history"]) == 0:
        st.info("👈 Click the '📂' button next to this chat in the sidebar to upload a PDF.")

    # Render Chat History for Active Session
    for message in current_session["history"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- Chat Input ---
    if user_question := st.chat_input("Message PDF-Pal...", disabled=not current_session.get("docs_processed", False)):
        
        # 1. Display user message
        with st.chat_message("user"):
            st.markdown(user_question)
        
        # 2. Append to history
        current_session["history"].append({"role": "user", "content": user_question})
        
        # 3. Rename chat based on first query if it's still 'New Chat'
        if current_session["name"] == "New Chat":
            short_q = user_question if len(user_question) <= 20 else user_question[:17] + "..."
            current_session["name"] = short_q
            
        # 4. Generate AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = st.session_state.pdf_pal_app.ask(
                        query=user_question,
                        session_id=current_session_id,
                        context_window=10,
                        file_names=current_session.get("files", [])
                    )
                    if response:
                        st.markdown(response)
                        current_session["history"].append({"role": "assistant", "content": response})
                        # Explicit rerun to update the sidebar if name changed
                        st.rerun()
                except Exception as e:
                    st.session_state.flash_msg = ("error", f"❌ Error generating response: {str(e)}")
                    logger.error(f"Chat generation error: {e}")
                    st.rerun()

if __name__ == "__main__":
    main()