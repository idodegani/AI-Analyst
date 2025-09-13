
# STEP 1: Install the correct, current packages3
#!pip install llama-index llama-cloud-services llama-index-llms-openai -q


# STEP 1: Install the correct, current packages
# !pip install llama-index llama-cloud-services llama-index-llms-openai -q

# STEP 2: Import required libraries
import os
import sys
import json
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_cloud_services import LlamaCloudIndex
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage

# STEP 3: Configuration
os.environ["OPENAI_API_KEY"] = "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"
LLAMA_CLOUD_API_KEY = "llx-hgbCEzLC1FOiv2hs7ldeHVzdtfOLPmIx9RQyBOzW4Mer611L"
LLAMA_CLOUD_INDEX_NAME = "GSTY_INDEX"
LLAMA_CLOUD_PROJECT_NAME = "Default"
LLAMA_CLOUD_ORGANIZATION_ID = "acd2b482-30f4-461d-a101-0190a08b0a87"

HISTORY_FILE = "chat_histories.json"

# STEP 4: Session Management Functions
def save_histories(histories_dict):
    """Saves the chat histories to a JSON file."""
    serializable_histories = {}
    for session_id, memory in histories_dict.items():
        # --- FIX 1: Changed .dict() to .model_dump() to fix deprecation warning ---
        serializable_histories[session_id] = [msg.model_dump() for msg in memory.get_all()]
    with open(HISTORY_FILE, 'w') as f:
        json.dump(serializable_histories, f)

def load_histories():
    """Loads chat histories from a JSON file."""
    try:
        if os.path.exists(HISTORY_FILE) and os.path.getsize(HISTORY_FILE) > 0:
            with open(HISTORY_FILE, 'r') as f:
                serializable_histories = json.load(f)
        else:
            return {}
    except Exception as e:
        print(f"⚠️ Warning: Could not load chat histories. Error: {e}")
        return {}

    histories_dict = {}
    for session_id, messages in serializable_histories.items():
        try:
            chat_messages = [ChatMessage(**msg) for msg in messages]
            # --- FIX 2: Use .from_defaults() for proper initialization ---
            memory = ChatMemoryBuffer.from_defaults(
                chat_history=chat_messages,
                token_limit=3900
            )
            histories_dict[session_id] = memory
        except Exception as e:
            print(f"⚠️ Warning: Could not load session '{session_id}'. Skipping. Error: {e}")
            continue
    return histories_dict

# STEP 5: Main Application Logic
def main():
    Settings.llm = OpenAI(model="gpt-4o", temperature=0.1)

    print("Connecting to LlamaCloud index...")
    try:
        index = LlamaCloudIndex(
            name=LLAMA_CLOUD_INDEX_NAME,
            project_name=LLAMA_CLOUD_PROJECT_NAME,
            organization_id=LLAMA_CLOUD_ORGANIZATION_ID,
            api_key=LLAMA_CLOUD_API_KEY,
        )
        print("✅ Successfully connected to LlamaCloud index.")
    except Exception as e:
        print(f"❌ Failed to connect to LlamaCloud index. Error: {e}")
        return

    chat_histories = load_histories()
    print(f"✅ Found {len(chat_histories)} existing session(s).")
    if chat_histories:
        print("   Existing session IDs:", ", ".join(chat_histories.keys()))

    while True:
        session_id = input("\nEnter a session ID to load or create (or 'exit' to quit): ").strip()
        if session_id.lower() == 'exit':
            print("\n👋 Goodbye!")
            break

        current_memory = chat_histories.get(session_id, ChatMemoryBuffer.from_defaults(token_limit=3900))
        chat_histories[session_id] = current_memory

        chat_engine = index.as_chat_engine(
            chat_mode="context",
            memory=current_memory,
            system_prompt=(
                "You are an expert Q&A assistant. Answer questions based on the provided context and conversation history."
            ),
        )

        print("\n" + "="*50)
        print(f"🤖 Chatting in session: '{session_id}'")
        print("   - Type your question and press Enter.")
        print("   - Type '!switch' to change to a different session.")
        print("="*50)

        while True:
            user_query = input("\n👤 You: ").strip()

            if user_query.lower() == '!switch':
                print("Switching sessions...")
                break

            response = chat_engine.stream_chat(user_query)

            print("💬 Assistant: ", end="", flush=True)
            for token in response.response_gen:
                print(token, end="", flush=True)
            print()

            save_histories(chat_histories)

# Run the application
if __name__ == "__main__":
    main()