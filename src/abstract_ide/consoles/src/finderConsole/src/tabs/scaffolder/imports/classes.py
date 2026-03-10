from .src import *
from .dataclasses import *

# =============================================================================
# REGISTRY
# =============================================================================


class FileRegistry:
    """
    Central registry for file state.
    Avoids scattered globals; all file state lives here.
    """

    def __init__(self) -> None:
        self._entries: dict[Path, FileEntry] = {}
        self._listeners: list[Callable[[Path, FileEntry], None]] = []

    def register(self, relative_path: Path, absolute_path: Path) -> FileEntry:
        entry = FileEntry(
            relative_path=relative_path,
            absolute_path=absolute_path,
            exists_on_disk=absolute_path.exists(),
        )
        if entry.exists_on_disk and absolute_path.is_file():
            try:
                entry.content = absolute_path.read_text(encoding="utf-8")
            except Exception:
                entry.content = ""
        self._entries[relative_path] = entry
        return entry

    def get(self, relative_path: Path) -> Optional[FileEntry]:
        return self._entries.get(relative_path)

    def update_content(self, relative_path: Path, content: str) -> None:
        entry = self._entries.get(relative_path)
        if entry:
            entry.content = content
            entry.is_dirty = True
            self._notify(relative_path, entry)

    def mark_saved(self, relative_path: Path) -> None:
        entry = self._entries.get(relative_path)
        if entry:
            entry.is_dirty = False
            entry.exists_on_disk = True

    def add_listener(self, callback: Callable[[Path, FileEntry], None]) -> None:
        self._listeners.append(callback)

    def _notify(self, path: Path, entry: FileEntry) -> None:
        for listener in self._listeners:
            listener(path, entry)

    def clear(self) -> None:
        self._entries.clear()

    def all_entries(self) -> dict[Path, FileEntry]:
        return dict(self._entries)


# =============================================================================
# PARSER
# =============================================================================


class TreeParser:
    """
    Parses `tree`-style text into TreeNode schema.
    Handles both actual tree output and simple indented lists.
    """

    TREE_CHARS = re.compile(r"[│├└─\s]+")

    def __init__(self, config: Config) -> None:
        self.config = config

    def parse(self, text: str) -> list[TreeNode]:
        lines = [ln for ln in text.strip().split("\n") if ln.strip()]
        if not lines:
            return []

        nodes: list[TreeNode] = []
        stack: list[tuple[int, TreeNode]] = []

        for line in lines:
            depth, name = self._parse_line(line)
            if not name:
                continue

            node_type = self._infer_type(name)
            node = TreeNode(name=name, node_type=node_type, depth=depth)

            while stack and stack[-1][0] >= depth:
                stack.pop()

            if stack:
                parent_node = stack[-1][1]
                node.parent = parent_node
                parent_node.children.append(node)
            else:
                nodes.append(node)

            if node.is_directory:
                stack.append((depth, node))

        return nodes

    def _parse_line(self, line: str) -> tuple[int, str]:
        stripped = self.TREE_CHARS.sub("", line).strip()
        if not stripped:
            return 0, ""

        raw_prefix = line[: line.find(stripped)] if stripped in line else ""
        depth = self._compute_depth(raw_prefix)

        return depth, stripped

    def _compute_depth(self, prefix: str) -> int:
        depth = 0
        for char in self.config.tree_indent_chars:
            depth += prefix.count(char)
        return depth

    def _infer_type(self, name: str) -> NodeType:
        if name.endswith("/"):
            return NodeType.DIRECTORY
        if "." in name and not name.startswith("."):
            return NodeType.FILE
        if any(name.endswith(ext) for ext in self.config.file_extensions):
            return NodeType.FILE
        if name in ("__init__", "Makefile", "Dockerfile", "README", "LICENSE"):
            return NodeType.FILE
        return NodeType.DIRECTORY


# =============================================================================
# SCAFFOLD BUILDER
# =============================================================================


class ScaffoldBuilder:
    """
    Creates directory/file structure on disk from TreeNodes.
    Uses a queue for ordered creation.
    """

    def __init__(self, registry: FileRegistry) -> None:
        self.registry = registry
        self._creation_queue: deque[tuple[Path, TreeNode]] = deque()

    def build(self, root: Path, nodes: list[TreeNode]) -> list[Path]:
        """
        Build scaffolding and return list of created file paths.
        """
        self.registry.clear()
        self._creation_queue.clear()
        created_files: list[Path] = []

        for node in nodes:
            self._enqueue(root, node, Path())

        while self._creation_queue:
            abs_path, node = self._creation_queue.popleft()
            rel_path = abs_path.relative_to(root)

            if node.is_directory:
                abs_path.mkdir(parents=True, exist_ok=True)
            else:
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                if not abs_path.exists():
                    abs_path.touch()
                self.registry.register(rel_path, abs_path)
                created_files.append(rel_path)

        return created_files

    def _enqueue(self, root: Path, node: TreeNode, current_rel: Path) -> None:
        node_rel = current_rel / node.name.rstrip("/")
        abs_path = root / node_rel

        self._creation_queue.append((abs_path, node))

        for child in node.children:
            self._enqueue(root, child, node_rel)


# =============================================================================
# QT WIDGETS
# =============================================================================


class TreeInputPanel(QGroupBox):
    """Panel for pasting tree structure text."""

    structure_submitted = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("1. Paste Structure", parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText(
            "Paste your tree structure here, e.g.:\n\n"
            "src/\n"
            "├── main.py\n"
            "├── models/\n"
            "│   └── user.py\n"
            "└── utils.py"
        )
        font = QFont("Courier New", 10)
        self.text_edit.setFont(font)
        self.text_edit.setMaximumHeight(200)

        self.create_btn = QPushButton("Create Scaffolding")
        self.create_btn.clicked.connect(self._on_create)

        layout.addWidget(self.text_edit)
        layout.addWidget(self.create_btn)

    def _on_create(self) -> None:
        text = self.text_edit.toPlainText()
        if text.strip():
            self.structure_submitted.emit(text)


class FileBrowserPanel(QGroupBox):
    """Tree view for browsing created files."""

    file_selected = pyqtSignal(Path)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("2. Browse Files", parent)
        self._path_map: dict[QStandardItem, Path] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.clicked.connect(self._on_item_clicked)

        self.model = QStandardItemModel()
        self.tree_view.setModel(self.model)

        layout.addWidget(self.tree_view)

    def populate(self, root_name: str, file_paths: list[Path]) -> None:
        self.model.clear()
        self._path_map.clear()

        root_item = QStandardItem(f"📁 {root_name}")
        root_item.setEditable(False)
        self.model.appendRow(root_item)

        dir_items: dict[Path, QStandardItem] = {Path(): root_item}

        sorted_paths = sorted(file_paths, key=lambda p: (len(p.parts), str(p)))

        for file_path in sorted_paths:
            parent_path = file_path.parent
            self._ensure_dirs(dir_items, parent_path, root_item)

            parent_item = dir_items.get(parent_path, root_item)
            file_item = QStandardItem(f"📄 {file_path.name}")
            file_item.setEditable(False)
            self._path_map[file_item] = file_path
            parent_item.appendRow(file_item)

        self.tree_view.expandAll()

    def _ensure_dirs(
        self,
        dir_items: dict[Path, QStandardItem],
        path: Path,
        root_item: QStandardItem,
    ) -> None:
        if path == Path() or path in dir_items:
            return

        parts_to_create: list[Path] = []
        current = path
        while current != Path() and current not in dir_items:
            parts_to_create.append(current)
            current = current.parent

        for dir_path in reversed(parts_to_create):
            parent_item = dir_items.get(dir_path.parent, root_item)
            dir_item = QStandardItem(f"📁 {dir_path.name}")
            dir_item.setEditable(False)
            parent_item.appendRow(dir_item)
            dir_items[dir_path] = dir_item

    def _on_item_clicked(self, index: QModelIndex) -> None:
        item = self.model.itemFromIndex(index)
        if item and item in self._path_map:
            self.file_selected.emit(self._path_map[item])


class EditorPanel(QGroupBox):
    """Editor panel for file content."""

    content_changed = pyqtSignal(str)
    save_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("3. Edit & Save", parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("font-weight: bold; color: #666;")

        self.text_edit = QPlainTextEdit()
        self.text_edit.setEnabled(False)
        font = QFont("Courier New", 10)
        self.text_edit.setFont(font)
        self.text_edit.textChanged.connect(self._on_text_changed)

        self.save_btn = QPushButton("Save File (Ctrl+S)")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_requested.emit)

        layout.addWidget(self.file_label)
        layout.addWidget(self.text_edit, stretch=1)
        layout.addWidget(self.save_btn)

    def set_file(self, path: Path, content: str) -> None:
        self.file_label.setText(str(path))
        self.text_edit.setEnabled(True)
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(content)
        self.text_edit.blockSignals(False)
        self.save_btn.setEnabled(True)

    def get_content(self) -> str:
        return self.text_edit.toPlainText()

    def clear(self) -> None:
        self.file_label.setText("No file selected")
        self.text_edit.clear()
        self.text_edit.setEnabled(False)
        self.save_btn.setEnabled(False)

    def _on_text_changed(self) -> None:
        self.content_changed.emit(self.text_edit.toPlainText())
