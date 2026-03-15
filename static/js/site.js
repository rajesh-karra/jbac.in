const menuToggle = document.querySelector('[data-menu-toggle]');
const menu = document.querySelector('[data-menu]');

if (menuToggle && menu) {
    menuToggle.addEventListener('click', () => {
        const expanded = menuToggle.getAttribute('aria-expanded') === 'true';
        menuToggle.setAttribute('aria-expanded', String(!expanded));
        menu.classList.toggle('open');
        if (expanded) {
            document.querySelectorAll('.nav-dropdown.open').forEach(dropdown => {
                dropdown.classList.remove('open');
                const trigger = dropdown.querySelector('[data-nav-dropdown-trigger]');
                if (trigger) {
                    trigger.setAttribute('aria-expanded', 'false');
                }
            });
        }
    });
}

const navDropdownTriggers = document.querySelectorAll('[data-nav-dropdown-trigger]');
const compactNavQuery = window.matchMedia('(max-width: 980px)');

const closeOtherDropdowns = current => {
    document.querySelectorAll('.nav-dropdown.open').forEach(dropdown => {
        if (current && dropdown === current) {
            return;
        }
        dropdown.classList.remove('open');
        const trigger = dropdown.querySelector('[data-nav-dropdown-trigger]');
        if (trigger) {
            trigger.setAttribute('aria-expanded', 'false');
        }
    });
};

if (navDropdownTriggers.length) {
    navDropdownTriggers.forEach(trigger => {
        trigger.addEventListener('click', event => {
            if (!compactNavQuery.matches) {
                return;
            }

            const dropdown = trigger.closest('.nav-dropdown');
            if (!dropdown) {
                return;
            }

            const isOpen = dropdown.classList.contains('open');
            if (!isOpen) {
                event.preventDefault();
                closeOtherDropdowns(dropdown);
                dropdown.classList.add('open');
                trigger.setAttribute('aria-expanded', 'true');
            }
        });
    });

    document.addEventListener('click', event => {
        if (!compactNavQuery.matches) {
            return;
        }
        if (event.target.closest('.nav-dropdown') || event.target.closest('[data-menu-toggle]')) {
            return;
        }
        closeOtherDropdowns(null);
    });
}

const revealItems = document.querySelectorAll('[data-reveal]');

if ('IntersectionObserver' in window && revealItems.length) {
    const observer = new IntersectionObserver(
        entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.12 }
    );

    revealItems.forEach(item => observer.observe(item));
} else {
    revealItems.forEach(item => item.classList.add('revealed'));
}

const songCards = document.querySelectorAll('[data-song-detail-url]');

if (songCards.length) {
    const shouldIgnoreNavigationTarget = target => {
        return Boolean(target.closest('a, button, input, select, textarea, label'));
    };

    songCards.forEach(card => {
        const destination = card.dataset.songDetailUrl;
        if (!destination) {
            return;
        }

        card.addEventListener('click', event => {
            if (shouldIgnoreNavigationTarget(event.target)) {
                return;
            }
            window.location.href = destination;
        });

        card.addEventListener('keydown', event => {
            if (event.key !== 'Enter' && event.key !== ' ') {
                return;
            }
            event.preventDefault();
            window.location.href = destination;
        });
    });
}

const booksPage = document.querySelector('[data-books-page]');

if (booksPage) {
    const booksGrid = booksPage.querySelector('[data-books-grid]');
    const booksNote = booksPage.querySelector('[data-books-note]');
    const booksSummary = booksPage.querySelector('[data-books-summary]');
    const booksEmpty = booksPage.querySelector('[data-books-empty]');
    const booksPagination = booksPage.querySelector('[data-books-pagination]');
    const query = (booksPage.dataset.booksQuery || '').trim() || 'christianity';

    const escapeHtml = value => {
        return String(value)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    };

    const bookCardMarkup = book => {
        const title = escapeHtml(book.title || 'Untitled book');
        const authors = escapeHtml((book.authors || []).map(author => author.name).filter(Boolean).join(', '));
        const subjects = escapeHtml((book.subjects || []).slice(0, 4).join(', '));
        const downloadCount = book.download_count || '';
        const formats = book.formats || {};
        const openLink = formats['text/html']
            || formats['application/epub+zip']
            || formats['text/plain; charset=utf-8']
            || formats['application/pdf']
            || '';

        if (!openLink) {
            return '';
        }

        const thumb = formats['image/jpeg'] || '';
        const safeOpenLink = escapeHtml(openLink);

        return `
            <article class="result-card book-card" data-reveal>
                ${thumb ? `<img class="book-cover" src="${escapeHtml(thumb)}" alt="${title} cover">` : '<div class="book-cover-placeholder">No Cover</div>'}
                <h3><a href="${safeOpenLink}" target="_blank" rel="noopener noreferrer">${title}</a></h3>
                ${authors ? `<p><strong>Author(s):</strong> ${authors}</p>` : ''}
                ${downloadCount ? `<p><strong>Downloads:</strong> ${escapeHtml(downloadCount)}</p>` : ''}
                ${subjects ? `<p><strong>Topics:</strong> ${subjects}</p>` : ''}
                <a class="button button-secondary" href="${safeOpenLink}" target="_blank" rel="noopener noreferrer">Open Free Book</a>
            </article>
        `;
    };

    const shouldHydrateFromBrowser = booksNote && booksNote.textContent.toLowerCase().includes('fallback mode');

    if (shouldHydrateFromBrowser && booksGrid) {
        fetch(`https://gutendex.com/books/?search=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(payload => {
                const results = Array.isArray(payload.results) ? payload.results : [];
                const cards = results.slice(0, 36).map(bookCardMarkup).filter(Boolean);
                if (!cards.length) {
                    return;
                }

                booksGrid.innerHTML = cards.join('');
                if (booksNote) {
                    booksNote.textContent = 'Source: Gutendex free books API (browser mode)';
                }
                if (booksSummary) {
                    booksSummary.textContent = `Showing ${cards.length} books`;
                }
                if (booksEmpty) {
                    booksEmpty.remove();
                }
                if (booksPagination) {
                    booksPagination.remove();
                }

                const refreshedRevealItems = booksGrid.querySelectorAll('[data-reveal]');
                refreshedRevealItems.forEach(item => item.classList.add('revealed'));
            })
            .catch(() => {
                // Keep server-rendered fallback list if browser fetch fails.
            });
    }
}