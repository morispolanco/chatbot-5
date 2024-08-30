import streamlit as st
import requests
import json

# Show title and description
st.title("🔍 Research Agent")
st.write(
    "This Research Agent uses Together's LLM API for chat completions and Serper's API for Google search. "
    "The agent can perform research tasks by combining internet search with language model capabilities."
)

# Get API keys from Streamlit secrets
together_api_key = st.secrets["TOGETHER_API_KEY"]
serper_api_key = st.secrets["SERPER_API_KEY"]

# Set up the API endpoints and headers
together_url = "https://api.together.xyz/v1/chat/completions"
serper_url = "https://google.serper.dev/search"

together_headers = {
    "Authorization": f"Bearer {together_api_key}",
    "Content-Type": "application/json"
}

serper_headers = {
    "X-API-KEY": serper_api_key,
    "Content-Type": "application/json"
}

# Function to perform Google search using Serper API
def google_search(query):
    payload = json.dumps({"q": query})
    response = requests.post(serper_url, headers=serper_headers, data=payload)
    return response.json()

# Function to get LLM response using Together API
def get_llm_response(messages):
    payload = {
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "repetition_penalty": 1,
        "stop": ["<|eot_id|>", "<|eom_id|>"],
        "stream": True
    }
    return requests.post(together_url, headers=together_headers, json=payload, stream=True)

# Create a session state variable to store the chat messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to research?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        # Perform Google search
        try:
            search_results = google_search(prompt)
        except Exception as e:
            st.error(f"Error during Google search: {str(e)}")
            search_results = {"organic": []}

        # Prepare context with search results
        context = f"Search results for '{prompt}':\n"
        for i, result in enumerate(search_results.get('organic', [])[:3], 1):
            context += f"{i}. {result.get('title', 'No title')}: {result.get('snippet', 'No snippet')}\n"

        # Prepare messages for LLM
        messages = [
            {"role": "system", "content": "You are a helpful research assistant. Use the provided search results to answer the user's question."},
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {prompt}"}
        ]

        # Get LLM response
        try:
            response = get_llm_response(messages)

            for line in response.iter_lines():
                if line:
                    try:
                        data = line.decode('utf-8').split('data: ', 1)
                        if len(data) > 1:
                            chunk = json.loads(data[1])
                            if chunk['choices'][0]['finish_reason'] is None:
                                content = chunk['choices'][0]['delta'].get('content', '')
                                full_response += content
                                message_placeholder.markdown(full_response + "▌")
                    except json.JSONDecodeError:
                        continue  # Skip this line if it's not valid JSON

            if not full_response:
                full_response = "I apologize, but I couldn't generate a response. Please try again."

        except Exception as e:
            full_response = f"An error occurred while processing your request: {str(e)}"

        message_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Add a button to clear the chat history
if st.button("Clear chat history"):
    st.session_state.messages = []
    st.experimental_rerun()
