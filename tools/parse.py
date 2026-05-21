"""Parser tool for SOTU HTML documents."""

import re

from selectolax.lexbor import LexborHTMLParser


def clean_text(text: str) -> str:
    """Normalize whitespace and strip HTML anomalies.

    Parameters
    - text (str): Text to clean.

    Returns
    - str: Cleaned text.
    """
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def parse_speech_html(html: str) -> str:
    """Parse SOTU speech HTML to clean plain text.

    Preserves paragraph breaks (\n\n) and strips formatting/metadata.

    Parameters
    - html (str): Raw HTML content.

    Returns
    - str: Cleaned speech text.
    """
    parser = LexborHTMLParser(html)
    container = parser.css_first(".field-docs-content")
    if not container:
        container = parser.css_first(".field-body, .node-answers-content, body")

    if not container:
        return ""

    paragraphs: list[str] = []
    p_tags = container.css("p")
    if p_tags:
        for p in p_tags:
            text = clean_text(p.text(deep=True))
            if text:
                paragraphs.append(text)
    else:
        # Fallback if no <p> tags are present
        text = clean_text(container.text(deep=True))
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]

    return "\n\n".join(paragraphs)
