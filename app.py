import os
import streamlit as st
from dotenv import load_dotenv, find_dotenv
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory
from PyPDF2 import PdfReader
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import AzureChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.embeddings import AzureOpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain

from genai.prompt import CHAIN_TEMPLATE

# Load environment variables
load_dotenv(find_dotenv())
st.set_page_config(page_title='DinimAi', page_icon='📚')
# Initialize embeddings and LLM with Azure and OpenAI settings
embeddings = AzureOpenAIEmbeddings(
    azure_deployment=os.environ.get('AZURE_EMBEDDING_DEPLOYMENT'),
    openai_api_version=os.environ.get('OPEN_AI_API_VER'),
    openai_api_key=os.environ.get('OPENAI_API_KEY'),
    azure_endpoint=os.environ.get('AZURE_ENDPOINT')
)
llm = AzureChatOpenAI(
    deployment_name=os.environ.get('AZURE_MODEL_DEPLOYMENT'),
    openai_api_version=os.environ.get('OPEN_AI_API_VER'),
    openai_api_key=os.environ.get('OPENAI_API_KEY'),
    azure_endpoint=os.environ.get('AZURE_ENDPOINT'),
    max_tokens=4096
)

claude_llm = ChatAnthropic(
    anthropic_api_key=os.environ.get('ANTHROPIC_API_KEY'),
    temperature=0, model_name="claude-3-opus-20240229",
    streaming=True
)

memory = ConversationBufferMemory(memory_key="chat_history", input_key='question', output_key='answer',
                                  return_messages=True)

fast_question_buttons = ["אני הולך לייצג את הנתבע במסמך תכין אותי לדיון איתו", "הכן לי תמצית של המסמך המצורף", "מי התובע ומי הנתבע?"]


# Function to parse PDF content
def parse_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ''
    for page in reader.pages:
        text += page.extract_text() + '\n'
    return text  # Returns the concatenated text of all pages

def generate_response(query_text, retriever):
    print(f"Generating response to - {query_text}")
    chain = ConversationalRetrievalChain.from_llm(
        llm=claude_llm,
        memory=memory,
        return_generated_question=True,
        retriever=retriever,
        condense_question_prompt=PromptTemplate.from_template(CHAIN_TEMPLATE),
    )
    chain_response = chain({"question": query_text})

    return chain_response["answer"]


if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
for item in st.session_state.chat_history:
    role, content = item["role"], item["content"]
    if role == "user":
        st.chat_message("user").markdown(content)
    elif role == "assistant":
        st.chat_message("assistant").markdown(content)


@st.cache_resource
def process_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        print("Processing uploaded file")
        document_text = parse_pdf(uploaded_file)
        documents = [document_text]
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        texts = text_splitter.create_documents(documents)

        db = Chroma.from_documents(texts, embeddings)
        st.session_state["chat_history"] = []
        st.sidebar.success('המסמך נטען בהצלחה!')
        st.chat_message("assistant").markdown("קראתי את המסמך! אתה יכול לשאול אותי שאלות עכשיו")
        return db.as_retriever()
    return None

def check_and_handle_fast_question():
    # Check if there's a fast question in the session state
    if "fast_question" in st.session_state and st.session_state["fast_question"]:
        fast_question = st.session_state["fast_question"]
        st.session_state["fast_question"] = ""
        return fast_question
    return None

prompt = st.chat_input("הכנס שאילתה על המסמך")


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
st.sidebar.image("logo.png", width=250)
uploaded_file = st.sidebar.file_uploader("Upload your PDF File", type="pdf", label_visibility="hidden")
# Sidebar for file upload
if uploaded_file is not None:
    retriever = process_uploaded_file(uploaded_file)
    if retriever:
        st.session_state.retriever = retriever
        st.session_state.uploaded_file = uploaded_file
        st.session_state.llm_ready = True
        st.session_state.show_initial_message = False
        cols = st.columns(len(fast_question_buttons))
        for idx, col in enumerate(cols):
            fast_question = fast_question_buttons[idx]
            with col:
                if st.button(fast_question):
                    st.session_state["fast_question"] = fast_question
                    # st.experimental_rerun()
    else:
        st.sidebar.error('Failed to process document.')

if "show_initial_message" not in st.session_state:
    st.session_state.show_initial_message = True

# Display initial chat message if session state variable is True
if st.session_state.show_initial_message:
    st.chat_message("assistant").markdown(
        "שלום שמי דין נוצרתי כדי לקרוא מסמכים ארוכים ללמוד אותם ולענות לכם על שאלות עליהם. "
        "\n"
        "תעלו אליי מסמכים כדי שאלמד אותם ואוכל לעזור לכם בעבודה היומיומית.")

# Chat interface
if prompt is not None:
    st.chat_message("user").markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    if not st.session_state.get('llm_ready', False):
        response = "אנא הכנס מסמך כדי שאוכל לעזור לך."
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})
    else:
        with st.chat_message("assistant"):
            tmp = st.markdown(f"אני חושב וכבר מחזיר לך תשובה...")
            response = generate_response(prompt, st.session_state.retriever)
            tmp.markdown(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})

# Attempt to handle a fast question if one has been set
fast_question = check_and_handle_fast_question()
if fast_question:
    prompt = fast_question
    # You can also programmatically display the fast question in the chat interface here
    st.chat_message("user").markdown(prompt)
    tmp = st.markdown(f"אני חושב וכבר מחזיר לך תשובה...")
    response = generate_response(prompt, st.session_state.retriever)
    tmp.markdown(response)
    st.session_state.chat_history.append({"role": "assistant", "content": response})

