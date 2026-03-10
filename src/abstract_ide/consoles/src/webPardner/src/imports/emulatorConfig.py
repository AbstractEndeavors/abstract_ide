from .imports import *
@dataclass
class EmulatorConfig:
    engine: str = "Playwright"  # "Playwright" or "Selenium"
    headless: bool = True
    proxy: Optional[str] = None
    proxy_pool: Optional[List[str]] = None
    stealth_mode: bool = True
    disable_images: bool = True
    user_agent: Optional[str] = None
    timeout: int = 10
