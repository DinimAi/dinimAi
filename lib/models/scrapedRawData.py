import uuid
from datetime import datetime

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document


class ScrapedRawMessageData(object):

    def __init__(self, text, **kwargs):
        self.text = text
        self.doc_id = str(uuid.uuid4())
        self.index_time = datetime.now()
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _split_text_to_chunks(self, chunk_size=1000, chunk_overlap=100):
        doc = Document(page_content=self.text, metadata={"source": "gov"})
        return RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap).split_documents([doc])

    def create_text_and_metadata_lists(self) -> list:
        chunks = self._split_text_to_chunks()  # Split text into chunks
        base_metadata = {k: v for k, v in self.__dict__.items() if k != 'text'}  # Base metadata

        for i, chunk in enumerate(chunks):
            chunk_metadata = base_metadata.copy()
            chunk_metadata['chunk_id'] = i
            chunk.metadata = chunk_metadata
            chunk.page_content = str(chunk_metadata) + chunk.page_content

        return chunks  # Return the list of chunks, each with its own metadata
