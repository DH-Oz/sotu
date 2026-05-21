"""Fetcher tool for downloading SOTU raw HTML documents from UCSB."""

import argparse
import asyncio
import os
import sys
from urllib.parse import parse_qs, urlparse

import httpx


def url_to_filename(url: str) -> str:
    """Map a UCSB SOTU URL to a safe, unique HTML filename.

    Parameters
    - url (str): UCSB document URL.

    Returns
    - str: Safe filename.
    """
    parsed = urlparse(url)

    # Check if this is a query-based URL (e.g. pid=4102)
    query_params = parse_qs(parsed.query)
    if "pid" in query_params:
        pid = query_params["pid"][0]
        if pid:
            return f"pid_{pid}.html"

    # Otherwise extract the last non-empty segment of path
    path = parsed.path.strip("/")
    parts = path.split("/")
    if parts:
        slug = parts[-1]
        if slug:
            return f"{slug}.html"

    # Fallback to hash if empty/malformed
    import hashlib

    h = hashlib.md5(url.encode("utf-8")).hexdigest()
    return f"doc_{h}.html"


async def download_html_with_retry(
    url: str,
    max_retries: int = 5,
    backoff_factor: float = 2.0,
) -> str:
    """Download HTML content from a URL with exponential backoff and retries.

    Parameters
    - url (str): The target URL.
    - max_retries (int): Maximum number of retry attempts.
    - backoff_factor (float): Multiplier for exponential backoff sleep.

    Returns
    - str: HTML content.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient(
        headers=headers, follow_redirects=True, timeout=10.0
    ) as client:
        attempt = 0
        while True:
            attempt += 1
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                # If status is 5xx or general request error, we retry.
                # But we fail early on 404 or 403.
                if isinstance(e, httpx.HTTPStatusError):
                    if e.response.status_code in (403, 404):
                        raise e

                if attempt >= max_retries:
                    raise e

                # Calculate exponential backoff
                sleep_time = backoff_factor * (2 ** (attempt - 1))
                await asyncio.sleep(sleep_time)


async def fetch_url(url: str, out_dir: str, delay: float = 2.0) -> bool:
    """Fetch a single SOTU URL, write its content to out_dir, and respect caching.

    Parameters
    - url (str): The target SOTU URL.
    - out_dir (str): Directory where downloaded files are saved.
    - delay (float): Pre-request rate-limiting delay (in seconds).

    Returns
    - bool: True if the file exists or was successfully fetched, False otherwise.
    """
    os.makedirs(out_dir, exist_ok=True)
    filename = url_to_filename(url)
    filepath = os.path.join(out_dir, filename)

    # Caching/idempotence check
    if os.path.exists(filepath):
        return True

    # Rate limiting delay
    if delay > 0:
        await asyncio.sleep(delay)

    try:
        html = await download_html_with_retry(url)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}", file=sys.stderr)
        return False


async def fetch_all_urls(urls: list[str], out_dir: str, delay: float = 2.0) -> None:
    """Fetch a list of URLs with a rate-limiting delay between requests.

    Parameters
    - urls (list[str]): List of URLs to fetch.
    - out_dir (str): Output directory.
    - delay (float): Delay in seconds between consecutive requests.
    """
    for idx, url in enumerate(urls):
        if idx > 0 and delay > 0:
            await asyncio.sleep(delay)
        await fetch_url(url, out_dir, delay=0.0)


def main() -> None:
    """CLI entrypoint for tools.fetch."""
    parser = argparse.ArgumentParser(
        description="Download SOTU raw HTML documents from UCSB."
    )
    parser.add_argument(
        "--urls-file",
        help="Path to a file containing SOTU URLs to download (one per line).",
    )
    parser.add_argument(
        "--out-dir",
        default="raw/ucsb",
        help="Directory to save downloaded HTML files.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between requests.",
    )
    parser.add_argument(
        "--full-scrape",
        action="store_true",
        help="Safety safeguard flag to confirm a live download of all SOTU documents.",
    )
    args = parser.parse_args()

    if not args.full_scrape:
        print(
            "Error: --full-scrape flag is required to run a live scrape.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.urls_file or not os.path.exists(args.urls_file):
        print(
            f"Error: URLs file '{args.urls_file}' not found or not specified.",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(args.urls_file, encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"Starting rate-limited download of {len(urls)} URLs to {args.out_dir}...")
    asyncio.run(fetch_all_urls(urls, args.out_dir, args.delay))
    print("Download completed successfully.")


if __name__ == "__main__":
    main()
