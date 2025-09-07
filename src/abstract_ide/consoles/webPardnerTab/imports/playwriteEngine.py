from .imports import *
from .emulatorConfig import *
from .politeFetcher import *
from .baseEngine import *
from .seleneumEngine import *
class PlaywrightEngine(BaseEngine):
    def __init__(self, cfg: EmulatorConfig):
        super().__init__(cfg)
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed. `pip install playwright` and `python -m playwright install chromium`.")
        self._pl = sync_playwright().start()
        self.browser: Optional[Browser] = None
        self.context = None
        self.page: Optional[Page] = None
        self._init_browser()

    @staticmethod
    def _parse_proxy(p: str) -> Dict[str, str]:
        # supports http://user:pass@host:port or http(s)://host:port
        u = urlparse(p)
        d = {"server": f"{u.scheme}://{u.hostname}:{u.port}"}
        if u.username or u.password:
            d["username"] = u.username or ""
            d["password"] = u.password or ""
        return d

    def _init_browser(self):
        launch_args = {
            "headless": self.cfg.headless,
            "args": [
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        }
        if self.proxy_pool:
            launch_args["proxy"] = self._parse_proxy(random.choice(self.proxy_pool))
        elif self.cfg.proxy:
            launch_args["proxy"] = self._parse_proxy(self.cfg.proxy)

        self.browser = self._pl.chromium.launch(**launch_args)
        ctx_args = {
            "user_agent": self.user_agent,
            "java_script_enabled": True,
            "viewport": {"width": 1280, "height": 800}
        }
        self.context = self.browser.new_context(**ctx_args)

        # Block heavy resources for speed
        if self.cfg.disable_images:
            def _route(route, request):
                if request.resource_type in ("image","font","media"):
                    return route.abort()
                return route.continue_()
            self.context.route("**/*", _route)

        self.page = self.context.new_page()

    def _goto(self, url: str, wait_for: Optional[str]):
        self.page.goto(url, wait_until="domcontentloaded", timeout=self.cfg.timeout * 1000)
        # brief network idle
        self.page.wait_for_timeout(600)
        if wait_for:
            self.page.wait_for_selector(wait_for, timeout=self.cfg.timeout * 1000)

    def scrape(self, url: str, wait_for: Optional[str], selectors: Dict[str, str]) -> Dict[str, Any]:
        if not self.polite.allowed(url):
            return {'url': url, 'status': 'skipped_by_robots'}
        self.polite.sleep()
        try:
            self._goto(url, wait_for)
            # light human-ish activity
            self.page.mouse.move(50, 50)
            self.page.wait_for_timeout(150)
            html = self.page.content()
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.title.string.strip() if soup.title else None
            data = self._extract(soup, selectors) if selectors else {}
            cookies = {c['name']: c['value'] for c in self.context.cookies()}
            return {'url': url, 'status': 'success', 'title': title, 'data': data, 'soup': soup, 'html': html, 'cookies': cookies}
        except Exception as e:
            logger.warning(f"[Playwright] Failed {url}: {e}")
            # fallback with requests
            try:
                r = self.session.get(url, timeout=self.cfg.timeout)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, 'html.parser')
                title = soup.title.string.strip() if soup.title else None
                data = self._extract(soup, selectors) if selectors else {}
                return {'url': url, 'status': 'fallback_success', 'title': title, 'data': data, 'soup': soup, 'cookies': r.cookies.get_dict()}
            except Exception as e2:
                return {'url': url, 'status': 'failed', 'error': str(e2)}

    def screenshot(self, url: str, out_path: str):
        try:
            self._goto(url, wait_for=None)
            self.page.screenshot(path=out_path, full_page=True)
        except Exception:
            pass

    def quit(self):
        try:
            if self.context: self.context.close()
        except Exception:
            pass
        try:
            if self.browser: self.browser.close()
        except Exception:
            pass
        try:
            if self._pl: self._pl.stop()
        except Exception:
            pass
        self.browser = None
        self.page = None
        self.context = None
