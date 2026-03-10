from bs4 import BeautifulSoup
from dataclasses import dataclass
from ..src import get_soup, get_filtered_articles,BASE_URL

@dataclass
class ArticleData:
    title: str
    image_url: str
    article_url: str
    author: str
    author_url: str
    size: str
    pages: str
    views: str
    download_url: str


def _file_id_from_url(url: str) -> str | None:
    try:
        return url.split(BASE_URL)[1].split('/')[0]
    except (IndexError, AttributeError):
        return None


def parse_articles(url, skip_downloaded: bool = False) -> list[ArticleData]:
    registry = None
    if skip_downloaded:
        from ..managers.db import DownloadRegistry
        from ..src.constants import DB_DSN
        registry = DownloadRegistry(DB_DSN)  # returns the same instance every time


    articles = []
    for art in get_filtered_articles(url):
        try:
            download_url = art.select_one(".kslinks")["href"]

            if registry:
                file_id = _file_id_from_url(download_url)
                if file_id and registry.has(file_id):
                    continue

            articles.append(ArticleData(
                title=art.select_one(".header-title").text.strip(),
                image_url=art.select_one("img")["src"],
                article_url=art.select_one("a")["href"],
                author=art.select_one(".author a").text,
                author_url=art.select_one(".author a")["href"],
                size=art.select_one(".size").text,
                pages=art.select_one(".pages").text,
                views=art.select_one(".views").text,
                download_url=download_url,
            ))
        except (TypeError, KeyError):
            continue

    return articles
