"""
Scaffolding Tool - PyQt6

A file scaffolding utility that:
1. Parses directory tree text (like `tree` output)
2. Creates the folder/file structure on disk
3. Allows clicking files to edit and save content

Design principles applied:
- Schemas over ad-hoc objects (dataclasses for tree nodes)
- Registries over globals (FileRegistry for state)
- Explicit environment wiring (Config dataclass)
- Queues for deferred operations where applicable
"""
from .imports import *
# =============================================================================
# MAIN WINDOW (Controller + View composition)
# =============================================================================
class Scaffolder(QMainWindow):
    """
    Main window wiring all components together.
    Explicit dependency injection, no hidden state.
    """
    def __init__(
        self,
        config: Config,
        registry: FileRegistry=FileRegistry,
        parser: TreeParser=TreeParser,
        builder: ScaffoldBuilder=ScaffoldBuilder,
    ) -> None:
        super().__init__()
        initFuncs(self)
        self.config = config
        self.registry = registry
        self.parser = parser
        self.builder = builder

        self._current_file: Optional[Path] = None
        self._setup_ui()
        self._connect_signals()
    def start():
        startConsole(Scaffolder)




