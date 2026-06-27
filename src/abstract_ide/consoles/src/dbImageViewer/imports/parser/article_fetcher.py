from .article_query import ArticleQuery
from ..src.utils import (
    get_user_page,
    get_soup,
    get_articles,
    is_getable,
    USER
)

def fetch_articles(query: ArticleQuery):
    if query.raw_url:
        soup = get_soup(query.raw_url)
        return get_articles(soup)

    user = query.user or USER
    page = query.page

    soup = get_soup(get_user_page(user=user, page=str(page)))
    
    articles = get_articles(soup)

    if query.media_type or query.required_tags:
        return [a for a in articles if is_getable(a)]

    return articles
