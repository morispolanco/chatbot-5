import streamlit as st
import requests
import json

# Show title and description
st.title("🛠️ Business Research Agent")
st.write(
    "This Business Research Agent specializes in investigating the conditions and elements you need to put your business idea into practice. "
    "It combines internet search using Serper's API with language model capabilities from Together's LLM API."
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

# Step 1: Ask for the business idea
if "business_idea" not in st.session_state:
    st.session_state.business_idea = st.text_input("Please describe your business idea to start the research:")
    if st.session_state.business_idea:
        st.session_state.messages.append({"role": "user", "content": st.session_state.business_idea})
        st.experimental_rerun()

# Step 2: Proceed with the research based on the business idea
else:
    business_idea = st.session_state.business_idea

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("What specific aspect of your business idea would you like to research?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            # Perform Google search
            try:
                search_results = google_search(f"{business_idea} {prompt}")
            except Exception as e:
                st.error(f"Error during Google search: {str(e)}")
                search_results = {"organic": []}

            # Prepare context with search results
            context = f"Search results for '{business_idea} {prompt}':\n"
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
        st.session_state.business_idea = ""
        st.experimental_rerun()
