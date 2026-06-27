from .imports import *
from .emulatorConfig import *

class PoliteFetcher:
    def __init__(self, session: requests.Session, user_agent: str):
        self.session = session
        self.user_agent = user_agent
        self.parsers: Dict[str, RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        base = urlparse(url)._replace(path='', params='', query='', fragment='').geturl()
        if base not in self.parsers:
            rp = RobotFileParser()
            try:
                resp = self.session.get(urljoin(base, '/robots.txt'), timeout=6)
                rp.parse(resp.text.splitlines()) if resp.ok else rp.parse([])
            except Exception:
                rp.parse([])
            self.parsers[base] = rp
        return self.parsers[base].can_fetch(self.user_agent, url)

    @staticmethod
    def sleep(min_s=0.8, max_s=2.2):
        time.sleep(random.uniform(min_s, max_s))
