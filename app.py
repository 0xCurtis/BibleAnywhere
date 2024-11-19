from flask import Flask, render_template, request, jsonify
import csv
import os
import random

app = Flask(__name__)

# Base directory for CSV files
DATA_DIR = "data"
SUPPORTED_LANGUAGES = ["en", "fr", "ru", "pt", "pl"]

# Load data from the specified CSV file
def load_csv_data(lang):
    file_path = os.path.join(DATA_DIR, f"bible{lang}.csv")
    if not os.path.exists(file_path):
        return None  # Return None if the file does not exist

    data = []
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append(row)
    return data

# Get verse by ID
def get_verse_by_id(data, verse_id):
    for idx, verse in enumerate(data):
        if verse['Verse ID'] == verse_id:
            # Determine next and previous verses
            next_id = data[idx + 1]['Verse ID'] if idx + 1 < len(data) else None
            prev_id = data[idx - 1]['Verse ID'] if idx - 1 >= 0 else None
            return {**verse, "next": next_id, "previous": prev_id}
    return None

# Endpoint to fetch a random verse
@app.route('/verse/random', methods=['GET'])
def get_random_verse():
    lang = request.args.get('lang', 'en')
    data = load_csv_data(lang)

    if data is None:
        return jsonify({'error': f'Language {lang} not found'}), 404

    verse = random.choice(data)
    verse_id = verse['Verse ID']
    result = get_verse_by_id(data, verse_id)

    if result:
        return jsonify(result)
    else:
        return jsonify({'error': 'Verse not found'}), 404

# Endpoint to fetch a specific verse by its ID
@app.route('/verse/id', methods=['GET'])
def get_verse_by_id_route():
    lang = request.args.get('lang', 'en')  # Default to English
    verse_id = request.args.get('verse_id')

    if not verse_id:
        return jsonify({'error': 'Verse ID is required'}), 400

    data = load_csv_data(lang)

    if data is None:
        return jsonify({'error': f'Language {lang} not found'}), 404

    verse = get_verse_by_id(data, verse_id)

    if verse:
        return jsonify(verse)
    else:
        return jsonify({'error': 'Verse not found'}), 404

# Endpoint to fetch a specific verse by book, chapter, and verse number
@app.route('/verse', methods=['GET'])
def get_specific_verse():
    lang = request.args.get('lang', 'en')  # Default to English
    book_name = request.args.get('book_name')
    chapter = request.args.get('chapter')
    verse_number = request.args.get('verse')

    data = load_csv_data(lang)

    if data is None:
        return jsonify({'error': f'Language {lang} not found'}), 404

    # Filter data for the requested verse
    for idx, verse in enumerate(data):
        if (
            verse['Book Name'] == book_name and
            verse['Chapter'] == chapter and
            verse['Verse'] == verse_number
        ):
            # Determine next and previous verses
            next_id = data[idx + 1]['Verse ID'] if idx + 1 < len(data) else None
            prev_id = data[idx - 1]['Verse ID'] if idx - 1 >= 0 else None
            return jsonify({**verse, "next": next_id, "previous": prev_id})

    return jsonify({'error': 'Verse not found'}), 404


@app.route("/", methods=["GET", "POST"])
def home():
    # Handle form submission
    selected_lang = request.form.get("lang", "en")  # Default to English
    verse_id = request.form.get("verse_id", "1")    # Default to the first verse

    # Load data for the selected language
    data = load_csv_data(selected_lang)
    if data is None:
        return f"Language {selected_lang} not supported.", 404

    # Fetch the current verse by its ID
    verse = get_verse_by_id(data, verse_id)
    if verse is None:
        verse = data[0]  # Fallback to the first verse

    # Render the webpage
    return render_template(
        "index.html",
        languages=SUPPORTED_LANGUAGES,
        selected_lang=selected_lang,
        verse=verse,
    )

# Main entry point
if __name__ == '__main__':
    app.run()
