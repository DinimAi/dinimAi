import os
import uuid

from dotenv import load_dotenv, find_dotenv
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import AzureChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.embeddings import AzureOpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from genai.prompt import CHAIN_TEMPLATE

# Constants for Streamlit page configuration
PAGE_TITLE = 'DinimAi'
PAGE_ICON = '📚'
PDF_FILE_TYPE = 'pdf'
FAST_QUESTIONS = [
    "מי הם הצדדים במסמך שצירפתי לך?",
    "הכן לי תמצית של המסמך המצורף",
    "מי התובע ומי הנתבע במסמך שצירפתי לך?"
]
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Load environment variables
load_dotenv(find_dotenv())
st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON)
st.markdown("""
    <style>
    /* Custom CSS for RTL alignment */
    .stTextInput>div>div>input, .st-bf, .st-bj, .st-bu, .stButton>button, .stFileUploader, 
    .stTextArea>div>div>textarea, .stMarkdown, .streamlit-alert {
        direction: rtl;
    }
    .css-hi6a2p, h1 {
        text-align: center;
        direction: rtl;
    }
    label[data-baseweb="file-uploader"], .st-sl, .st-cb, .st-dd {
        justify-content: flex-end;
    }
    .stSelectbox>div>div, .stMultiSelect>div>div>div {
        direction: rtl;
    }
    .stButton>button {
        justify-content: right;
    }
    </style>
""", unsafe_allow_html=True)


# Initialize embeddings and LLM with Azure and OpenAI settings
def initialize_embeddings_and_llm():
    return AzureOpenAIEmbeddings(
        azure_deployment=os.getenv('AZURE_EMBEDDING_DEPLOYMENT'),
        openai_api_version=os.getenv('OPEN_AI_API_VER'),
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        azure_endpoint=os.getenv('AZURE_ENDPOINT')
    ), AzureChatOpenAI(
        deployment_name=os.getenv('AZURE_MODEL_DEPLOYMENT'),
        openai_api_version=os.getenv('OPEN_AI_API_VER'),
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        azure_endpoint=os.getenv('AZURE_ENDPOINT'),
        max_tokens=4096
    )


embeddings, llm = initialize_embeddings_and_llm()

claude_llm = ChatAnthropic(
    anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
    temperature=0,
    model_name="claude-3-opus-20240229",
    streaming=True
)

memory = ConversationBufferMemory(
    memory_key="chat_history",
    input_key='question',
    output_key='answer',
    return_messages=True
)


# Function to parse PDF content
def parse_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ''.join([page.extract_text() + '\n' for page in reader.pages])
    return text


# Function to generate response using the ConversationalRetrievalChain
def generate_response(query_text, retriever):
    print(f"Generating response to - {query_text}")
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        memory=memory,
        return_generated_question=True,
        retriever=retriever,
        condense_question_prompt=PromptTemplate.from_template(CHAIN_TEMPLATE),
    )
    return chain({"question": query_text})["answer"]


# Function to process uploaded PDF file
@st.cache_resource
def process_uploaded_file(uploaded_file, session_uuid):
    if uploaded_file:
        print(f"Processing uploaded file {session_uuid}")
        document_text = parse_pdf(uploaded_file)
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        texts = text_splitter.create_documents([document_text])

        db = Chroma.from_documents(texts, embeddings)
        st.sidebar.success('המסמך נטען בהצלחה!')
        st.session_state["chat_history"] = []
        return db.as_retriever()

    return None


# Function to handle fast questions from session state
def check_and_handle_fast_question():
    fast_question = st.session_state.get("fast_question", "")
    st.session_state["fast_question"] = ""
    return fast_question if fast_question else None


# Main UI setup
def setup_ui():
    if "show_initial_message" not in st.session_state:
        st.session_state.show_initial_message = True

    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4()

    st.sidebar.image("logo.png", width=250)
    uploaded_file = st.sidebar.file_uploader("Upload your PDF File", type=PDF_FILE_TYPE, label_visibility="hidden")
    if uploaded_file:
        retriever = process_uploaded_file(uploaded_file, st.session_state.session_id)
        if retriever:
            update_session_state(retriever, uploaded_file)
        else:
            st.sidebar.error('Failed to process document.')

    if st.session_state.show_initial_message:
        st.chat_message("assistant").markdown(
            "שלום שמי דין נוצרתי כדי לקרוא מסמכים ארוכים ללמוד אותם ולענות לכם על שאלות עליהם. "
            "\n"
            "תעלו אליי מסמכים כדי שאלמד אותם ואוכל לעזור לכם בעבודה היומיומית.")


def update_session_state(retriever, uploaded_file):
    st.session_state.update({
        "retriever": retriever,
        "uploaded_file": uploaded_file,
        "llm_ready": True,
        "show_initial_message": False
    })


def display_fast_questions():
    st.chat_message("assistant").markdown("קראתי את המסמך! אתה יכול לשאול אותי שאלות עכשיו")


def chat_history_display():
    for item in st.session_state.chat_history:
        role, content = item["role"], item["content"]
        if role == "user":
            st.chat_message("user").markdown(content)
        elif role == "assistant":
            st.chat_message("assistant").markdown(content)

def handle_fast_question():
    if "retriever" in st.session_state:
        cols = st.columns(len(FAST_QUESTIONS))
        for idx, col in enumerate(cols):
            with col:
                if st.button(FAST_QUESTIONS[idx]):
                    st.session_state["fast_question"] = FAST_QUESTIONS[idx]

def main():
    # Check if a retriever is created and if the user hasn't submitted a prompt
    if "retriever" in st.session_state and not "user_submitted_prompt" in st.session_state:
        st.session_state.show_initial_message = False
    handle_fast_question()
    prompt = st.chat_input("הכנס שאילתה על המסמך")  # Insert a query about the document
    if prompt:
        handle_chat(prompt)
    fast_question = check_and_handle_fast_question()
    if fast_question:
        handle_chat(fast_question)

def handle_chat(prompt):
    chat_history_display()
    st.chat_message("user").markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    if not st.session_state.get('llm_ready', False):
        display_initial_message()
    else:
        display_response(prompt)
    st.session_state.user_submitted_prompt = True

def display_initial_message():
    response = "אנא הכנס מסמך כדי שאוכל לעזור לך."  # Please upload a document so I can assist you.
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.chat_history.append({"role": "assistant", "content": response})


def display_response(prompt):
    with st.chat_message("assistant"):
        tmp = st.markdown(f"אני חושב וכבר מחזיר לך תשובה...")  # I'm thinking and will get back to you with an answer...
        response = generate_response(prompt, st.session_state.retriever)
        tmp.markdown(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    setup_ui()
    main()
