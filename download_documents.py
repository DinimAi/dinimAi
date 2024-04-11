import requests
import os

from sqlite_db import SqliteDB

def download_file(url, local_filename):
    """
    Downloads a file from a given URL and saves it locally.

    Parameters:
    - url (str): The URL of the file to download.
    - local_filename (str): The local path where the file should be saved.
    """
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Successfully downloaded {local_filename}.")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")


def fetch_and_download_documents(db_path='spokmanship_court.db'):
    """
    Connects to the SQLite database, fetches all rows from the 'documents' table,
    and downloads the corresponding files.

    Parameters:
    - db_path (str): The path to the SQLite database file.
    """
    db = SqliteDB(db_path)

    # Fetch all rows from the documents table
    documents = db.fetch_documents(from_id=5296)

    # Ensure a directory exists for downloads
    download_dir = "downloads"

    if documents:
        print(f"Starting the download of {len(documents)} documents...")
        for idx, (doc_id, name, full_path, court_record_id) in enumerate(documents, start=1):
            # Constructing a safe file name
            if '8910' in court_record_id:
                pass
            safe_name = name.replace('/', '_').replace('\\', '_').replace(' ', '_')
            ftype = full_path.split('.')[-1]
            if ftype not in ['docx', 'doc', 'txt', 'pdf']:
                print(f"Unknown file type: {ftype}")
                continue
            court_record_id = court_record_id.replace('/', '-')
            filename = f"{safe_name}__{court_record_id}.{ftype}"
            local_dir = os.path.join(download_dir, court_record_id)
            os.makedirs(local_dir, exist_ok=True)
            local_filename = os.path.join(local_dir, filename)

            download_file(full_path, local_filename)
            print(f"{doc_id=}: Downloaded {idx}/{len(documents)}")
            if local_filename:
                # Assume you have doc_id available; if not, you'll need to retrieve or adjust your logic
                db.update_document_local_path(doc_id, local_filename)
    else:
        print("No documents found to download.")


if __name__ == "__main__":
    fetch_and_download_documents()
