import streamlit as st
import requests
import json

# Show title and description
st.title("🎓 Scholarship Research Agent")
st.write(
    "This Research Agent specializes in finding study scholarships based on your interests and background. "
    "It uses Together's LLM API for processing and Serper's API for Google search to provide tailored scholarship recommendations."
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
        "max_tokens": 1024,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "repetition_penalty": 1,
        "stop": ["<|eot_id|>", "<|eom_id|>"],
        "stream": True
    }
    return requests.post(together_url, headers=together_headers, json=payload, stream=True)

# Create a session state variable to store the chat messages and user info
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_info" not in st.session_state:
    st.session_state.user_info = {}

# Function to ask user for scholarship preferences
def ask_scholarship_preferences():
    st.subheader("Scholarship Preferences")
    field = st.text_input("What field of study are you interested in?", key="field")
    location = st.text_input("In which country or region do you want to study?", key="location")
    level = st.selectbox("What academic level are you applying for?", 
                         ["Undergraduate", "Master's", "PhD", "Postdoctoral"], key="level")
    nationality = st.text_input("What is your nationality?", key="nationality")
    nationality_specific = st.checkbox("Are you only interested in scholarships specific to your nationality?", key="nationality_specific")
    
    if st.button("Search for Scholarships"):
        st.session_state.user_info = {
            "field": field,
            "location": location,
            "level": level,
            "nationality": nationality,
            "nationality_specific": nationality_specific
        }
        return True
    return False

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Main interaction loop
if not st.session_state.user_info:
    if ask_scholarship_preferences():
        st.experimental_rerun()
else:
    user_info = st.session_state.user_info
    search_query = f"scholarships for {user_info['level']} in {user_info['field']} in {user_info['location']}"
    if user_info['nationality_specific']:
        search_query += f" for {user_info['nationality']} students"

    try:
        search_results = google_search(search_query)
    except Exception as e:
        st.error(f"Error during Google search: {str(e)}")
        search_results = {"organic": []}

    context = "Search results for scholarships:\n"
    for i, result in enumerate(search_results.get('organic', [])[:5], 1):
        context += f"{i}. {result.get('title', 'No title')}: {result.get('snippet', 'No snippet')} [Link: {result.get('link', 'No link')}]\n"

    prompt = f"""
    Based on the following user preferences and search results, recommend suitable scholarships:
    
    User Preferences:
    - Field of study: {user_info['field']}
    - Desired study location: {user_info['location']}
    - Academic level: {user_info['level']}
    - Nationality: {user_info['nationality']}
    - Only interested in nationality-specific scholarships: {"Yes" if user_info['nationality_specific'] else "No"}

    {context}

    Please provide a detailed response with:
    1. The most relevant scholarship opportunities.
    2. Direct links to the institutions offering these scholarships.
    3. Brief explanations of why you're recommending each institution or scholarship.
    4. Any additional advice for the user based on their preferences.
    """

    messages = [
        {"role": "system", "content": "You are a helpful scholarship research assistant. Provide detailed and accurate scholarship information based on the user's preferences and the search results."},
        {"role": "user", "content": prompt}
    ]

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

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
                        continue

            if not full_response:
                full_response = "I apologize, but I couldn't generate a response. Please try again."

        except Exception as e:
            full_response = f"An error occurred while processing your request: {str(e)}"

        message_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Add a button to start a new search
if st.button("Start New Scholarship Search"):
    st.session_state.messages = []
    st.session_state.user_info = {}
    st.experimental_rerun()
