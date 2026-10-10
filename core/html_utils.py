"""Utilities for normalizing HTML values returned by FitNesse."""
import re


def clean_html_url(value: str) -> str:
    """
    Return the URL from a FitNesse-rendered value. FitNesse turns a URL (for example ${API_BASE_URL}) into a link, so
    "${API_BASE_URL}/users/1" arrives as <a href="https://host">https://host</a>/users/1; every link is replaced by
    its href and the text around it is kept.
    """
    value = str(value).strip()
    replaced = re.sub(r"""<a[^>]*href=["']([^"']+)["'][^>]*>[\s\S]*?</a>""", lambda m: m.group(1).strip(), value)
    if replaced != value:
        return re.sub(r"<[^<]+?>", "", replaced).strip()
    match = re.search(r"""href=["']([^"']+)["']""", value)
    if match:
        return match.group(1).strip()
    return re.sub(r"<[^<]+?>", "", value).strip()


def clean_html_text(value: str) -> str:
    """Return visible text from a FitNesse-rendered link or other HTML."""
    value = str(value).strip()
    value = re.sub(r"<a[^>]*>([\s\S]*?)</a>", r"\1", value)
    return re.sub(r"<[^<]+?>", "", value).strip()
