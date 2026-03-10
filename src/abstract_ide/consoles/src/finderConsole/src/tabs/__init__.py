from .imports import *
from .diffParserTab import diffParserTab
from .directoryMapTab import directoryMapTab
from .extractImportsTab import extractImportsTab
from .finderTab import finderTab
from .collectFilesTab import collectFilesTab
from .scaffolder import Scaffolder
from .main import finderConsole
from .mani import ManifestViewerWindow
def startFinderConsole():
    startConsole(finderConsole)
def startManifestViewerWindow():
    startConsole(ManifestViewerWindow)
