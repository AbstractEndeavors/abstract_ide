from .imports import *
from .emulatorConfig import *
from .politeFetcher import *
class BaseEngine:
    DEFAULT_USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
    ]

    def __init__(self, cfg: EmulatorConfig):
        self.cfg = cfg
        self.user_agent = cfg.user_agent or random.choice(self.DEFAULT_USER_AGENTS)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        self.proxy_pool = cfg.proxy_pool or ([cfg.proxy] if cfg.proxy else [])
        if self.proxy_pool:
            picked = random.choice(self.proxy_pool)
            self.session.proxies = {'http': picked, 'https': picked}
        self.polite = PoliteFetcher(self.session, self.user_agent)

    # interface
    def scrape(self, url: str, wait_for: Optional[str], selectors: Dict[str, str]) -> Dict[str, Any]:
        raise NotImplementedError

    def crawl(self, start_url: str, selectors: Dict[str,str], next_selector: Optional[str], same_host_only: bool, max_pages: int, max_depth: int) -> Dict[str, Any]:
        seen, out, q = set(), [], deque([(start_url, 0)])
        base_host = urlparse(start_url).netloc
        # try sitemaps
        for u in self.discover_sitemap_urls(start_url):
            q.append((u, 0))

        while q and len(out) < max_pages:
            url, depth = q.popleft()
            if url in seen or depth > max_depth:
                continue
            seen.add(url)
            if not self.polite.allowed(url):
                out.append({'url': url, 'status': 'skipped_by_robots'})
                continue
            self.polite.sleep()

            res = self.scrape(url, wait_for=None, selectors=selectors)
            # carry minimal result to output; if selenium/playwright, we can attach 'html' too
            entry = {
                'url': url,
                'status': res.get('status'),
                'title': res.get('title'),
                'data': res.get('data'),
            }
            if 'html' in res:
                entry['html'] = res['html']
            out.append(entry)

            if res.get('status') in ('success','fallback_success'):
                soup: BeautifulSoup = res['soup']
                # pagination
                if next_selector:
                    nxt = soup.select_one(next_selector)
                    if nxt and nxt.get('href'):
                        q.append((urljoin(url, nxt['href']), depth+1))
                # same-host breadth
                for a in soup.select('a[href]'):
                    href = urljoin(url, a['href'])
                    if same_host_only and urlparse(href).netloc != base_host:
                        continue
                    if href.startswith(('mailto:', 'javascript:')):
                        continue
                    if href not in seen:
                        q.append((href, depth+1))

            # politeness between pages
            self.polite.sleep(0.5, 1.6)

        return {'status': 'ok', 'pages': out}

    def discover_sitemap_urls(self, root: str) -> List[str]:
        base = urlparse(root)._replace(path='', params='', query='', fragment='').geturl()
        urls = [urljoin(base, p) for p in ('/sitemap.xml', '/sitemap_index.xml')]
        out = []
        for u in urls:
            try:
                r = self.session.get(u, timeout=6)
                if r.ok and ('<urlset' in r.text or '<sitemapindex' in r.text):
                    soup = BeautifulSoup(r.text, 'xml')
                    for loc in soup.select('url > loc, sitemap > loc'):
                        out.append(loc.text.strip())
            except Exception:
                pass
        return out

    def quit(self):
        pass

    # helpers
    @staticmethod
    def _extract(soup: BeautifulSoup, selectors: Dict[str,str]) -> Dict[str, Any]:
        data = {}
        for key, selector in selectors.items():
            els = soup.select(selector)
            data[key] = [el.get_text(strip=True) for el in els] if els else None
        return data
