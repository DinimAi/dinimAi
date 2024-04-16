from PyPDF2 import PdfReader
from docx import Document
import io


class BaseParser:
    def parse(self, uploaded_file):
        pass


class PDFParser(BaseParser):
    def parse(self, uploaded_file):
        reader = PdfReader(uploaded_file)
        text = ''.join([page.extract_text() + '\n' for page in reader.pages])
        return text


class DocxParser(BaseParser):
    """Read the content of a docx file and return it as a string."""
    def parse(self, uploaded_file):
        doc = Document(io.BytesIO(uploaded_file.read()))
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)


class FileParser:
    PARSERS = {
        'pdf': PDFParser,
        'docx': DocxParser
    }

    FILE_TYPES = list(PARSERS.keys())

    @classmethod
    def load_file(cls, uploaded_file):
        file_type = uploaded_file.split('/')[-1].split('.')[-1]
        if file_type not in cls.PARSERS:
            raise Exception(f"File type {file_type} not supported")

        with open(uploaded_file, 'rb') as uploaded_file:
            return cls.PARSERS[file_type]().parse(uploaded_file)

    @classmethod
    def load(cls, uploaded_file):
        file_type = uploaded_file.name.split('.')[-1]
        if file_type not in cls.PARSERS:
            raise Exception(f"File type {file_type} not supported")
        return cls.PARSERS[file_type]().parse(uploaded_file)


