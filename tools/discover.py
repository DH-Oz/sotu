"""Tools for discovering SOTU document URLs from UCSB Presidency Project pages.
"""

from selectolax.lexbor import LexborHTMLParser


def normalize_url(url: str) -> str:
    """Prepend UCSB base URL to relative paths if necessary.

    Parameters
    - url (str): Relative or absolute URL.

    Returns
    - str: Normalized absolute URL.
    """
    if not url:
        return ""
    if url.startswith("/"):
        return f"https://www.presidency.ucsb.edu{url}"
    return url


def _is_real_sotu(url: str) -> bool:
    """Filter out non-SOTU joint-session addresses (e.g. incoming first-year).

    Parameters
    - url (str): UCSB document URL.

    Returns
    - bool: True if the address is a true SOTU or Annual Message.
    """
    slug = url.rsplit("/", 1)[-1]
    # Pre-1947 annual addresses/messages:
    if "annual-message" in slug or "annual-address" in slug:
        return True
    # Modern era: keep only addresses with "the-state-the-union"
    # or "state-the-union" in the slug
    if "the-state-the-union" in slug or "state-the-union" in slug:
        return True
    # Query parameters based pid URLs (fallback if any):
    if "pid=" in url:
        return True
    return False


def parse_taxonomy_content(html: str) -> list[str]:
    """Extract SOTU document URLs from a taxonomy page's views rows.

    Parameters
    - html (str): The HTML content of the taxonomy page.

    Returns
    - list[str]: A list of SOTU document URLs.
    """
    parser = LexborHTMLParser(html)
    urls: list[str] = []
    seen: set[str] = set()

    # SOTU document URLs inside .views-row usually have class field-title
    # and contain a link with /documents/ in href.
    for row in parser.css(".view-content .views-row"):
        # Search for title link
        selectors = ".field-title p a, .views-field-title a, a[href*='/documents/']"
        for a in row.css(selectors):
            href = a.attributes.get("href")
            if href:
                normalized = normalize_url(href)
                if _is_real_sotu(normalized):
                    if normalized not in seen:
                        seen.add(normalized)
                        urls.append(normalized)

    return urls


def parse_taxonomy_pagination(html: str) -> list[str]:
    """Extract pagination page URLs containing '?page=' from pager navigation.

    Parameters
    - html (str): The HTML content of the taxonomy page.

    Returns
    - list[str]: A list of pagination page URLs.
    """
    parser = LexborHTMLParser(html)
    page_urls: list[str] = []
    seen: set[str] = set()

    for a in parser.css("a"):
        href = a.attributes.get("href")
        if href and "?page=" in href:
            normalized = normalize_url(href)
            if normalized not in seen:
                seen.add(normalized)
                page_urls.append(normalized)

    return page_urls


def parse_guidebook_table(html: str) -> list[str]:
    """Extract historical SOTU URLs from the main guidebook grid table.

    Processes Table 0 (cells in columns 2 to 11 of the 12-cell rows)
    and all links from Table 1.

    Parameters
    - html (str): The HTML content of the guidebook page.

    Returns
    - list[str]: A list of SOTU document URLs.
    """
    parser = LexborHTMLParser(html)
    urls: list[str] = []
    seen: set[str] = set()

    tables = parser.css("table")
    if not tables:
        return urls

    # Process Table 0
    t0_rows = tables[0].css("tr")
    for row in t0_rows:
        cells = row.css("td, th")
        if len(cells) == 12:
            # Columns 2 through 11 represent speech and written message columns
            for cell in cells[2:12]:
                for a in cell.css("a"):
                    href = a.attributes.get("href")
                    if href and not href.startswith("#"):
                        normalized = normalize_url(href)
                        is_sotu = (
                            "/documents/" in normalized
                            or "presidency.ucsb.edu" in normalized
                        )
                        if is_sotu and _is_real_sotu(normalized):
                            if normalized not in seen:
                                seen.add(normalized)
                                urls.append(normalized)

    # Process Table 1 (multi-topic State of the Union messages)
    if len(tables) > 1:
        t1_rows = tables[1].css("tr")
        for row in t1_rows:
            for a in row.css("a"):
                href = a.attributes.get("href")
                if href and not href.startswith("#"):
                    normalized = normalize_url(href)
                    is_sotu = (
                        "/documents/" in normalized
                        or "presidency.ucsb.edu" in normalized
                    )
                    if is_sotu and _is_real_sotu(normalized):
                        if normalized not in seen:
                            seen.add(normalized)
                            urls.append(normalized)

    return urls
