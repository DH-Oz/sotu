"""Tests for the SOTU fetcher tool (tools/fetch.py)."""

import os
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

from tools import fetch


def test_url_to_filename() -> None:
    """Assert that URLs are mapped to correct, safe filenames."""
    url1 = (
        "https://www.presidency.ucsb.edu/documents/"
        "address-before-joint-session-the-congress"
    )
    expected1 = "address-before-joint-session-the-congress.html"
    assert fetch.url_to_filename(url1) == expected1

    url2 = "https://www.presidency.ucsb.edu/ws/index.php?pid=4102"
    assert fetch.url_to_filename(url2) == "pid_4102.html"

    url3 = "https://www.presidency.ucsb.edu/documents/some-slug/"
    assert fetch.url_to_filename(url3) == "some-slug.html"


@respx.mock
@pytest.mark.asyncio
async def test_fetch_url_success(tmp_path: pytest.TempPathFactory) -> None:
    """Assert that fetching a URL successfully writes content and honors cache."""
    out_dir = str(tmp_path)
    url = "https://www.presidency.ucsb.edu/documents/test-speech"
    filename = "test-speech.html"
    filepath = os.path.join(out_dir, filename)

    # Mock HTTP response
    route = respx.get(url).mock(
        return_value=Response(200, text="<html>SOTU content</html>")
    )

    # Fetch
    success = await fetch.fetch_url(url, out_dir, delay=0.0)
    assert success is True
    assert route.called

    # Verify file content
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    assert content == "<html>SOTU content</html>"

    # Reset route mock and test skip/idempotence
    route.reset()
    success_cache = await fetch.fetch_url(url, out_dir, delay=0.0)
    assert success_cache is True
    assert not route.called  # skipped due to cache


@respx.mock
@pytest.mark.asyncio
async def test_fetch_url_retry_and_fail() -> None:
    """Assert that fetch_url retries on HTTP errors and eventually fails or succeeds."""
    url = "https://www.presidency.ucsb.edu/documents/fail-speech"

    # Mock HTTP errors then a success, or just continuous failure
    route = respx.get(url).mock(
        side_effect=[
            Response(500),
            Response(502),
            Response(200, text="<html>Finally recovered</html>"),
        ]
    )

    # We mock asyncio.sleep so the test runs instantly despite retries/backoffs
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        html = await fetch.download_html_with_retry(
            url, max_retries=3, backoff_factor=0.0
        )
        assert html == "<html>Finally recovered</html>"
        assert route.call_count == 3
        assert mock_sleep.called


@pytest.mark.asyncio
async def test_rate_limiting_delay() -> None:
    """Assert that batch fetch introduces a rate-limiting delay between requests."""
    urls = [
        "https://www.presidency.ucsb.edu/documents/speech-1",
        "https://www.presidency.ucsb.edu/documents/speech-2",
        "https://www.presidency.ucsb.edu/documents/speech-3",
    ]

    # We mock fetch_url to not actually hit network/disk but just record calls
    with (
        patch("tools.fetch.fetch_url", new_callable=AsyncMock) as mock_fetch_url,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        mock_fetch_url.return_value = True

        await fetch.fetch_all_urls(urls, "/tmp/dummy", delay=2.0)

        # For 3 URLs, it should attempt to fetch all 3.
        assert mock_fetch_url.call_count == 3
        # We delay 2.0s before 2nd and 3rd requests (total 2 sleeps)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(2.0)
