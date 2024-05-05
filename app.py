import os
import uuid
import yaml
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import streamlit as st
from lib.vector_db.pinecone import PineconeDB
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import AzureChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.embeddings import AzureOpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from genai.prompt import CHAIN_TEMPLATE
import streamlit_authenticator as stauth
from langchain_community.chat_models import ChatOllama

from file_parser import FileParser

if os.environ.get('WITH_TRACING', None):
    os.environ['LANGCHAIN_TRACING_V2'] = 'true'
    os.environ['LANGCHAIN_ENDPOINT'] = 'https://api.smith.langchain.com'
    #os.environ['LANGCHAIN_API_KEY'] = 'ls__....'


PAGE_TITLE = 'DinimAi'
PAGE_ICON = '📚'
FAST_QUESTIONS = [
    "מי הם הצדדים במסמך שצירפתי לך?",
    "הכן לי תמצית של המסמך המצורף",
    "על איזה סכומים מדובר במסמך שצירפתי לך?",
]
LOCAL_VECTOR_STORE_DIR = Path(__file__).resolve().parent.joinpath('data', 'vector_store')
# Load environment variables
load_dotenv(find_dotenv())
st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON)

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)
name, authentication_status, username = authenticator.login(fields=['username', 'password'])


def is_hebrew(input_sentence):
    # Unicode range for Hebrew characters is U+0590 to U+05FF
    return any('\u0590' <= char <= '\u05FF' for char in input_sentence)


def is_less_than_three_words(input_sentence, min_num_words=3):
    # Split the sentence into words based on spaces
    words = input_sentence.split()
    # Check if the number of words is less than 3
    return len(words) < min_num_words


# Function to generate response using the ConversationalRetrievalChain
def generate_response(query_text):

    if is_less_than_three_words(query_text) or not is_hebrew(query_text):
        return "שאלה קצרה מדיי או לא בעברית"

    print(f"Generating response to - {query_text}")
    prompt = PromptTemplate(
        template=CHAIN_TEMPLATE,
        input_variables=["context", "question"])
    chain = ConversationalRetrievalChain.from_llm(
        llm=claude_llm,
        retriever=st.session_state.retriever,
        memory=st.session_state.chat_memory,
        combine_docs_chain_kwargs={"prompt": prompt},
        return_generated_question=True,
        return_source_documents=True)
    res = chain({"question": query_text})
    print(res)
    return res["answer"]


def process_uploaded_file(uploaded_file, session_uuid):
    if uploaded_file:
        try:
            file_identifier = uploaded_file.name
            if ("uploaded_file_identifier" not in st.session_state or
                    st.session_state.uploaded_file_identifier != file_identifier):
                print(f"Processing uploaded file {session_uuid}")
                document_text = FileParser.load(uploaded_file)
                text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
                texts = text_splitter.create_documents([document_text], metadatas=[{"source": file_identifier}])
                # add metadata to the text

                db = Chroma.from_documents(texts, embeddings,
                                           persist_directory=LOCAL_VECTOR_STORE_DIR.as_posix() + f'/{file_identifier.split(".")[0]}')
                st.sidebar.success('המסמך נטען בהצלחה!')
                st.session_state["chat_history"] = []
                st.session_state.uploaded_file_identifier = file_identifier
                return db.as_retriever(search_kwargs={"k": 2})
        except Exception as e:
            st.sidebar.error(f'Failed to process document: {e}')
            return None


def initialize_vector_db_retriever():
    vector_db = PineconeDB()
    return vector_db.db.as_retriever(search_type="similarity_score_threshold",
                                     search_kwargs={"score_threshold": .9, "k": 50})


def check_and_handle_fast_question():
    fast_question = st.session_state.get("fast_question", "")
    st.session_state["fast_question"] = ""
    return fast_question if fast_question else None


def setup():
    if "show_initial_message" not in st.session_state:
        st.session_state.show_initial_message = True

    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4()

    if "chat_memory" not in st.session_state:
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            input_key='question',
            output_key='answer',
            return_messages=True
        )
        st.session_state.chat_memory = memory

    st.sidebar.image("logo.png", width=250)
    data_source = st.sidebar.radio(
        "A",
        ('העלה מסמך משלך', 'השתמש במסד נתונים טעון'), label_visibility="hidden"
    )

    if data_source == 'העלה מסמך משלך':
        uploaded_file = st.sidebar.file_uploader("Upload your PDF file", type=FileParser.FILE_TYPES,
                                                 label_visibility="hidden")
        if uploaded_file:
            retriever = process_uploaded_file(uploaded_file, st.session_state.session_id)
            if retriever:
                update_session_state(retriever, uploaded_file)
    else:
        retriever = initialize_vector_db_retriever()
        if retriever:
            update_session_state(retriever, 'Pinecone')
        st.sidebar.success("התחברות למסד הנתונים הסתיימה בהצלחה!")

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
    if "retriever" in st.session_state and not st.session_state.uploaded_file == 'Pinecone':
        st.chat_message("assistant").markdown("קראתי את המסמך! אתה יכול לשאול אותי שאלות עכשיו")
        cols = st.columns(len(FAST_QUESTIONS))
        for idx, col in enumerate(cols):
            with col:
                if st.button(FAST_QUESTIONS[idx]):
                    st.session_state["fast_question"] = FAST_QUESTIONS[idx]


def run_app():
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
    response = "אנא הכנס מסמך כדי שאוכל לעזור לך. או השתמש במסד הנתונים שלנו המכיל מגוון רחב של מסמכיים משפטיים"  # Please upload a document so I can assist you.
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.chat_history.append({"role": "assistant", "content": response})


def display_response(prompt):
    with st.chat_message("assistant"):
        tmp = st.markdown(
            f"אני חושב וכבר מחזיר לך תשובה...")  # I'm thinking and will get back to you with an answer...
        response = generate_response(prompt)
        tmp.markdown(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})


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
        max_tokens=1024
    )


if authentication_status:

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

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # claude_llm = ChatOllama(model='llama3', temperature=0, max_tokens=4096)

    claude_llm = ChatAnthropic(
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
        temperature=0,
        model_name="claude-3-opus-20240229",
        streaming=True,
        max_tokens=4096,
        verbose=True,
    )
    embeddings, llm = initialize_embeddings_and_llm()

    setup()
    run_app()


elif not authentication_status:
    st.error('Username/password is incorrect')
elif authentication_status is None:
    st.warning('Please enter your username and password')
