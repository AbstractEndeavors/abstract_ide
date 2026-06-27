from .constants import *
from .soupManager import get_soup,BeautifulSoup
def get_user(part_url,user):
    return f"{part_url}/user/{user}"
def get_uploads(part_url):
    return f"{part_url}/uploads"
def get_page(part_url,page):
    return f"{part_url}/page/{page}"
def get_user_page(user,page):
    part_url = get_user(TARGET_DOMAIN,user)
    part_url = get_uploads(part_url)
    return get_page(part_url,page)
def get_soup(url):
    req_mgr = requests.get(url)
    return BeautifulSoup(req_mgr.text, "html.parser")
def get_articles(soup):
    return soup.find_all("article")
def get_all_tags(soup):
    return soup.find("div", {"class": "tags"})
def get_categoryurl(soup):
    return soup.find("a", {"class": "categoryurl"}).text
def get_as(soup):
    return soup.find_all("a")
def get_tags(soup):
    return [tag.text for tag in get_as(soup)]
def isFilteredTags(soup,fiters):
    for tag in get_tags(soup):
        if tag in fiters:
            return True
    return False
def get_kslinks(soup):
    kslink = soup.find("a", {"class": "kslinks"})
    if kslink:
        return kslink["href"]
def is_getable(article):
    if (get_categoryurl(article) == MEDIA_TYPE and isFilteredTags(article, FILTERS)):
        return get_kslinks(article)
def get_site_articles(i=None,user=None):
    user = user or USER
    i=i or 0
    url = get_user_page(user=user, page=str(i))
    soup = get_soup(url)
    return get_articles(soup)
def get_site_articles_from_url(i=None,user=None):
    user = user or USER
    i=i or 0
    url = get_user_page(user=user, page=str(i))
    soup = get_soup(url)
    return get_articles(soup)
def get_filtered_articles(url):
    soup = get_soup(url)
    return [article for article in get_articles(soup) if is_getable(article)]
def get_article_tags(article) -> list[str]:
    """Tags are the <a> elements inside the .tags div specifically."""
    tags_div = article.find("div", {"class": "tags"})
    if not tags_div:
        return []
    return [a.text.strip() for a in tags_div.find_all("a") if a.text.strip()]

def get_page_tags(page: int = 1, user: str = None) -> list[str]:
    """All unique tags across every article on a given page, sorted."""
    user = user or USER
    soup = get_soup(get_user_page(user=user, page=str(page)))
    seen = set()
    for article in get_articles(soup):
        seen.update(get_article_tags(article))
    return sorted(seen)

# fix the original -- was pulling ALL anchors, not just tag anchors
def isFilteredTags(article, filters) -> bool:
    return bool(set(get_article_tags(article)) & set(filters))
