# media_autofill.py
from __future__ import annotations
import re, mimetypes, json, hashlib, time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, unquote
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import sys
import logging
import time
import random
import json
import csv
import re
from typing import Optional, Dict, List, Any, Callable, Tuple
from dataclasses import dataclass
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ---------- PyQt6 ----------
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QCheckBox, QComboBox, QLabel,
    QFileDialog, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# ---------- Selenium (optional engine) ----------
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# ---------- Requests / parsing ----------
from bs4 import BeautifulSoup
import requests
from urllib.robotparser import RobotFileParser

# ---------- Playwright (optional engine) ----------
try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
