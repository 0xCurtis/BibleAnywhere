import os
import sqlite3
import csv

# Directory containing the CSV files
DATA_DIR = "data"
DATABASE_FILE = "bible.db"

# SQLite database schema
CREATE_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS verses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    verse_id INTEGER NOT NULL,
    book_name TEXT NOT NULL,
    book_number INTEGER NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    text TEXT NOT NULL,
    UNIQUE(language, verse_id) -- Enforce uniqueness for verse_id within a language
);
"""

def merge_csv_to_db():
    # Connect to the SQLite database (or create it)
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Create the table
    cursor.execute(CREATE_TABLE_QUERY)

    # Iterate over all CSV files in the data directory
    for file_name in os.listdir(DATA_DIR):
        if file_name.endswith(".csv"):
            lang = file_name.replace("bible", "").replace(".csv", "")  # Extract language code
            file_path = os.path.join(DATA_DIR, file_name)
            print(f"Processing {file_name} for language {lang}...")

            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = [
                    (
                        lang,
                        row["Verse ID"],
                        row["Book Name"],
                        row["Book Number"],
                        row["Chapter"],
                        row["Verse"],
                        row["Text"],
                    )
                    for row in reader
                ]

                # Insert data into the database
                cursor.executemany("""
                INSERT OR IGNORE INTO verses (
                    language, verse_id, book_name, book_number, chapter, verse, text
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """, rows)

    # Commit changes and close the connection
    conn.commit()
    conn.close()
    print(f"All data has been merged into {DATABASE_FILE}.")

if __name__ == "__main__":
    merge_csv_to_db()
