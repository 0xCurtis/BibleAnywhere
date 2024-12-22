from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import random
from contextlib import contextmanager
from sqlite3.dbapi2 import Connection
import threading
from functools import lru_cache
import json
import os
import re

app = Flask(__name__)

# Load color theme
def load_theme():
    theme_path = os.path.join(app.static_folder, 'colors.json')
    try:
        with open(theme_path, 'r') as f:
            return json.load(f)['theme']
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        # Return default theme if file is not found or invalid
        return {
            "primary": {"main": "#4299e1", "light": "#63b3ed", "dark": "#3182ce", "text": "#ffffff"},
            "secondary": {"main": "#2d3748", "light": "#4a5568", "dark": "#1a202c", "text": "#ffffff"},
            "background": {"main": "#f7fafc", "paper": "#ffffff", "sidebar": "#ffffff", "hover": "#edf2f7"},
            "text": {"primary": "#2d3748", "secondary": "#4a5568", "disabled": "#a0aec0"},
            "border": {"main": "#e2e8f0", "dark": "#cbd5e0"},
            "shadow": {"small": "0 2px 4px rgba(0,0,0,0.05)", "medium": "0 4px 6px rgba(0,0,0,0.1)", "large": "0 8px 16px rgba(0,0,0,0.1)"}
        }

# Database configuration
DATABASE_FILE = "bible.db"
SUPPORTED_LANGUAGES = ["en", "fr", "ru", "pt", "pl"]
VERSE_WINDOW_SIZE = 20  # Number of verses to fetch before and after
LOAD_THRESHOLD = 5  # Load more verses when within this many verses of the edge

# Bible structure
OLD_TESTAMENT = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles",
    "Ezra", "Nehemiah", "Esther", "Job", "Psalms",
    "Proverbs", "Ecclesiastes", "Song of Solomon",
    "Isaiah", "Jeremiah", "Lamentations", "Ezekiel",
    "Daniel", "Hosea", "Joel", "Amos", "Obadiah",
    "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi"
]

NEW_TESTAMENT = [
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
    "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon",
    "Hebrews", "James", "1 Peter", "2 Peter",
    "1 John", "2 John", "3 John", "Jude", "Revelation"
]

# Thread-local storage for database connections and verse cache
db_local = threading.local()
verse_cache = {}  # Format: {lang: {verse_id: verse_data}}

def get_db() -> Connection:
    if not hasattr(db_local, "connection"):
        connection = sqlite3.connect(DATABASE_FILE)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA journal_mode=WAL')
        with connection:
            connection.execute('''
                CREATE INDEX IF NOT EXISTS idx_verses_lang_id 
                ON verses(language, verse_id)
            ''')
            connection.execute('''
                CREATE INDEX IF NOT EXISTS idx_verses_book 
                ON verses(language, book_name, chapter, verse)
            ''')
        db_local.connection = connection
    return db_local.connection

@contextmanager
def get_db_cursor():
    db = get_db()
    cursor = db.cursor()
    try:
        yield cursor
    finally:
        cursor.close()

def fetch_verse_range(start_id, end_id, lang):
    """Fetch a range of verses and process them"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT v.*,
                LEAD(verse_id, 1) OVER (ORDER BY verse_id) as next_id,
                LAG(verse_id, 1) OVER (ORDER BY verse_id) as prev_id
            FROM verses v
            WHERE language = ?
                AND verse_id >= ?
                AND verse_id <= ?
            ORDER BY verse_id
        """, (lang, start_id, end_id))
        
        verses = cursor.fetchall()
        return process_verses(verses)

def process_verses(verses):
    """Process verses into a dictionary with next/previous links"""
    verse_dict = {}
    for verse in verses:
        verse_data = dict(verse)
        verse_id = str(verse_data['verse_id'])
        verse_data['next'] = verse_data.pop('next_id')
        verse_data['previous'] = verse_data.pop('prev_id')
        verse_dict[verse_id] = verse_data
    return verse_dict

def ensure_verse_cached(verse_id, lang):
    """Ensure a verse and its surrounding verses are cached"""
    verse_id = int(verse_id)
    
    # Initialize cache for language if needed
    if lang not in verse_cache:
        verse_cache[lang] = {}
    
    # If verse is not in cache, fetch a window of verses
    if str(verse_id) not in verse_cache[lang]:
        start_id = max(0, verse_id - VERSE_WINDOW_SIZE)
        end_id = verse_id + VERSE_WINDOW_SIZE
        new_verses = fetch_verse_range(start_id, end_id, lang)
        verse_cache[lang].update(new_verses)
    
    # Check if we need to load more verses (near the edge of our cache)
    verse = verse_cache[lang].get(str(verse_id))
    if verse:
        if verse['next'] and str(verse['next']) not in verse_cache[lang]:
            if int(verse_id) % VERSE_WINDOW_SIZE >= (VERSE_WINDOW_SIZE - LOAD_THRESHOLD):
                # Load next batch
                start_id = verse_id + 1
                end_id = start_id + VERSE_WINDOW_SIZE
                new_verses = fetch_verse_range(start_id, end_id, lang)
                verse_cache[lang].update(new_verses)
        
        if verse['previous'] and str(verse['previous']) not in verse_cache[lang]:
            if int(verse_id) % VERSE_WINDOW_SIZE <= LOAD_THRESHOLD:
                # Load previous batch
                end_id = verse_id - 1
                start_id = max(0, end_id - VERSE_WINDOW_SIZE)
                new_verses = fetch_verse_range(start_id, end_id, lang)
                verse_cache[lang].update(new_verses)

def get_verse_by_id(verse_id, lang):
    """Get a verse by ID, ensuring it's cached"""
    ensure_verse_cached(verse_id, lang)
    return verse_cache.get(lang, {}).get(str(verse_id))

def get_book_info(lang):
    """Get information about available chapters for each book"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT book_name, 
                   MIN(chapter) as min_chapter,
                   MAX(chapter) as max_chapter,
                   MIN(verse_id) as first_verse_id
            FROM verses 
            WHERE language = ?
            GROUP BY book_name
            ORDER BY MIN(verse_id)
        """, (lang,))
        books = {}
        for row in cursor.fetchall():
            books[row['book_name']] = {
                'min_chapter': row['min_chapter'],
                'max_chapter': row['max_chapter'],
                'first_verse_id': row['first_verse_id']
            }
        return books

def get_chapter_info(book_name, chapter, lang):
    """Get information about verses in a specific chapter"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT MIN(verse) as min_verse,
                   MAX(verse) as max_verse,
                   MIN(verse_id) as first_verse_id
            FROM verses 
            WHERE language = ? 
            AND book_name = ? 
            AND chapter = ?
        """, (lang, book_name, chapter))
        return dict(cursor.fetchone())

def get_first_verse_id_of_chapter(book_name, chapter, lang):
    """Get the first verse ID of a specific chapter"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT MIN(verse_id) as first_verse_id
            FROM verses 
            WHERE language = ? 
            AND book_name = ? 
            AND chapter = ?
        """, (lang, book_name, chapter))
        result = cursor.fetchone()
        return result['first_verse_id'] if result else None

def get_chapter_verses(book_name, chapter, lang):
    """Get all verses in a chapter"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT verse_id, verse, text
            FROM verses 
            WHERE language = ? 
            AND book_name = ? 
            AND chapter = ?
            ORDER BY verse
        """, (lang, book_name, chapter))
        return [dict(row) for row in cursor.fetchall()]

def highlight_text(text, keyword):
    """Add highlight markers around matching text"""
    pattern = re.compile(f'({re.escape(keyword)})', re.IGNORECASE)
    return pattern.sub(r'<mark class="highlight">\1</mark>', text)

def search_verses(keyword, lang):
    """Search for verses containing the keyword"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT verse_id, book_name, chapter, verse, text
            FROM verses 
            WHERE language = ? 
            AND text LIKE ?
            ORDER BY verse_id
            LIMIT 100
        """, (lang, f"%{keyword}%"))
        results = [dict(row) for row in cursor.fetchall()]
        
        # Add highlighted text to results
        for result in results:
            result['highlighted_text'] = highlight_text(result['text'], keyword)
        
        return results

@app.route('/verse/random', methods=['GET'])
def get_random_verse():
    lang = request.args.get('lang', 'en')
    
    if lang not in SUPPORTED_LANGUAGES:
        return jsonify({'error': f'Language {lang} not found'}), 404
    
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT verse_id FROM verses 
            WHERE language = ? 
            ORDER BY RANDOM() 
            LIMIT 1
        """, (lang,))
        
        result = cursor.fetchone()
        if result:
            verse = get_verse_by_id(result['verse_id'], lang)
            return jsonify(verse)
    
    return jsonify({'error': 'Verse not found'}), 404

@app.route('/verse/id', methods=['GET'])
def get_verse_by_id_route():
    lang = request.args.get('lang', 'en')
    verse_id = request.args.get('verse_id')
    
    if not verse_id:
        return jsonify({'error': 'Verse ID is required'}), 400
        
    if lang not in SUPPORTED_LANGUAGES:
        return jsonify({'error': f'Language {lang} not found'}), 404
    
    verse = get_verse_by_id(verse_id, lang)
    
    if verse:
        return jsonify(verse)
    return jsonify({'error': 'Verse not found'}), 404

@app.route('/verse', methods=['GET'])
def get_specific_verse():
    lang = request.args.get('lang', 'en')
    book_name = request.args.get('book_name')
    chapter = request.args.get('chapter')
    verse_number = request.args.get('verse')
    
    if lang not in SUPPORTED_LANGUAGES:
        return jsonify({'error': f'Language {lang} not found'}), 404
    
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT verse_id 
            FROM verses 
            WHERE language = ? 
            AND book_name = ? 
            AND chapter = ? 
            AND verse = ?
        """, (lang, book_name, chapter, verse_number))
        
        result = cursor.fetchone()
        if result:
            verse = get_verse_by_id(result['verse_id'], lang)
            return jsonify(verse)
    
    return jsonify({'error': 'Verse not found'}), 404

@app.route("/get_chapter_verse", methods=["POST"])
def get_chapter_verse():
    """AJAX endpoint to get the first verse ID of a chapter"""
    book_name = request.form.get("book_name")
    chapter = request.form.get("chapter")
    lang = request.form.get("lang")
    
    verse_id = get_first_verse_id_of_chapter(book_name, chapter, lang)
    if verse_id:
        return jsonify({"verse_id": verse_id})
    return jsonify({"error": "Chapter not found"}), 404

@app.route("/chapter_verses", methods=["POST"])
def get_chapter_verses_route():
    """AJAX endpoint to get all verses in a chapter"""
    book_name = request.form.get("book_name")
    chapter = request.form.get("chapter")
    lang = request.form.get("lang")
    
    verses = get_chapter_verses(book_name, chapter, lang)
    if verses:
        return jsonify({"verses": verses})
    return jsonify({"error": "Chapter not found"}), 404

@app.route("/search", methods=["POST"])
def search():
    keyword = request.form.get("keyword", "").strip()
    lang = request.form.get("lang", "en")
    
    if not keyword:
        return redirect(url_for("home"))
    
    search_results = search_verses(keyword, lang)
    
    # Get current verse for navigation context
    verse_id = request.form.get("verse_id", "1")
    verse = get_verse_by_id(verse_id, lang)
    
    # Get book information
    books = get_book_info(lang)
    old_testament_books = {book: books[book] for book in OLD_TESTAMENT if book in books}
    new_testament_books = {book: books[book] for book in NEW_TESTAMENT if book in books}
    
    # Load theme colors
    theme = load_theme()
    
    return render_template(
        "index.html",
        languages=SUPPORTED_LANGUAGES,
        selected_lang=lang,
        verse=verse,
        old_testament=old_testament_books,
        new_testament=new_testament_books,
        current_book=verse['book_name'] if verse else None,
        current_chapter=verse['chapter'] if verse else None,
        theme=theme,
        search_results=search_results,
        search_query=keyword
    )

@app.route("/", methods=["GET", "POST"])
def home():
    selected_lang = request.form.get("lang", "en")
    verse_id = request.form.get("verse_id", "1")
    
    if selected_lang not in SUPPORTED_LANGUAGES:
        return f"Language {selected_lang} not supported.", 404

    # Get book information
    books = get_book_info(selected_lang)
    
    # Get current verse
    verse = get_verse_by_id(verse_id, selected_lang)
    
    if verse is None:
        # Fallback to the first verse
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT verse_id 
                FROM verses 
                WHERE language = ? 
                ORDER BY verse_id ASC 
                LIMIT 1
            """, (selected_lang,))
            result = cursor.fetchone()
            
            if result:
                verse = get_verse_by_id(result['verse_id'], selected_lang)
            else:
                return "No verses found.", 404

    # Get verses in current chapter
    chapter_verses = get_chapter_verses(verse['book_name'], verse['chapter'], selected_lang)

    # Organize books by testament
    old_testament_books = {book: books[book] for book in OLD_TESTAMENT if book in books}
    new_testament_books = {book: books[book] for book in NEW_TESTAMENT if book in books}

    # Load theme colors
    theme = load_theme()

    return render_template(
        "index.html",
        languages=SUPPORTED_LANGUAGES,
        selected_lang=selected_lang,
        verse=verse,
        chapter_verses=chapter_verses,
        old_testament=old_testament_books,
        new_testament=new_testament_books,
        current_book=verse['book_name'] if verse else None,
        current_chapter=verse['chapter'] if verse else None,
        theme=theme
    )

@app.teardown_appcontext
def close_connection(exception):
    if hasattr(db_local, "connection"):
        db_local.connection.close()
        del db_local.connection
    # Clear verse cache when the app context ends
    verse_cache.clear()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)