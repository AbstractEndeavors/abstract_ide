from .imports import *
# ---------- Selenium (optional engine) ----------
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
# ---------- Playwright (optional engine) ----------
try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
