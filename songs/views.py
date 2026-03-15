import json
import time
from urllib import parse, request
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render


SONG_CATEGORIES = {
    "all": "All",
    "telugu": "Telugu",
    "hymns": "Hymns",
    "choruses": "Choruses",
}

DISPLAY_CATEGORY_LABELS = {
    "telugu": "Telugu",
    "hymns": "Hyms (Hymns)",
    "choruses": "Choruses",
}

_CATEGORY_ALIASES = {
    "hymn": "hymns",
    "hyms": "hymns",
    "chorous": "choruses",
    "chorouse": "choruses",
    "chorouses": "choruses",
    "chorus": "choruses",
}

_CATEGORY_TO_DOCUMENT_ID = {
    "telugu": "TeluguSongs",
    "hymns": "EnglishHymns",
    "choruses": "EnglishChoruses",
}

_CACHE_TTL_SECONDS = 600
_BOOK_CACHE = {}
_PAGE_SIZE = 24
_BOOKS_PAGE_SIZE = 18

_FALLBACK_FREE_BOOKS = [
    {
        "title": "The Kingdom of God Is Within You",
        "authors": "Leo Tolstoy",
        "subjects": "Christian ethics, Non-violence, Christianity",
        "download_count": "",
        "thumbnail": "",
        "info_link": "https://www.gutenberg.org/ebooks/43302",
    },
    {
        "title": "Orthodoxy",
        "authors": "G. K. Chesterton",
        "subjects": "Christian apologetics, Christian thought",
        "download_count": "",
        "thumbnail": "",
        "info_link": "https://www.gutenberg.org/ebooks/130",
    },
    {
        "title": "The Practice of the Presence of God",
        "authors": "Brother Lawrence",
        "subjects": "Devotional literature, Christian life",
        "download_count": "",
        "thumbnail": "",
        "info_link": "https://www.gutenberg.org/ebooks/5657",
    },
    {
        "title": "The Imitation of Christ",
        "authors": "Thomas a Kempis",
        "subjects": "Christian devotion, Spiritual life",
        "download_count": "",
        "thumbnail": "",
        "info_link": "https://www.gutenberg.org/ebooks/1653",
    },
    {
        "title": "Foxe's Book of Martyrs",
        "authors": "John Foxe",
        "subjects": "Church history, Martyrs",
        "download_count": "",
        "thumbnail": "",
        "info_link": "https://www.gutenberg.org/ebooks/22400",
    },
    {
        "title": "Confessions",
        "authors": "Saint Augustine",
        "subjects": "Christian autobiography, Theology",
        "download_count": "",
        "thumbnail": "",
        "info_link": "https://www.gutenberg.org/ebooks/3296",
    },
    {
        "title": "The Pilgrim's Progress",
        "authors": "John Bunyan",
        "subjects": "Christian allegory, Classic literature",
        "download_count": "",
        "thumbnail": "",
        "info_link": "https://www.gutenberg.org/ebooks/131",
    },
    {
        "title": "Morning and Evening",
        "authors": "Charles H. Spurgeon",
        "subjects": "Daily devotion, Sermons",
        "download_count": "",
        "thumbnail": "",
        "info_link": "https://www.gutenberg.org/ebooks/17484",
    },
    {
        "title": "On Prayer and the Contemplative Life",
        "authors": "Thomas Aquinas",
        "subjects": "Prayer, Christian philosophy",
        "download_count": "",
        "thumbnail": "",
        "info_link": "https://www.gutenberg.org/ebooks/18704",
    },
    {
        "title": "The Life of Trust",
        "authors": "George Muller",
        "subjects": "Faith, Christian biography",
        "download_count": "",
        "thumbnail": "",
        "info_link": "https://www.gutenberg.org/ebooks/11134",
    },
    {
        "title": "A Treatise on Christian Doctrine",
        "authors": "John Milton",
        "subjects": "Systematic theology, Christian doctrine",
        "download_count": "",
        "thumbnail": "",
        "info_link": "https://www.gutenberg.org/ebooks/10173",
    },
    {
        "title": "The Gospel Day",
        "authors": "Charles Ebert Orr",
        "subjects": "Christian teaching, Gospel",
        "download_count": "",
        "thumbnail": "",
        "info_link": "https://www.gutenberg.org/ebooks/27644",
    },
]


def _filter_fallback_books(query):
    query_text = (query or "").strip().lower()
    if not query_text:
        return list(_FALLBACK_FREE_BOOKS)

    result = []
    for book in _FALLBACK_FREE_BOOKS:
        haystack = " ".join(
            [
                str(book.get("title") or ""),
                str(book.get("authors") or ""),
                str(book.get("subjects") or ""),
            ]
        ).lower()
        if query_text in haystack:
            result.append(book)
    return result


def _build_pagination_links(current_page, total_pages, radius=2):
    if total_pages <= 1:
        return []

    candidates = {1, total_pages}
    for page_number in range(current_page - radius, current_page + radius + 1):
        if 1 <= page_number <= total_pages:
            candidates.add(page_number)

    sorted_pages = sorted(candidates)
    links = []
    previous = None
    for page_number in sorted_pages:
        if previous is not None and page_number - previous > 1:
            links.append({"type": "ellipsis"})
        links.append({"type": "page", "number": page_number, "active": page_number == current_page})
        previous = page_number
    return links


def _song_sort_key(song):
    raw_number = str(song.get("song_number") or "").strip()
    try:
        numeric_number = int(raw_number)
    except ValueError:
        numeric_number = 10**9
    return (
        numeric_number,
        raw_number.lower(),
        str(song.get("title") or "").lower(),
    )


def _normalize_category(raw_value):
    value = (raw_value or "").strip().lower()
    if not value:
        return "all"
    if value in SONG_CATEGORIES:
        return value
    return _CATEGORY_ALIASES.get(value, "all")


def _get_json(url, headers=None):
    headers = headers or {"Accept": "application/json"}
    request_obj = request.Request(url, headers=headers)
    timeout = max(1, int(getattr(settings, "ANDHRA_CHRISTIAN_SONGS_TIMEOUT_SECONDS", 10)))
    with request.urlopen(request_obj, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _cached_fetch_json(url, headers=None):
    now = time.time()
    cached = _BOOK_CACHE.get(url)
    if cached and now - cached["ts"] < _CACHE_TTL_SECONDS:
        return cached["payload"]

    payload = _get_json(url, headers=headers)
    _BOOK_CACHE[url] = {"ts": now, "payload": payload}
    return payload


def _extract_items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("songs", "data", "results", "items", "list"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        if payload.get("song") and isinstance(payload["song"], dict):
            return [payload["song"]]
    return []


def _detect_category(song):
    combined = " ".join(
        [
            str(song.get("category", "")),
            str(song.get("type", "")),
            str(song.get("genre", "")),
            str(song.get("language", "")),
            str(song.get("tags", "")),
        ]
    ).lower()

    if "telugu" in combined:
        return "telugu"
    if "hymn" in combined or "hyms" in combined:
        return "hymns"
    if "chorus" in combined or "chorouse" in combined or "chorous" in combined:
        return "choruses"
    return "all"


def _normalized_song(song):
    if not isinstance(song, dict):
        return None

    title = (
        song.get("title")
        or song.get("name")
        or song.get("song_title")
        or song.get("lyrics_title")
        or song.get("displayName")
        or "Untitled song"
    )
    lyrics = song.get("lyrics") or song.get("content") or song.get("body") or ""
    artist = song.get("artist") or song.get("author") or song.get("composer") or ""
    language = song.get("language") or ""
    category = _normalize_category(song.get("category") or _detect_category(song))
    song_url = song.get("url") or song.get("link") or song.get("permalink") or ""

    return {
        "song_number": song.get("songNumber") or song.get("number") or "",
        "title": str(title).strip(),
        "lyrics": str(lyrics).strip(),
        "romanized_title": str(song.get("romanizedTitle") or "").strip(),
        "tags": str(song.get("tags") or "").strip(),
        "artist": str(artist).strip(),
        "language": str(language).strip(),
        "display_name": str(song.get("displayName") or "").strip(),
        "document_id": str(song.get("documentId") or "").strip(),
        "category": category,
        "song_url": str(song_url).strip(),
    }


def _search_match(song, query):
    if not query:
        return True
    haystack = " ".join(
        [
            str(song.get("song_number", "")),
            song.get("title", ""),
            song.get("romanized_title", ""),
            song.get("lyrics", ""),
            song.get("tags", ""),
            song.get("artist", ""),
            song.get("language", ""),
        ]
    ).lower()
    return query in haystack


def _fetch_songs_from_api(query, category):
    base_url = getattr(settings, "ANDHRA_CHRISTIAN_SONGS_API_URL", "").strip()
    api_key = getattr(settings, "ANDHRA_CHRISTIAN_SONGS_API_KEY", "").strip()
    books_url = getattr(settings, "ANDHRA_CHRISTIAN_SONGS_BOOKS_URL", "").strip()

    try:
        if base_url:
            query_params = {}
            if query:
                query_params["q"] = query
            if category and category != "all":
                query_params["category"] = category

            endpoint = f"{base_url}?{parse.urlencode(query_params)}" if query_params else base_url
            headers = {"Accept": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            payload = _get_json(endpoint, headers=headers)

            normalized = []
            for raw_song in _extract_items(payload):
                song = _normalized_song(raw_song)
                if song is None:
                    continue
                if category != "all" and song["category"] != category:
                    continue
                if not _search_match(song, query):
                    continue
                normalized.append(song)
            return normalized[:300], "Source: configured Andhra Christian Songs API"

        if not books_url:
            return [], "Songs source is not configured."

        books_payload = _cached_fetch_json(books_url)
        books = books_payload if isinstance(books_payload, list) else _extract_items(books_payload)
        category_doc_id = _CATEGORY_TO_DOCUMENT_ID.get(category)
        songs = []

        for book in books:
            if not isinstance(book, dict):
                continue
            document_id = str(book.get("documentId") or "").strip()
            if category != "all" and document_id != category_doc_id:
                continue

            book_url = str(book.get("url") or "").strip()
            if not book_url:
                continue

            for raw_song in _cached_fetch_json(book_url):
                if not isinstance(raw_song, dict):
                    continue
                enriched = {
                    **raw_song,
                    "displayName": book.get("displayName") or raw_song.get("displayName"),
                    "documentId": document_id or raw_song.get("documentId"),
                    "language": raw_song.get("language") or book.get("defaultLanguage"),
                    "category": _normalize_category(
                        raw_song.get("category")
                        or (
                            "telugu"
                            if document_id == "TeluguSongs"
                            else "hymns"
                            if document_id == "EnglishHymns"
                            else "choruses"
                            if document_id == "EnglishChoruses"
                            else "all"
                        )
                    ),
                }
                song = _normalized_song(enriched)
                if song is None:
                    continue
                if category != "all" and song["category"] != category:
                    continue
                if not _search_match(song, query):
                    continue
                songs.append(song)

        songs.sort(key=_song_sort_key)
        return songs[:500], "Source: Rejoice In Lord public songs database"
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return [], "Songs service is temporarily unavailable. Please try again later."


def _fetch_christian_books(query):
    books_api_url = getattr(settings, "CHRISTIAN_BOOKS_API_URL", "https://gutendex.com/books").strip()
    max_results = max(6, min(100, int(getattr(settings, "CHRISTIAN_BOOKS_MAX_RESULTS", "36"))))
    default_query = getattr(settings, "CHRISTIAN_BOOKS_DEFAULT_QUERY", "christianity")

    if not books_api_url:
        return [], "Christian books source is not configured."

    query_text = query.strip() or default_query
    endpoint = f"{books_api_url}?{parse.urlencode({'search': query_text})}"

    try:
        payload = _cached_fetch_json(endpoint)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
        fallback = _filter_fallback_books(query_text)
        return fallback, "Source: Curated free Christian books (fallback mode)"

    items = payload.get("results", []) if isinstance(payload, dict) else _extract_items(payload)
    books = []
    for item in items:
        if not isinstance(item, dict):
            continue
        formats = item.get("formats") or {}
        if not isinstance(formats, dict):
            continue

        open_link = (
            formats.get("text/html")
            or formats.get("application/epub+zip")
            or formats.get("text/plain; charset=utf-8")
            or formats.get("application/pdf")
            or ""
        )
        if not open_link:
            continue

        title = str(item.get("title") or "Untitled book").strip()
        authors = item.get("authors") or []
        authors_text = ", ".join(
            str(author.get("name") or "").strip()
            for author in authors
            if isinstance(author, dict) and str(author.get("name") or "").strip()
        )

        download_count = item.get("download_count") or ""
        subjects = item.get("subjects") or []
        subjects_text = ", ".join(str(subject).strip() for subject in subjects[:4] if str(subject).strip())
        cover_image = formats.get("image/jpeg") or ""

        books.append(
            {
                "title": title,
                "authors": authors_text,
                "description": "",
                "published_date": "",
                "page_count": "",
                "thumbnail": cover_image,
                "info_link": str(open_link).strip(),
                "download_count": download_count,
                "subjects": subjects_text,
            }
        )
        if len(books) >= max_results:
            break

    books.sort(key=lambda row: str(row.get("title") or "").lower())
    if not books:
        fallback = _filter_fallback_books(query_text)
        return fallback, "Source: Curated free Christian books (fallback mode)"
    return books, "Source: Gutendex free books API"


def songs_search(request, category=None):
    requested_category = request.GET.get("category")
    selected_category = _normalize_category(requested_category or category or "all")
    query = request.GET.get("q", "").strip().lower()
    songs, service_note = _fetch_songs_from_api(query=query, category=selected_category)

    grouped_songs = []
    page_obj = None
    pagination_links = []
    page_songs = songs

    if selected_category == "all":
        for category_key in ("telugu", "hymns", "choruses"):
            category_rows = [song for song in songs if song.get("category") == category_key]
            grouped_songs.append(
                {
                    "key": category_key,
                    "label": DISPLAY_CATEGORY_LABELS.get(category_key, category_key.title()),
                    "songs": category_rows,
                }
            )
    else:
        paginator = Paginator(songs, _PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page") or 1)
        pagination_links = _build_pagination_links(page_obj.number, paginator.num_pages)
        page_songs = page_obj.object_list
        grouped_songs.append(
            {
                "key": selected_category,
                "label": DISPLAY_CATEGORY_LABELS.get(selected_category, selected_category.title()),
                "songs": page_songs,
            }
        )

    return render(
        request,
        "songs/search.html",
        {
            "songs": page_songs,
            "grouped_songs": grouped_songs,
            "page_obj": page_obj,
            "pagination_links": pagination_links,
            "total_matches": len(songs),
            "query": request.GET.get("q", "").strip(),
            "service_note": service_note,
            "selected_category": selected_category,
            "categories": SONG_CATEGORIES,
        },
    )


def books_list(request):
    query = request.GET.get("q", "").strip()
    books, service_note = _fetch_christian_books(query)
    paginator = Paginator(books, _BOOKS_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    pagination_links = _build_pagination_links(page_obj.number, paginator.num_pages)

    return render(
        request,
        "songs/books.html",
        {
            "books": page_obj.object_list,
            "query": query,
            "page_obj": page_obj,
            "pagination_links": pagination_links,
            "total_matches": paginator.count,
            "service_note": service_note,
        },
    )


def song_detail(request):
    raw_category = request.GET.get("category", "")
    selected_category = _normalize_category(raw_category)
    if selected_category == "all":
        raise Http404("Category is required.")

    number_param = (request.GET.get("number") or "").strip()
    title_param = (request.GET.get("title") or "").strip().lower()

    songs, service_note = _fetch_songs_from_api(query="", category=selected_category)
    if not songs:
        raise Http404("Song not found.")

    selected_song = None
    for song in songs:
        number_match = number_param and str(song.get("song_number", "")).strip() == number_param
        title_match = title_param and str(song.get("title", "")).strip().lower() == title_param
        if number_match and (not title_param or title_match):
            selected_song = song
            break

    if selected_song is None and title_param:
        for song in songs:
            title_match = title_param in str(song.get("title", "")).strip().lower()
            if title_match:
                selected_song = song
                break

    if selected_song is None:
        raise Http404("Song not found.")

    next_url = (request.GET.get("next") or "").strip()
    if not next_url.startswith("/songs"):
        next_url = f"/songs/{selected_category}/"

    return render(
        request,
        "songs/detail.html",
        {
            "song": selected_song,
            "next_url": next_url,
            "service_note": service_note,
        },
    )
