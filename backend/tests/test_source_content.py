import socket

import pytest

from app.core.errors import AppError
from app.core.url_security import normalize_and_validate_url
from app.services.source_content import clean_html, create_semantic_chunks, detect_language


def test_url_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))
        ],
    )

    result = normalize_and_validate_url("HTTP://Example.COM:80/guide?q=1#section")

    assert result == "http://example.com/guide?q=1"


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "http://localhost/admin",
        "http://127.0.0.1/data",
        "http://10.0.0.1/data",
        "http://0.0.0.0/data",
    ],
)
def test_invalid_and_private_urls_are_blocked(url: str) -> None:
    with pytest.raises(AppError) as error:
        normalize_and_validate_url(url)

    assert error.value.code == "INVALID_SOURCE_URL"


def test_html_cleaning_removes_noise_and_preserves_structure() -> None:
    clean_content, title = clean_html(
        """
        <html><head><title>Async Python</title><style>.x {}</style></head>
        <body><nav>Menu</nav><h1>Async</h1><p>Use an event loop.</p>
        <h2>Example</h2><pre>await task()</pre><footer>Copyright</footer></body></html>
        """
    )

    assert title == "Async Python"
    assert "Menu" not in clean_content
    assert "Copyright" not in clean_content
    assert "# Async" in clean_content
    assert "```" in clean_content

    chunks = create_semantic_chunks(clean_content)
    assert [chunk.heading_path for chunk in chunks] == ["Async", "Async > Example"]
    assert chunks[1].content == "```\nawait task()\n```"


def test_detects_russian_and_english_content() -> None:
    assert detect_language("Функции помогают повторно использовать код программы.") == "ru"
    assert detect_language("Functions help organize and reuse program code.") == "en"
