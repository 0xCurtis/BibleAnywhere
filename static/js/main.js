// Book and Chapter Navigation
function toggleChapters(book) {
    const bookId = book.replace(/ /g, '_');
    const chapterList = document.getElementById(bookId);
    const allChapterLists = document.getElementsByClassName('chapter-list');
    
    // Close all other chapter lists
    for (let list of allChapterLists) {
        if (list.id !== bookId) {
            list.classList.remove('active');
        }
    }
    
    // Toggle the clicked book's chapter list
    chapterList.classList.toggle('active');
    
    // Update active book highlighting
    const allBookItems = document.getElementsByClassName('book-item');
    for (let item of allBookItems) {
        item.classList.remove('active');
    }
    chapterList.parentElement.classList.add('active');
}

function navigateToChapter(book, chapter, lang) {
    // Create form data
    const formData = new FormData();
    formData.append('book_name', book);
    formData.append('chapter', chapter);
    formData.append('lang', lang);

    // Send POST request to get the verse ID
    fetch('/get_chapter_verse', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.verse_id) {
            navigateToVerse(data.verse_id, lang);
        }
    })
    .catch(error => console.error('Error:', error));
}

// Verse Navigation
function navigateToVerse(verseId, lang = currentLang) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.style.display = 'none';

    const langInput = document.createElement('input');
    langInput.type = 'hidden';
    langInput.name = 'lang';
    langInput.value = lang;

    const verseInput = document.createElement('input');
    verseInput.type = 'hidden';
    verseInput.name = 'verse_id';
    verseInput.value = verseId;

    form.appendChild(langInput);
    form.appendChild(verseInput);
    document.body.appendChild(form);
    form.submit();
}

// Chapter View Toggle
function toggleChapterView() {
    const chapterView = document.getElementById('chapterView');
    const verseContainer = document.querySelector('.verse-container');
    const btn = document.getElementById('viewChapterBtn');
    
    if (chapterView.classList.contains('active')) {
        // Switch to single verse view
        chapterView.classList.remove('active');
        verseContainer.style.display = 'block';
        btn.textContent = 'View Full Chapter';
    } else {
        // Switch to chapter view
        chapterView.classList.add('active');
        verseContainer.style.display = 'none';
        btn.textContent = 'Show Single Verse';
        
        // Scroll to current verse if it exists
        const currentVerse = document.querySelector('.verse-item.current');
        if (currentVerse) {
            setTimeout(() => {
                currentVerse.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 100);
        }
    }
}

// Mobile Menu
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
    
    // Prevent body scrolling when sidebar is open on mobile
    document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : '';
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Scroll to active book
    const activeBook = document.querySelector('.book-item.active');
    if (activeBook) {
        activeBook.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(event) {
        const sidebar = document.querySelector('.sidebar');
        const menuToggle = document.querySelector('.menu-toggle');
        
        if (window.innerWidth <= 768 && 
            !sidebar.contains(event.target) && 
            !menuToggle.contains(event.target) &&
            sidebar.classList.contains('active')) {
            toggleSidebar();
        }
    });

    // Handle window resize
    window.addEventListener('resize', function() {
        const sidebar = document.querySelector('.sidebar');
        const overlay = document.querySelector('.sidebar-overlay');
        
        if (window.innerWidth > 768 && sidebar.classList.contains('active')) {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
}); 