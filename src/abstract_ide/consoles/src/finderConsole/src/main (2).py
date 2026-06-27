#!/usr/bin/env python3
"""
TDD Manifest Viewer - PyQt5 GUI
Interactive desktop application for viewing and managing image manifests.
"""
from .imports import *
from .diffParserTab import diffParserTab
from .directoryMapTab import directoryMapTab
from .extractImportsTab import extractImportsTab
from .finderTab import finderTab
from .collectFilesTab import collectFilesTab
from .scaffolder import Scaffolder

# ═══════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════

@dataclass
class AppConfig:
    """Application configuration"""
    root: str = "/srv/media/thedailydialectics"
    manifest_dir: str = "/srv/media/thedailydialectics/manifests"
    manifest_file: str = "complete_manifest.json"
    auto_refresh: bool = False
    show_missing_only: bool = False
    show_without_metadata_only: bool = False
    
    def manifest_path(self) -> str:
        return os.path.join(self.manifest_dir, self.manifest_file)


# ═══════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════

@dataclass
class DirectoryStatus:
    """Status of a single image directory"""
    canonical_path: str
    filesystem_path: Optional[str]
    exists: bool
    has_info_json: bool
    has_index_html: bool
    has_resized_webp: bool
    total_files: int
    file_list: List[str]
    has_complete_metadata: bool
    missing_metadata_fields: List[str]
    used_by_pages: List[str]
    usage_count: int
    title: Optional[str]
    alt: Optional[str]
    keywords: Optional[List[str]]
    dimensions: Optional[Dict[str, int]]
    
    def status_color(self) -> QColor:
        """Get status color for UI"""
        if not self.exists:
            return QColor(220, 100, 100)  # Red
        elif self.has_complete_metadata:
            return QColor(100, 220, 100)  # Green
        else:
            return QColor(220, 200, 100)  # Yellow
    
    def status_icon(self) -> str:
        """Get status icon"""
        if not self.exists:
            return "❌"
        elif self.has_complete_metadata:
            return "✅"
        else:
            return "⚠️"
    
    def status_text(self) -> str:
        """Get status description"""
        if not self.exists:
            return "Missing"
        elif self.has_complete_metadata:
            return "Complete"
        else:
            return f"Incomplete ({len(self.missing_metadata_fields)} fields missing)"


@dataclass
class ManifestStats:
    """Statistics for the manifest"""
    total_directories: int = 0
    existing_directories: int = 0
    missing_directories: int = 0
    with_info_json: int = 0
    without_info_json: int = 0
    with_index_html: int = 0
    with_complete_metadata: int = 0
    shared_directories: int = 0


# ═══════════════════════════════════════════════════════════
# MANIFEST LOADER (Background Thread)
# ═══════════════════════════════════════════════════════════

class ManifestLoader(QThread):
    """Background thread for loading manifest"""
    
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict, dict, object)
    error = pyqtSignal(str)
    
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
    
    def run(self):
        """Load manifest in background"""
        try:
            # Load manifest file
            self.progress.emit(10, "Loading manifest file...")
            manifest_path = self.config.manifest_path()
            
            if not os.path.exists(manifest_path):
                self.error.emit(f"Manifest not found: {manifest_path}")
                return
            
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            self.progress.emit(30, "Building directory statuses...")
            statuses = self._build_statuses(manifest)
            
            self.progress.emit(70, "Calculating statistics...")
            stats = self._calculate_stats(statuses)
            
            self.progress.emit(100, "Complete!")
            self.finished.emit(manifest, statuses, stats)
            
        except Exception as e:
            self.error.emit(f"Error loading manifest: {e}")
    
    def _build_statuses(self, manifest: dict) -> Dict[str, DirectoryStatus]:
        """Build directory status objects"""
        statuses = {}
        path_usage = manifest.get('path_usage', {})
        
        for page in manifest.get('pages', []):
            for ref in page.get('image_refs', []):
                canonical = ref.get('canonical_path')
                if not canonical or canonical in statuses:
                    continue
                
                metadata = ref.get('metadata', {})
                dir_contents = ref.get('directory_contents', {})
                
                missing_fields = []
                if metadata:
                    if not metadata.get('alt'):
                        missing_fields.append('alt')
                    if not metadata.get('title'):
                        missing_fields.append('title')
                    if not metadata.get('keywords'):
                        missing_fields.append('keywords')
                    if not metadata.get('dimensions'):
                        missing_fields.append('dimensions')
                
                file_list = []
                if dir_contents:
                    file_list = (
                        dir_contents.get('html_files', []) +
                        dir_contents.get('json_files', []) +
                        dir_contents.get('image_files', []) +
                        dir_contents.get('other_files', [])
                    )
                
                status = DirectoryStatus(
                    canonical_path=canonical,
                    filesystem_path=ref.get('resolved_dir'),
                    exists=ref.get('exists', False),
                    has_info_json=metadata.get('has_info_json', False) if metadata else False,
                    has_index_html=dir_contents.get('has_index_html', False) if dir_contents else False,
                    has_resized_webp=dir_contents.get('has_resized_webp', False) if dir_contents else False,
                    total_files=dir_contents.get('total_files', 0) if dir_contents else 0,
                    file_list=sorted(file_list),
                    has_complete_metadata=len(missing_fields) == 0 and metadata and metadata.get('has_info_json'),
                    missing_metadata_fields=missing_fields,
                    used_by_pages=path_usage.get(canonical, []),
                    usage_count=len(path_usage.get(canonical, [])),
                    title=metadata.get('title') if metadata else None,
                    alt=metadata.get('alt') if metadata else None,
                    keywords=metadata.get('keywords') if metadata else None,
                    dimensions=metadata.get('dimensions') if metadata else None,
                )
                
                statuses[canonical] = status
        
        return statuses
    
    def _calculate_stats(self, statuses: Dict[str, DirectoryStatus]) -> ManifestStats:
        """Calculate statistics"""
        return ManifestStats(
            total_directories=len(statuses),
            existing_directories=sum(1 for s in statuses.values() if s.exists),
            missing_directories=sum(1 for s in statuses.values() if not s.exists),
            with_info_json=sum(1 for s in statuses.values() if s.has_info_json),
            without_info_json=sum(1 for s in statuses.values() if not s.has_info_json),
            with_index_html=sum(1 for s in statuses.values() if s.has_index_html),
            with_complete_metadata=sum(1 for s in statuses.values() if s.has_complete_metadata),
            shared_directories=sum(1 for s in statuses.values() if s.usage_count > 1),
        )


# ═══════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════

class finderConsole(ConsoleBase):
    def __init__(self, *, bus=None, parent=None):
        super().__init__(bus=bus, parent=parent)
        inner = QTabWidget()
        self.layout().addWidget(inner)
    
        # all content tabs share THIS console’s bus
        inner.addTab(finderTab(self.bus),         "Find Content")
        inner.addTab(directoryMapTab(self.bus),   "Directory Map")
        #inner.addTab(extractImportsTab(self.bus), "Extract Python Imports")
        inner.addTab(diffParserTab(self.bus),     "Diff (Repo)")
        inner.addTab(Scaffolder(self.bus),     "scaffolder")

    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.config = AppConfig()
        
        # Data
        self.manifest = {}
        self.statuses: Dict[str, DirectoryStatus] = {}
        self.stats = ManifestStats()
        self.current_filter = "all"
        
        # UI
        self.init_ui()
        
        # Auto-load manifest
        self.load_manifest()
    
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("TDD Manifest Viewer")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Menu bar
        self.create_menu_bar()
        
        # Toolbar
        toolbar = self.create_toolbar()
        layout.addLayout(toolbar)
        
        # Main content (splitter)
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Tree view
        tree_widget = self.create_tree_view()
        splitter.addWidget(tree_widget)
        
        # Right: Details panel
        details_widget = self.create_details_panel()
        splitter.addWidget(details_widget)
        
        splitter.setSizes([600, 800])
        layout.addWidget(splitter)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progress_bar)
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Manifest...", self)
        open_action.triggered.connect(self.open_manifest_dialog)
        file_menu.addAction(open_action)
        
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.load_manifest)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        expand_action = QAction("Expand All", self)
        expand_action.triggered.connect(lambda: self.tree.expandAll())
        view_menu.addAction(expand_action)
        
        collapse_action = QAction("Collapse All", self)
        collapse_action.triggered.connect(lambda: self.tree.collapseAll())
        view_menu.addAction(collapse_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        stats_action = QAction("Show Statistics", self)
        stats_action.triggered.connect(self.show_statistics_dialog)
        tools_menu.addAction(stats_action)
    
    def create_toolbar(self) -> QHBoxLayout:
        """Create toolbar"""
        toolbar = QHBoxLayout()
        
        # Search
        toolbar.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter path or keyword...")
        self.search_input.textChanged.connect(self.filter_tree)
        toolbar.addWidget(self.search_input)
        
        # Filter
        toolbar.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Directories",
            "Missing Only",
            "Without Metadata",
            "Without info.json",
            "Shared (Multi-use)",
            "Complete Only"
        ])
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        toolbar.addWidget(self.filter_combo)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_manifest)
        toolbar.addWidget(refresh_btn)
        
        toolbar.addStretch()
        
        return toolbar
    
    def create_tree_view(self) -> QWidget:
        """Create tree view widget"""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Stats summary
        self.stats_label = QLabel()
        self.update_stats_label()
        layout.addWidget(self.stats_label)
        
        # Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Directory", "Status", "Files", "Usage"])
        self.tree.setColumnWidth(0, 400)
        self.tree.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.tree)
        
        return container
    
    def create_details_panel(self) -> QWidget:
        """Create details panel"""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Title
        self.details_title = QLabel("Select a directory to view details")
        self.details_title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(self.details_title)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Overview tab
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        self.overview_text = QTextEdit()
        self.overview_text.setReadOnly(True)
        overview_layout.addWidget(self.overview_text)
        self.tabs.addTab(overview_tab, "Overview")
        
        # Files tab
        files_tab = QWidget()
        files_layout = QVBoxLayout(files_tab)
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(2)
        self.files_table.setHorizontalHeaderLabels(["File", "Type"])
        self.files_table.horizontalHeader().setStretchLastSection(True)
        files_layout.addWidget(self.files_table)
        self.tabs.addTab(files_tab, "Files")
        
        # Metadata tab
        metadata_tab = QWidget()
        metadata_layout = QVBoxLayout(metadata_tab)
        self.metadata_text = QTextEdit()
        self.metadata_text.setReadOnly(True)
        metadata_layout.addWidget(self.metadata_text)
        self.tabs.addTab(metadata_tab, "Metadata")
        
        # Usage tab
        usage_tab = QWidget()
        usage_layout = QVBoxLayout(usage_tab)
        self.usage_table = QTableWidget()
        self.usage_table.setColumnCount(1)
        self.usage_table.setHorizontalHeaderLabels(["Page Path"])
        self.usage_table.horizontalHeader().setStretchLastSection(True)
        usage_layout.addWidget(self.usage_table)
        self.tabs.addTab(usage_tab, "Usage")
        
        layout.addWidget(self.tabs)
        
        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout(actions_group)
        
        self.open_dir_btn = QPushButton("Open Directory")
        self.open_dir_btn.clicked.connect(self.open_directory)
        self.open_dir_btn.setEnabled(False)
        actions_layout.addWidget(self.open_dir_btn)
        
        self.create_info_btn = QPushButton("Create info.json")
        self.create_info_btn.clicked.connect(self.create_info_json)
        self.create_info_btn.setEnabled(False)
        actions_layout.addWidget(self.create_info_btn)
        
        actions_layout.addStretch()
        
        layout.addWidget(actions_group)
        
        return container
    
    def update_stats_label(self):
        """Update statistics label"""
        text = f"""
        <b>Statistics:</b> 
        Total: {self.stats.total_directories} | 
        Existing: {self.stats.existing_directories} | 
        Missing: {self.stats.missing_directories} | 
        With info.json: {self.stats.with_info_json} | 
        Complete: {self.stats.with_complete_metadata}
        """
        self.stats_label.setText(text)
    
    def load_manifest(self):
        """Load manifest in background"""
        self.statusBar.showMessage("Loading manifest...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Create loader thread
        self.loader = ManifestLoader(self.config)
        self.loader.progress.connect(self.on_load_progress)
        self.loader.finished.connect(self.on_load_finished)
        self.loader.error.connect(self.on_load_error)
        self.loader.start()
    
    def on_load_progress(self, value: int, message: str):
        """Handle load progress"""
        self.progress_bar.setValue(value)
        self.statusBar.showMessage(message)
    
    def on_load_finished(self, manifest: dict, statuses: Dict[str, DirectoryStatus], stats: ManifestStats):
        """Handle load completion"""
        self.manifest = manifest
        self.statuses = statuses
        self.stats = stats
        
        self.progress_bar.setVisible(False)
        self.statusBar.showMessage(f"Loaded {len(statuses)} directories", 3000)
        
        self.update_stats_label()
        self.populate_tree()
    
    def on_load_error(self, error: str):
        """Handle load error"""
        self.progress_bar.setVisible(False)
        self.statusBar.showMessage("Error loading manifest", 3000)
        QMessageBox.critical(self, "Error", error)
    
    def populate_tree(self):
        """Populate tree view"""
        self.tree.clear()
        
        # Build tree structure
        root_items = {}  # path -> QTreeWidgetItem
        
        for canonical, status in sorted(self.statuses.items()):
            # Apply filters
            if not self.matches_filter(status):
                continue
            
            # Parse path
            parts = [p for p in canonical.split('/') if p]
            if not parts:
                continue
            
            # Build tree path
            current_path = ""
            parent = None
            
            for i, part in enumerate(parts):
                current_path = current_path + "/" + part if current_path else "/" + part
                
                # Create item if doesn't exist
                if current_path not in root_items:
                    if parent is None:
                        item = QTreeWidgetItem(self.tree)
                    else:
                        item = QTreeWidgetItem(parent)
                    
                    item.setText(0, part)
                    item.setData(0, Qt.UserRole, current_path)
                    root_items[current_path] = item
                    
                    # If this is the final directory, set status
                    if i == len(parts) - 1:
                        item.setText(1, status.status_icon() + " " + status.status_text())
                        item.setText(2, str(status.total_files))
                        item.setText(3, str(status.usage_count) + (" pages" if status.usage_count > 1 else " page"))
                        item.setBackground(1, status.status_color())
                        item.setData(0, Qt.UserRole + 1, canonical)  # Store canonical path
                
                parent = root_items[current_path]
    
    def matches_filter(self, status: DirectoryStatus) -> bool:
        """Check if status matches current filter"""
        filter_text = self.filter_combo.currentText()
        
        if filter_text == "All Directories":
            return True
        elif filter_text == "Missing Only":
            return not status.exists
        elif filter_text == "Without Metadata":
            return not status.has_complete_metadata
        elif filter_text == "Without info.json":
            return not status.has_info_json
        elif filter_text == "Shared (Multi-use)":
            return status.usage_count > 1
        elif filter_text == "Complete Only":
            return status.has_complete_metadata
        
        return True
    
    def filter_tree(self, text: str):
        """Filter tree by search text"""
        if not text:
            # Show all
            self.populate_tree()
            return
        
        # Hide all items
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            item.setHidden(True)
            iterator += 1
        
        # Show matching items and their parents
        text_lower = text.lower()
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if text_lower in item.text(0).lower():
                # Show this item and all parents
                current = item
                while current:
                    current.setHidden(False)
                    current.setExpanded(True)
                    current = current.parent()
            iterator += 1
    
    def apply_filter(self, filter_text: str):
        """Apply filter"""
        self.populate_tree()
    
    def on_selection_changed(self):
        """Handle tree selection change"""
        items = self.tree.selectedItems()
        if not items:
            return
        
        item = items[0]
        canonical = item.data(0, Qt.UserRole + 1)
        
        if canonical and canonical in self.statuses:
            self.show_details(self.statuses[canonical])
        else:
            self.clear_details()
    
    def show_details(self, status: DirectoryStatus):
        """Show directory details"""
        self.details_title.setText(status.canonical_path)
        
        # Overview
        overview = f"""
<h3>Status: {status.status_icon()} {status.status_text()}</h3>

<p><b>Canonical Path:</b> {status.canonical_path}</p>
<p><b>Filesystem Path:</b> {status.filesystem_path or 'N/A'}</p>
<p><b>Exists:</b> {'Yes' if status.exists else 'No'}</p>
<p><b>Total Files:</b> {status.total_files}</p>

<h4>Features:</h4>
<ul>
<li>{'✅' if status.has_info_json else '❌'} info.json</li>
<li>{'✅' if status.has_index_html else '❌'} index.html</li>
<li>{'✅' if status.has_resized_webp else '❌'} resized.webp</li>
</ul>

<h4>Usage:</h4>
<p>Used by <b>{status.usage_count}</b> page(s)</p>
"""
        
        if status.missing_metadata_fields:
            overview += f"""
<h4 style="color: #cc6600;">Missing Metadata Fields:</h4>
<p>{', '.join(status.missing_metadata_fields)}</p>
"""
        
        self.overview_text.setHtml(overview)
        
        # Files table
        self.files_table.setRowCount(len(status.file_list))
        for i, filename in enumerate(status.file_list):
            self.files_table.setItem(i, 0, QTableWidgetItem(filename))
            ext = os.path.splitext(filename)[1]
            file_type = {
                '.html': 'HTML',
                '.json': 'JSON',
                '.webp': 'Image (WebP)',
                '.jpg': 'Image (JPEG)',
                '.png': 'Image (PNG)',
            }.get(ext, 'Other')
            self.files_table.setItem(i, 1, QTableWidgetItem(file_type))
        
        # Metadata
        metadata_html = "<h3>Metadata</h3>"
        if status.title:
            metadata_html += f"<p><b>Title:</b> {status.title}</p>"
        if status.alt:
            metadata_html += f"<p><b>Alt Text:</b> {status.alt}</p>"
        if status.keywords:
            metadata_html += f"<p><b>Keywords:</b> {', '.join(status.keywords)}</p>"
        if status.dimensions:
            metadata_html += f"<p><b>Dimensions:</b> {status.dimensions['width']} × {status.dimensions['height']}</p>"
        
        if not any([status.title, status.alt, status.keywords, status.dimensions]):
            metadata_html += "<p><i>No metadata available</i></p>"
        
        self.metadata_text.setHtml(metadata_html)
        
        # Usage table
        self.usage_table.setRowCount(len(status.used_by_pages))
        for i, page_path in enumerate(status.used_by_pages):
            page_rel = page_path.split('/pages/')[-1] if '/pages/' in page_path else page_path
            self.usage_table.setItem(i, 0, QTableWidgetItem(page_rel))
        
        # Enable action buttons
        self.open_dir_btn.setEnabled(status.exists)
        self.create_info_btn.setEnabled(status.exists and not status.has_info_json)
    
    def clear_details(self):
        """Clear details panel"""
        self.details_title.setText("Select a directory to view details")
        self.overview_text.clear()
        self.files_table.setRowCount(0)
        self.metadata_text.clear()
        self.usage_table.setRowCount(0)
        self.open_dir_btn.setEnabled(False)
        self.create_info_btn.setEnabled(False)
    
    def open_directory(self):
        """Open selected directory in file manager"""
        items = self.tree.selectedItems()
        if not items:
            return
        
        item = items[0]
        canonical = item.data(0, Qt.UserRole + 1)
        
        if canonical and canonical in self.statuses:
            status = self.statuses[canonical]
            if status.filesystem_path:
                os.system(f'xdg-open "{status.filesystem_path}" &')
    
    def create_info_json(self):
        """Create info.json template for selected directory"""
        items = self.tree.selectedItems()
        if not items:
            return
        
        item = items[0]
        canonical = item.data(0, Qt.UserRole + 1)
        
        if canonical and canonical in self.statuses:
            status = self.statuses[canonical]
            if status.filesystem_path and not status.has_info_json:
                info_path = os.path.join(status.filesystem_path, 'info.json')
                
                template = {
                    "alt": "",
                    "caption": "",
                    "keywords_str": "",
                    "filename": "",
                    "ext": "webp",
                    "title": "",
                    "dimensions": {"width": 0, "height": 0},
                    "file_size": "",
                    "license": "CC BY-SA 4.0",
                    "attribution": "Created by The Daily Dialectics for educational purposes"
                }
                
                with open(info_path, 'w') as f:
                    json.dump(template, f, indent=4)
                
                QMessageBox.information(self, "Success", f"Created: {info_path}")
                self.load_manifest()  # Refresh
    
    def open_manifest_dialog(self):
        """Open manifest file dialog"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Manifest",
            self.config.manifest_dir,
            "JSON Files (*.json)"
        )
        
        if filename:
            self.config.manifest_file = os.path.basename(filename)
            self.config.manifest_dir = os.path.dirname(filename)
            self.load_manifest()
    
    def show_statistics_dialog(self):
        """Show statistics dialog"""
        stats_text = f"""
<h2>Manifest Statistics</h2>

<table>
<tr><td><b>Total Directories:</b></td><td>{self.stats.total_directories}</td></tr>
<tr><td><b>Existing:</b></td><td>{self.stats.existing_directories}</td></tr>
<tr><td><b>Missing:</b></td><td>{self.stats.missing_directories}</td></tr>
<tr><td><b>With info.json:</b></td><td>{self.stats.with_info_json}</td></tr>
<tr><td><b>Without info.json:</b></td><td>{self.stats.without_info_json}</td></tr>
<tr><td><b>With index.html:</b></td><td>{self.stats.with_index_html}</td></tr>
<tr><td><b>Complete Metadata:</b></td><td>{self.stats.with_complete_metadata}</td></tr>
<tr><td><b>Shared (Multi-use):</b></td><td>{self.stats.shared_directories}</td></tr>
</table>
"""
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Statistics")
        msg.setTextFormat(Qt.RichText)
        msg.setText(stats_text)
        msg.exec_()

