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
                # Make a minimal API call to get headers
                test_response = client.messages.create(
                    model=MODEL_NAME,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hi"}]
                )
                # The response headers contain rate limit info
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
    log_file = os.path.join(log_dir, f"chat_history_{timestamp}.json")

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
    Returns a formatted context block or empty string on failure.

    Env vars:
      - RAG_API_URL: base URL of the retrieval service (default: http://localhost:8002)
    """
    rag_url = os.getenv("RAG_API_URL", "http://localhost:8002").rstrip("/")

    try:
        resp = requests.get(
            f"{rag_url}/retrieve",
            params={"q": query, "k": k},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        parts = []
        for item in data.get("results", []):
            source = item.get("source", "unknown")
            text = item.get("text", "")
            if text:
                parts.append(f"SOURCE: {source}\n{text}")

        if not parts:
            return ""

        # Keep it bounded so you don't explode token usage
        # (Optional tweak: cap total chars)
        context = "\n\n---\n\n".join(parts)
        max_chars = int(os.getenv("RAG_CONTEXT_MAX_CHARS", "8000"))
        if len(context) > max_chars:
            context = context[:max_chars] + "\n\n[...context truncated...]"

        return (
            "### Retrieved Context (use when relevant)\n"
            "Use the following excerpts as grounding. Cite SOURCE filenames when using facts.\n\n"
            + context
        )

    except Exception as e:
        # Fail silently; chatbot should still work without RAG
        print(f"RAG retrieval failed: {e}")
        return ""


# ============================================================================
# CHAT INTERFACE
# ============================================================================

# Display welcome message if chat is empty
if len(st.session_state.messages) == 0:
    with st.chat_message("assistant"):
        st.markdown(WELCOME_MESSAGE)

# Display chat history
for message in st.session_state.messages:
    # Do not display internal system messages (e.g., injected RAG context)
    if message.get("role") == "system":
        continue

    with st.chat_message(message["role"]):
        # Handle both string content and list content (from Claude API)
        content = message["content"]
        if isinstance(content, str):
            st.markdown(content)
        elif isinstance(content, list):
            # Skip tool_result messages (internal API communication)
            if message["role"] == "user" and any(isinstance(item, dict) and item.get("type") == "tool_result" for item in content):
                continue
            # For assistant messages with mixed content, just show text blocks
            for item in content:
                if hasattr(item, 'text'):
                    st.markdown(item.text)

# Handle user input
if prompt := st.chat_input(CHAT_INPUT_PLACEHOLDER):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ------------------------------------------------------------------------
    # RAG RETRIEVAL (FastAPI / Chroma) - injected as a SYSTEM message
    # (not displayed in the UI; see history loop above)
    # ------------------------------------------------------------------------
    rag_context = retrieve_rag_context(prompt, k=int(os.getenv("RAG_TOP_K", "5")))
    if rag_context:
        st.session_state.messages.append({"role": "system", "content": rag_context})

    # Generate assistant response
    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("_Thinking..._")
        full_resp = ""

        try:
            # ====================================================================
            # PHASE 1: Initial Claude Response (may include tool use requests)
            # ====================================================================
            # Stream the message generation from the Anthropic API with tools
            with client.messages.stream(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=SYSTEM_PROMPT,
                tools=CLAUDE_TOOLS,
                messages=st.session_state.messages
            ) as stream:
                for text in stream.text_stream:
                    full_resp += text
                    msg_placeholder.markdown(full_resp + "▌")

                final_msg = stream.get_final_message()

                # Capture rate limit info from response
                try:
                    from datetime import datetime, timedelta
                    usage = final_msg.usage
                    st.session_state.rate_limits = {
                        "requests_remaining": "See Anthropic Console",
                        "tokens_remaining": "See Anthropic Console",
                        "input_tokens_used": usage.input_tokens if hasattr(usage, 'input_tokens') else "N/A",
                        "output_tokens_used": usage.output_tokens if hasattr(usage, 'output_tokens') else "N/A",
                        "reset_time": "Resets every minute"
                    }
                except Exception as e:
                    pass  # Silently fail if rate limit info not available

                # ====================================================================
                # PHASE 2: Tool Execution Loop (continues until Claude is done)
                # ====================================================================
                if final_msg.stop_reason == "tool_use":
                    current_msg = final_msg
                    max_tool_iterations = 10  # Safety limit to prevent infinite loops
                    iteration = 0
                    tool_execution_log = []  # Track tool executions separately
                    size_warning_encountered = False  # Flag to stop loop if query too large

                    while current_msg.stop_reason == "tool_use" and iteration < max_tool_iterations and not size_warning_encountered:
                        iteration += 1
                        tool_results = []

                        # Execute each tool that Claude requested
                        for content_block in current_msg.content:
                            if content_block.type == "tool_use":
                                tool_name = content_block.name
                                tool_input = content_block.input

                                # Log tool execution (don't duplicate in full_resp)
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
                                    tool_execution_log[-1] += f" ✅"

                                    # Special handling for plot tool
                                    if tool_name == "create_plot":
                                        fig = result.get("data", {}).get("figure")
                                        if fig is not None:
                                            # Display the plot
                                            st.pyplot(fig)

                                            # Add download button for the plot
                                            buf = BytesIO()
                                            fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                                            buf.seek(0)

                                            st.download_button(
                                                label="📥 Download Plot (PNG)",
                                                data=buf,
                                                file_name=f"climate_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                                                mime="image/png"
                                            )

                                            import matplotlib.pyplot as plt
                                            plt.close(fig)  # Clean up
                                        else:
                                            with st.expander(f"View {tool_name} results"):
                                                st.json(result.get("data"))
                                    else:
                                        with st.expander(f"View {tool_name} results"):
                                            st.json(result.get("data"))
                                else:
                                    # Check error type
                                    error_type = result.get('error', '')

                                    # Size warning or invalid coordinate error - stop execution
                                    if "Query too large" in error_type or "Invalid latitude range" in error_type or "Invalid longitude range" in error_type:
                                        if "Query too large" in error_type:
                                            tool_execution_log[-1] += f" ⚠️ Query too large - prevented execution"
                                        else:
                                            tool_execution_log[-1] += f" ⚠️ Invalid coordinates - prevented execution"

                                        # Set flag to stop tool loop
                                        size_warning_encountered = True

                                        # Display formatted warning message
                                        warning_msg = result.get('warning_message', '')
                                        if warning_msg:
                                            if "Invalid" in error_type and "range" in error_type:
                                                st.warning("Invalid Coordinate Range")
                                            else:
                                                st.warning("Query Size Warning")
                                            st.markdown(warning_msg)

                                            # Show data shape info (for size warnings only)
                                            data_shape = result.get('data_shape', {})
                                            if data_shape:
                                                with st.expander("📊 Query Details"):
                                                    st.write(f"**Time points:** {data_shape.get('time_points', 'N/A'):,}")
                                                    st.write(f"**Latitude points:** {data_shape.get('lat_points', 'N/A'):,}")
                                                    st.write(f"**Longitude points:** {data_shape.get('lon_points', 'N/A'):,}")
                                                    st.write(f"**Total data points:** {data_shape.get('total_data_points', 'N/A'):,}")
                                                    st.write(f"**Estimated tokens:** {result.get('estimated_tokens', 'N/A'):,}")
                                    else:
                                        # Regular error
                                        tool_execution_log[-1] += f" ❌ Error: {result.get('error')}"

                                current_display = full_resp + "\n\n" + "\n".join(tool_execution_log)
                                msg_placeholder.markdown(current_display)

                                # Prepare tool result for Claude
                                # Check if this is a size warning - mark as error to stop Claude from retrying
                                if result.get("status") == "error" and "Query too large" in result.get('error', ''):
                                    # Send as error with warning message to Claude
                                    tool_results.append({
                                        "type": "tool_result",
                                        "tool_use_id": content_block.id,
                                        "is_error": True,  # Tell Claude this is a terminal error
                                        "content": result.get('warning_message', result.get('error', 'Query too large'))
                                    })
                                else:
                                    # Regular tool result (success or regular error)
                                    try:
                                        content_str = json.dumps(result, default=str)
                                    except (TypeError, ValueError, json.JSONDecodeError) as e:
                                        content_str = f"Tool result serialization error: {str(e)}\nRaw result: {str(result)}"

                                    tool_results.append({
                                        "type": "tool_result",
                                        "tool_use_id": content_block.id,
                                        "content": content_str
                                    })

                        # If size warning encountered, don't add to history or continue
                        if size_warning_encountered:
                            # Display message telling user to provide new query
                            final_msg_text = "\n\n**⚠️ Query size exceeds limits. Please provide a smaller query or choose one of the alternatives above.**"
                            current_display = full_resp + "\n\n" + "\n".join(tool_execution_log) + final_msg_text
                            msg_placeholder.markdown(current_display)
                            text_response = final_msg_text

                            # Add just the initial response to history (not the failed tool attempt)
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": current_display
                            })
                            save_chat_history()
                            break  # Exit the tool loop immediately

                        # Add assistant's tool use to history (only if no size warning)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": current_msg.content
                        })

                        # Add tool results to history (only if no size warning)
                        st.session_state.messages.append({
                            "role": "user",
                            "content": tool_results
                        })

                        # Ask Claude what to do next
                        msg_placeholder.markdown(current_display + "\n\n_Processing..._")

                        with client.messages.stream(
                            model=MODEL_NAME,
                            max_tokens=MAX_TOKENS,
                            temperature=TEMPERATURE,
                            system=SYSTEM_PROMPT,
                            tools=CLAUDE_TOOLS,
                            messages=st.session_state.messages
                        ) as followup_stream:
                            # Collect any text response
                            text_response = ""
                            for text in followup_stream.text_stream:
                                text_response += text
                                msg_placeholder.markdown(current_display + "\n\n" + text_response + "▌")

                            # Get the next message
                            current_msg = followup_stream.get_final_message()

                    # After loop completes, combine everything for final display
                    if tool_execution_log:
                        full_resp += "\n\n" + "\n".join(tool_execution_log)
                    if text_response:
                        full_resp += "\n\n" + text_response

                    # Final display after all tools are done
                    msg_placeholder.markdown(full_resp)

                    # Add final response to history
                    st.session_state.messages.append({"role": "assistant", "content": full_resp})
                    save_chat_history()  # Save after assistant response
                else:
                    # No tool use, just display the response
                    msg_placeholder.markdown(full_resp)
                    st.session_state.messages.append({"role": "assistant", "content": full_resp})
                    save_chat_history()  # Save after assistant response

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            msg_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            save_chat_history()  # Save even on error
