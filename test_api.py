import pytest
from api import app, load_csv_data

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def sample_data():
    return [
        {
            "Verse ID": "1001",
            "Book Name": "Genesis",
            "Book Number": "1",
            "Chapter": "1",
            "Verse": "1",
            "Text": "In the beginning God created the heaven and the earth."
        },
        {
            "Verse ID": "1002",
            "Book Name": "Genesis",
            "Book Number": "1",
            "Chapter": "1",
            "Verse": "2",
            "Text": "And the earth was without form, and void; and darkness was upon the face of the deep."
        }
    ]

@pytest.fixture(autouse=True)
def mock_data(monkeypatch, sample_data):
    def mock_load_csv_data(lang):
        return sample_data if lang == "en" else None
    monkeypatch.setattr("api.load_csv_data", mock_load_csv_data)


# Random Endpoint Tests
def test_random_endpoint(client, sample_data):
    response = client.get('/verse/random?lang=en')
    assert response.status_code == 200, f"Unexpected status: {response.status_code}"
    data = response.get_json()
    assert data is not None, "Response data is None"
    assert "Verse ID" in data, f"Response missing 'Verse ID': {data}"
    assert "next" in data, f"Response missing 'next': {data}"
    assert "previous" in data, f"Response missing 'previous': {data}"


def test_random_invalid_lang(client):
    """It should return 404 when language is not found."""
    response = client.get('/verse/random?lang=idontexist')
    assert response.status_code == 404
    data = response.get_json()
    assert data == {"error": "Language idontexist not found"}

# Specific Verse Endpoint Tests
def test_get_specific_verse(client, sample_data):
    """It should return a specific verse by book, chapter, and verse."""
    response = client.get('/verse?lang=en&book_name=Genesis&chapter=1&verse=1')
    assert response.status_code == 200
    data = response.get_json()
    assert data["Verse ID"] == "1001"
    assert data["next"] == "1002"
    assert data["previous"] is None

def test_get_specific_verse_not_found(client):
    """It should return 404 when the verse is not found."""
    response = client.get('/verse?lang=en&book_name=Exodus&chapter=1&verse=1')
    assert response.status_code == 404
    data = response.get_json()
    assert data == {"error": "Verse not found"}

# Verse by ID Endpoint Tests
def test_get_verse_by_id(client, sample_data):
    """It should return a verse by its ID with next and previous fields."""
    response = client.get('/verse/id?lang=en&verse_id=1002')
    assert response.status_code == 200
    data = response.get_json()
    assert data["Verse ID"] == "1002"
    assert data["next"] is None
    assert data["previous"] == "1001"

def test_get_verse_by_id_not_found(client):
    """It should return 404 when the verse ID is not found."""
    response = client.get('/verse/id?lang=en&verse_id=9999')
    assert response.status_code == 404
    data = response.get_json()
    assert data == {"error": "Verse not found"}
