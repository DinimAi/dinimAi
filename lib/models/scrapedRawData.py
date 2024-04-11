from langchain.text_splitter import RecursiveCharacterTextSplitter


class ScrapedRawMessageData(object):

    def __init__(self, text, **kwargs):
        self.text = text

        for key, value in kwargs.items():
            setattr(self, key, value)

    def _split_text_to_chunks(self, chunk_size=1000, chunk_overlap=100):
        return RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap).split_text(self.text)

    def create_text_and_metadata_lists(self) -> tuple[list[str], list[dict]]:
        chunks = self._split_text_to_chunks()
        all_texts = [f"metadata: {self.__dict__.items()} text: {chunk}" for chunk in chunks if chunk.strip()]
        all_metadata = [{k: v for k, v in self.__dict__.items() if k != 'text'} for _ in all_texts]

        return all_texts, all_metadata
