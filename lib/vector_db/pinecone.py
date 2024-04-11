import logging
import os
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import Pinecone
import pinecone
from lib.vector_db import Database
from lib.models.scrapedRawData import ScrapedRawMessageData


class PineconeDB(Database):
    index_name: str

    def __init__(self, index_name=None):
        super().__init__()
        self._index_name = index_name

    @property
    def index_name(self):
        if not hasattr(self, '_index_name') or self._index_name is None:
            self._index_name = os.getenv("PINECONE_INDEX_NAME", "embedding2")
        return self._index_name

    def connect(self):
        try:
            logging.info("Connecting to Pinecone")
            embeddings = AzureOpenAIEmbeddings(
                azure_deployment=os.environ.get('AZURE_EMBEDDING_DEPLOYMENT'),
                openai_api_version=os.environ.get('OPEN_AI_API_VER'),
                openai_api_key=os.environ.get('OPENAI_API_KEY'),
                azure_endpoint=os.environ.get('AZURE_ENDPOINT')
            )
            logging.info("Connecting to Pinecone")
            pc = pinecone.Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            index = pc.Index(name=self.index_name,
                             host=os.getenv("PINECONE_HOST_NAME",
                                            "https://dinim-ai-index-1ynzr5q.svc.gcp-starter.pinecone.io"))
            db = Pinecone(embedding=embeddings, index=index, text_key="articles")
            logging.info("Successfully connected to Pinecone")
            return db
        except Exception as e:
            logging.error("Error connecting to database: %s", e)

    def insert(self, item: ScrapedRawMessageData):
        all_texts, all_metadata = item.create_text_and_metadata_lists()
        try:
            self.db.add_texts(all_texts, all_metadata)
        except Exception as e:
            logging.error("did not succeed to index due to %s", e)

    def query(self, query):
        logging.info("will require impl in the future")
