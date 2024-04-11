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
        document_text = FileParser.load(source)
        return document_text

    def scrape_and_index_single(self, source):
        try:
            text = self.parse_pdf(source)
            print(f"text extracted from {source}")
            court_record_id = source.split('/')[2]

            # Create a new database connection for each thread
            db_connection = sqlite3.connect(self.db_path)
            db_connection.row_factory = sqlite3.Row
            cursor = db_connection.cursor()

            cursor.execute("SELECT is_scraped FROM court_records WHERE record_number = ?", (court_record_id,))
            is_scraped = cursor.fetchone()
            if is_scraped and is_scraped[0] == 1:
                print(f"Already scraped {source}")
                return

            cursor.execute("SELECT * FROM court_records WHERE record_number = ?", (court_record_id,))
            metadata_row = cursor.fetchone()
            metadata = dict(metadata_row) if metadata_row is not None else {}
            item = ScrapedRawMessageData(text=text, **metadata)
            print(f"Inserting {source} into vector db")
            self.vector_db.insert(item)
            cursor.execute("UPDATE court_records SET is_scraped = 1 WHERE record_number = ?", (court_record_id,))
            db_connection.commit()
            db_connection.close()
            print(f"Scraped {source}")
        except Exception as ex:
            print(f"Error scraping {source}: {ex}")

    def scrape_and_index(self):
        with ThreadPoolExecutor(max_workers=20) as executor:
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
