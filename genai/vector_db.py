import logging
import os
import pinecone
from langchain_community.vectorstores import Pinecone
from langchain_community.embeddings import AzureOpenAIEmbeddings


class PineconeDB:
    def __init__(self, index_name):
        self._index_name = index_name
        self.db = self.connect()

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
            index = pc.Index(name=self._index_name,
                             host=os.getenv("PINECONE_HOST_NAME"))
            db = Pinecone(embedding=embeddings, index=index, text_key="articles")
            logging.info("Successfully connected to Pinecone")
            return db
        except Exception as e:
            logging.error("Error connecting to database: %s", e)

