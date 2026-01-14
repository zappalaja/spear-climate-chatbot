"""
SPEAR Climate Data Chatbot
===========================
A Streamlit-based chatbot that uses Claude AI with MCP (Model Context Protocol)
tools to access and analyze SPEAR climate model data.

Features:
- Direct integration with SPEAR climate data via MCP tools
- Real-time data querying and analysis
- Conversational interface with context retention
- Tool execution with visual feedback
"""

import streamlit as st
import os
import json
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO

# Import configuration and tools
from ai_config import (
    MODEL_NAME,
    MAX_TOKENS,
    TEMPERATURE,
    SYSTEM_PROMPT,
    CHAT_TITLE,
    CHAT_INPUT_PLACEHOLDER,
    WELCOME_MESSAGE
)
from mcp_tools_wrapper import query_mcp_tool
from claude_tools import CLAUDE_TOOLS

# ============================================================================
# CONFIGURATION
# ============================================================================

# Add the src directory to the system path for SPEAR MCP tools access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Load environment variables (API keys, etc.)
load_dotenv()

# Initialize Anthropic Claude client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ============================================================================
# UI SETUP
# ============================================================================

st.title(CHAT_TITLE)

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Add a clear chat button in the sidebar
with st.sidebar:
    st.header("Chat Controls")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    # Show current message count
    msg_count = len(st.session_state.messages)
    st.caption(f"Messages in history: {msg_count}")
    if msg_count > 20:
        st.warning("⚠️ Long conversation history may cause rate limits")

    # Show rate limit info if available
    st.header("API Usage")
    if "rate_limits" in st.session_state:
        limits = st.session_state.rate_limits
        st.metric("Input Tokens (Last Request)", limits.get("input_tokens_used", "N/A"))
        st.metric("Output Tokens (Last Request)", limits.get("output_tokens_used", "N/A"))
        st.caption("⏱️ Rate limits reset every minute")
        st.caption("📊 For detailed limits, check Anthropic Console")
    else:
        st.caption("Token usage will appear after first message")

    # Add manual rate limit check button
    if st.button("🔍 Check Rate Limits Now"):
        with st.spinner("Checking rate limits..."):
            try:
                _ = client.messages.create(
                    model=MODEL_NAME,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hi"}],
                    system=SYSTEM_PROMPT,
                )
                st.success("✅ API connection successful!")
                st.info("Rate limit details will be shown after your next chat message")
            except Exception as e:
                st.error(f"Error checking limits: {str(e)}")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def save_chat_history():
    """
    Save the current chat history to a JSON file for debugging and review.
    Creates a timestamped log file in the chat_logs directory.
    """
    log_dir = "chat_logs"
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _log_file = os.path.join(log_dir, f"chat_history_{timestamp}.json")

    # Save the most recent version with a simple name too
    latest_file = os.path.join(log_dir, "chat_history_latest.json")

    try:
        with open(latest_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "message_count": len(st.session_state.messages),
                "messages": st.session_state.messages
            }, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving chat history: {e}")


def show_tool_output(result: dict):
    """
    Display structured tool results and optional plots.

    Args:
        result: Dictionary containing tool execution results with 'status', 'tool', and 'data' keys
    """
    if result.get("status") != "ok":
        st.error(result.get("error"))
        return

    # Special handling for NetCDF data queries
    if result["tool"] == "query_netcdf_data" and isinstance(result.get("data"), dict):
        info = result["data"].get("data_info", {})
        st.write(f"**Variable:** {result['data'].get('variable')} — shape {info.get('shape')}")
        plot_data_preview(result["data"])

    # Show full JSON result in an expander
    with st.expander("Show full JSON result"):
        st.json(result)


def plot_data_preview(data_dict: dict):
    """
    Generate a quick matplotlib plot for climate data arrays.

    Args:
        data_dict: Dictionary containing climate data arrays
    """
    try:
        arr = np.array(data_dict.get("data"))
        if arr.ndim == 2:
            st.pyplot(plt.imshow(arr, aspect='auto'))
        elif arr.ndim == 1:
            plt.plot(arr)
            st.pyplot(plt)
    except Exception as e:
        st.info(f"❌ Error plotting data: {e}")


def retrieve_rag_context(query: str, k: int = 5) -> str:
    """
    Retrieve relevant context from the RAG FastAPI service.

    IMPORTANT:
    - Uses POST /query with JSON body: {"query": "...", "k": 5}
    - Never injects a 'system' role into messages (Anthropic doesn't allow that).
    """
    rag_url = os.getenv("RAG_API_URL", "http://localhost:8002").rstrip("/")
    try:
        r = requests.post(
            f"{rag_url}/query",
            json={"query": query, "k": k},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        if not results:
            return ""
        return "\n\n".join([x.get("content", "") for x in results if x.get("content")])
    except Exception as e:
        print(f"RAG retrieval failed: {e}")
        return ""


def build_augmented_user_prompt(user_text: str) -> str:
    """
    Pull RAG context and return a user prompt augmented with it.
    This avoids putting 'system' messages into the Anthropic messages list.
    """
    rag_k = int(os.getenv("RAG_TOP_K", "5"))
    rag_context = retrieve_rag_context(user_text, k=rag_k)
    if not rag_context.strip():
        return user_text

    return (
        "Use the retrieved context below if it is relevant. "
        "If it is not relevant, ignore it.\n\n"
        "--- RAG CONTEXT START ---\n"
        f"{rag_context}\n"
        "--- RAG CONTEXT END ---\n\n"
        f"User question: {user_text}"
    )


def sanitize_messages_for_anthropic(messages: list[dict]) -> list[dict]:
    """
    Anthropic Messages API does NOT allow role='system' inside messages.
    This function also strips any accidental tool_result-only user blocks from UI artifacts.
    """
    cleaned = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            continue
        cleaned.append(m)
    return cleaned


# ============================================================================
# CHAT INTERFACE
# ============================================================================

# Display welcome message if chat is empty
if len(st.session_state.messages) == 0:
    with st.chat_message("assistant"):
        st.markdown(WELCOME_MESSAGE)

# Display chat history
for message in st.session_state.messages:
    # No system messages exist anymore, but keep this as a safety check
    if message.get("role") == "system":
        continue

    with st.chat_message(message["role"]):
        content = message["content"]
        if isinstance(content, str):
            st.markdown(content)
        elif isinstance(content, list):
            # Skip tool_result messages (internal API communication)
            if message["role"] == "user" and any(
                isinstance(item, dict) and item.get("type") == "tool_result"
                for item in content
            ):
                continue
            # For assistant messages with mixed content, just show text blocks
            for item in content:
                if hasattr(item, 'text'):
                    st.markdown(item.text)

# Handle user input
if prompt := st.chat_input(CHAT_INPUT_PLACEHOLDER):
    # Show the user's *clean* message in UI
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build the augmented prompt (RAG is injected here, NOT as role=system)
    augmented_prompt = build_augmented_user_prompt(prompt)

    # Store the augmented prompt in history (what the model sees)
    st.session_state.messages.append({"role": "user", "content": augmented_prompt})

    # Generate assistant response
    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("_Thinking..._")
        full_resp = ""

        try:
            # Prepare messages for Anthropic (no system role allowed in list)
            anthropic_messages = sanitize_messages_for_anthropic(st.session_state.messages)

            # ====================================================================
            # PHASE 1: Initial Claude Response (may include tool use requests)
            # ====================================================================
            with client.messages.stream(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=SYSTEM_PROMPT,
                tools=CLAUDE_TOOLS,
                messages=anthropic_messages,
            ) as stream:
                for text in stream.text_stream:
                    full_resp += text
                    msg_placeholder.markdown(full_resp + "▌")

                final_msg = stream.get_final_message()

                # Capture rate limit info from response
                try:
                    usage = final_msg.usage
                    st.session_state.rate_limits = {
                        "requests_remaining": "See Anthropic Console",
                        "tokens_remaining": "See Anthropic Console",
                        "input_tokens_used": usage.input_tokens if hasattr(usage, 'input_tokens') else "N/A",
                        "output_tokens_used": usage.output_tokens if hasattr(usage, 'output_tokens') else "N/A",
                        "reset_time": "Resets every minute",
                    }
                except Exception:
                    pass

                # ====================================================================
                # PHASE 2: Tool Execution Loop (continues until Claude is done)
                # ====================================================================
                if final_msg.stop_reason == "tool_use":
                    current_msg = final_msg
                    max_tool_iterations = 10  # Safety limit to prevent infinite loops
                    iteration = 0
                    tool_execution_log = []  # Track tool executions separately
                    size_warning_encountered = False  # Flag to stop loop if query too large

                    while (
                        current_msg.stop_reason == "tool_use"
                        and iteration < max_tool_iterations
                        and not size_warning_encountered
                    ):
                        iteration += 1
                        tool_results = []

                        # Execute each tool that Claude requested
                        for content_block in current_msg.content:
                            if content_block.type == "tool_use":
                                tool_name = content_block.name
                                tool_input = content_block.input

                                # Log tool execution
                                tool_log_entry = f"🔧 **Using tool:** `{tool_name}`"
                                tool_execution_log.append(tool_log_entry)

                                # Show current progress
                                current_display = full_resp + "\n\n" + "\n".join(tool_execution_log)
                                msg_placeholder.markdown(current_display)

                                # Execute the tool
                                with st.spinner(f"Executing {tool_name}..."):
                                    result = query_mcp_tool(tool_name, tool_input)

                                # Update log with completion status
                                if result.get("status") == "ok":
                                    tool_execution_log[-1] += " ✅"

                                    # Special handling for plot tool
                                    if tool_name == "create_plot":
                                        fig = result.get("data", {}).get("figure")
                                        if fig is not None:
                                            st.pyplot(fig)

                                            buf = BytesIO()
                                            fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                                            buf.seek(0)

                                            st.download_button(
                                                label="📥 Download Plot (PNG)",
                                                data=buf,
                                                file_name=f"climate_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                                                mime="image/png",
                                            )

                                            import matplotlib.pyplot as _plt
                                            _plt.close(fig)
                                        else:
                                            with st.expander(f"View {tool_name} results"):
                                                st.json(result.get("data"))
                                    else:
                                        with st.expander(f"View {tool_name} results"):
                                            st.json(result.get("data"))
                                else:
                                    error_type = result.get("error", "")

                                    if (
                                        "Query too large" in error_type
                                        or "Invalid latitude range" in error_type
                                        or "Invalid longitude range" in error_type
                                    ):
                                        if "Query too large" in error_type:
                                            tool_execution_log[-1] += " ⚠️ Query too large - prevented execution"
                                        else:
                                            tool_execution_log[-1] += " ⚠️ Invalid coordinates - prevented execution"

                                        size_warning_encountered = True

                                        warning_msg = result.get("warning_message", "")
                                        if warning_msg:
                                            st.warning("Query Issue")
                                            st.markdown(warning_msg)

                                            data_shape = result.get("data_shape", {})
                                            if data_shape:
                                                with st.expander("📊 Query Details"):
                                                    st.write(f"**Time points:** {data_shape.get('time_points', 'N/A'):,}")
                                                    st.write(f"**Latitude points:** {data_shape.get('lat_points', 'N/A'):,}")
                                                    st.write(f"**Longitude points:** {data_shape.get('lon_points', 'N/A'):,}")
                                                    st.write(f"**Total data points:** {data_shape.get('total_data_points', 'N/A'):,}")
                                                    st.write(f"**Estimated tokens:** {result.get('estimated_tokens', 'N/A'):,}")
                                    else:
                                        tool_execution_log[-1] += f" ❌ Error: {result.get('error')}"

                                current_display = full_resp + "\n\n" + "\n".join(tool_execution_log)
                                msg_placeholder.markdown(current_display)

                                # Prepare tool result for Claude
                                if result.get("status") == "error" and "Query too large" in result.get("error", ""):
                                    tool_results.append({
                                        "type": "tool_result",
                                        "tool_use_id": content_block.id,
                                        "is_error": True,
                                        "content": result.get("warning_message", result.get("error", "Query too large")),
                                    })
                                else:
                                    try:
                                        content_str = json.dumps(result, default=str)
                                    except (TypeError, ValueError, json.JSONDecodeError) as e:
                                        content_str = f"Tool result serialization error: {str(e)}\nRaw result: {str(result)}"

                                    tool_results.append({
                                        "type": "tool_result",
                                        "tool_use_id": content_block.id,
                                        "content": content_str,
                                    })

                        # If size warning encountered, don't add to history or continue
                        if size_warning_encountered:
                            final_msg_text = "\n\n**⚠️ Query size exceeds limits. Please provide a smaller query or choose one of the alternatives above.**"
                            current_display = full_resp + "\n\n" + "\n".join(tool_execution_log) + final_msg_text
                            msg_placeholder.markdown(current_display)

                            st.session_state.messages.append({"role": "assistant", "content": current_display})
                            save_chat_history()
                            break

                        # Add assistant's tool use to history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": current_msg.content,
                        })

                        # Add tool results to history
                        st.session_state.messages.append({
                            "role": "user",
                            "content": tool_results,
                        })

                        current_display = full_resp + "\n\n" + "\n".join(tool_execution_log)
                        msg_placeholder.markdown(current_display + "\n\n_Processing..._")

                        # Ask Claude what to do next
                        anthropic_messages = sanitize_messages_for_anthropic(st.session_state.messages)

                        with client.messages.stream(
                            model=MODEL_NAME,
                            max_tokens=MAX_TOKENS,
                            temperature=TEMPERATURE,
                            system=SYSTEM_PROMPT,
                            tools=CLAUDE_TOOLS,
                            messages=anthropic_messages,
                        ) as followup_stream:
                            text_response = ""
                            for text in followup_stream.text_stream:
                                text_response += text
                                msg_placeholder.markdown(current_display + "\n\n" + text_response + "▌")

                            current_msg = followup_stream.get_final_message()

                    # After loop completes, combine everything for final display
                    if tool_execution_log:
                        full_resp += "\n\n" + "\n".join(tool_execution_log)
                    if "text_response" in locals() and text_response:
                        full_resp += "\n\n" + text_response

                    msg_placeholder.markdown(full_resp)

                    # Add final response to history
                    st.session_state.messages.append({"role": "assistant", "content": full_resp})
                    save_chat_history()

                else:
                    # No tool use, just display the response
                    msg_placeholder.markdown(full_resp)
                    st.session_state.messages.append({"role": "assistant", "content": full_resp})
                    save_chat_history()

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            msg_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            save_chat_history()
