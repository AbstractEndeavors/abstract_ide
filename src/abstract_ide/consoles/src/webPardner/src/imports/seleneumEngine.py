from .imports import *
from .emulatorConfig import *
from .politeFetcher import *
from .baseEngine import *

class SeleniumEngine(BaseEngine):
    DEFAULT_WINDOW_SIZES = [
        (1920, 1080), (1366, 768), (1440, 900), (1536, 864), (1280, 720)
    ]

    def __init__(self, cfg: EmulatorConfig):
        super().__init__(cfg)
        self.driver = None
        self.wait: Optional[WebDriverWait] = None
        self._init_driver()

    def _pick_proxy(self) -> Optional[str]:
        return random.choice(self.proxy_pool) if self.proxy_pool else self.cfg.proxy

    def _init_driver(self):
        options = Options()
        if self.cfg.headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument(f'--user-agent={self.user_agent}')
        width, height = random.choice(self.DEFAULT_WINDOW_SIZES)
        options.add_argument(f'--window-size={width},{height}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        proxy = self._pick_proxy()
        if proxy:
            options.add_argument(f'--proxy-server={proxy}')
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        # CDP: block heavy resources
        try:
            self.driver.execute_cdp_cmd("Page.enable", {})
            self.driver.execute_cdp_cmd("Network.enable", {})
            if self.cfg.disable_images:
                self.driver.execute_cdp_cmd("Network.setBlockedURLs", {
                    "urls": ["*.png","*.jpg","*.jpeg","*.gif","*.webp","*.svg","*.woff","*.woff2","*.ttf","*.otf","*.avi","*.mp4","*.mp3","*.mov"]
                })
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": self.user_agent})
        except Exception:
            pass
        self.driver.implicitly_wait(5)
        self.wait = WebDriverWait(self.driver, self.cfg.timeout)

    def scrape(self, url: str, wait_for: Optional[str], selectors: Dict[str, str]) -> Dict[str, Any]:
        if not self.polite.allowed(url):
            return {'url': url, 'status': 'skipped_by_robots'}
        self.polite.sleep()
        try:
            self.driver.get(url)
            # wait for doc complete + brief idle
            self.driver.execute_script("""
                return new Promise(resolve=>{
                    const check=()=>{ if(document.readyState==='complete') resolve(); else setTimeout(check,100); };
                    check();
                });
            """)
            time.sleep(0.6)
            if wait_for:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_for)))
            # tiny human-ish activity
            self.driver.execute_script("document.body.dispatchEvent(new Event('mousemove'));")
            time.sleep(0.2)
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.title.string.strip() if soup.title else None
            data = self._extract(soup, selectors) if selectors else {}
            return {'url': url, 'status': 'success', 'title': title, 'data': data, 'soup': soup, 'html': html, 'cookies': self.driver.get_cookies()}
        except Exception as e:
            logger.warning(f"[Selenium] Failed {url}: {e}")
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
            self.driver.get(url)
            time.sleep(0.5)
            self.driver.save_screenshot(out_path)
        except Exception:
            pass

    def quit(self):
        try:
            if self.driver: self.driver.quit()
        except Exception:
            pass
        self.driver = None
