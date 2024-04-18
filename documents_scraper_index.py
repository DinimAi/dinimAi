import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from file_parser import FileParser
from lib.vector_db.pinecone import PineconeDB
from dotenv import find_dotenv, load_dotenv
from lib.models.scrapedRawData import ScrapedRawMessageData

load_dotenv(find_dotenv())

class PDFScraper:
    def __init__(self, downloads_path: str, db_path: str, vector_db, index_name: str):
        self.downloads_path = downloads_path
        self.db_path = db_path
        self.vector_db = vector_db
        self.index_name = index_name
        self._sources = []
        self._raw_data = []

    def get_sources(self):
        sources = []
        for root, dirs, files in os.walk(self.downloads_path):
            for file in files:
                if file.endswith(".pdf") or file.endswith(".docx"):
                    sources.append(os.path.join(root, file))
        self._sources = sources
        return True

    @staticmethod
    def parse_pdf(source):
        document_text = FileParser.load_file(source)
        return document_text

    def scrape_and_index_single(self, source):
        try:

            text = self.parse_pdf(source)
            print(f"text extracted from {source}")
            court_record_id = source.split('/')[2]
            if court_record_id == '1633-20':
                print("skipping 1633-20")
                return
            # Create a new database connection for each thread
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT is_scraped FROM court_records WHERE record_number = ?", (court_record_id,))
            is_scraped = cursor.fetchone()
            if is_scraped and is_scraped[0] == 1:
                print(f"Already scraped {source}")
                return

            cursor.execute("SELECT * FROM court_records WHERE record_number = ?", (court_record_id,))
            metadata_row = cursor.fetchone()
            metadata = dict(metadata_row) if metadata_row is not None else {}
            cursor.execute("SELECT name, full_path FROM documents WHERE court_record_id = ?", (court_record_id,))
            document_info = cursor.fetchone()
            if document_info:
                metadata['name'] = document_info['name']
                metadata['source'] = document_info['full_path']
            if 'is_scraped' in metadata:
                del metadata['is_scraped']
            item = ScrapedRawMessageData(text=text, **metadata)
            print(f"Inserting {source} into vector db")
            self.vector_db.insert(item)
            print(f"Scraped {source}")
        #     update sqlite db
            cursor.execute("UPDATE court_records SET is_scraped = 1 WHERE record_number = ?", (court_record_id,))
            conn.commit()
            conn.close()
        except Exception as ex:
            print(f"Error scraping {source}: {ex}, source: {source}")

    def scrape_and_index(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.map(self.scrape_and_index_single, self._sources)

    def run(self):
        self.get_sources()
        self.scrape_and_index()


if __name__ == "__main__":
    db_path = "./psikot_docs.db"
    vector_db = PineconeDB()
    scraper = PDFScraper(downloads_path="./downloads",
                         db_path=db_path,
                         vector_db=vector_db,
                         index_name="dinim-ai-index")
    scraper.run()
