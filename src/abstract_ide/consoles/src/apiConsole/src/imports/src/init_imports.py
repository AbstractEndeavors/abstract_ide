from __future__ import annotations
import logging,requests,json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin
from contextlib import suppress
from urllib.parse import urlencode
from abstract_utilities import initFuncs
from typing import *
from abstract_apis import *  # getRequest, postRequest, MIME_TYPES
from abstract_gui.QT6 import *
from abstract_gui import startConsole
from PySide6.QtCore import QUrl, QUrlQuery, QByteArray, QObject, QThread, Signal as pyqtSignal, QSignalBlocker
from PySide6.QtNetwork import QNetworkRequest, QNetworkAccessManager
from PySide6.QtCore import QObject, QThread, Signal as pyqtSignal, Qt
from PySide6.QtWidgets import (
    QComboBox, QListView, QSizePolicy, QMessageBox, QTextEdit,QVBoxLayout,
    QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QTableWidget,
    QAbstractItemView
)
try:
    from PyQt6.sip import isdeleted  # PyQt6-safe deleted check
except Exception:
    def isdeleted(obj):  # fallback
        try:
            _ = obj.metaObject()
            return False
        except Exception:
            return True
        
