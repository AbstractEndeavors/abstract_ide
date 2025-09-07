from ..imports import *
import os
def init_ui(self):
    self.central_widget = QWidget()
    self.setCentralWidget(self.central_widget)
    self.layout = QVBoxLayout(self.central_widget)

    # Engine selector
    engine_row = QHBoxLayout()
    self.engine_combo = QComboBox()
    self.engine_combo.addItems(["Playwright", "Selenium"])
    engine_row.addWidget(QLabel("Engine:"))
    engine_row.addWidget(self.engine_combo)
    self.layout.addLayout(engine_row)

    # URL input
    self.url_label = QLabel("URL to Scrape:")
    self.url_input = QLineEdit()
    self.url_input.setPlaceholderText("https://example.com")
    self.layout.addWidget(self.url_label)
    self.layout.addWidget(self.url_input)

    # Wait-for selector
    self.wait_for_label = QLabel("Wait for Selector (optional):")
    self.wait_for_input = QLineEdit()
    self.wait_for_input.setPlaceholderText(".content")
    self.layout.addWidget(self.wait_for_label)
    self.layout.addWidget(self.wait_for_input)

    # Crawl options
    crawl_row = QHBoxLayout()
    self.next_selector_input = QLineEdit()
    self.next_selector_input.setPlaceholderText(".next a")
    self.max_pages_input = QSpinBox(); self.max_pages_input.setRange(1, 5000); self.max_pages_input.setValue(50)
    self.max_depth_input = QSpinBox(); self.max_depth_input.setRange(1, 25); self.max_depth_input.setValue(2)
    self.same_host_check = QCheckBox("Same Host Only"); self.same_host_check.setChecked(True)
    crawl_row.addWidget(QLabel("Next Page Selector:")); crawl_row.addWidget(self.next_selector_input)
    crawl_row.addWidget(QLabel("Max Pages:")); crawl_row.addWidget(self.max_pages_input)
    crawl_row.addWidget(QLabel("Max Depth:")); crawl_row.addWidget(self.max_depth_input)
    crawl_row.addWidget(self.same_host_check)
    self.layout.addLayout(crawl_row)

    # Selectors JSON
    self.selectors_label = QLabel('Extract Selectors JSON (e.g. {"title": "h1", "body": ".article p"})')
    self.selectors_input = QTextEdit()
    self.layout.addWidget(self.selectors_label)
    self.layout.addWidget(self.selectors_input)

    # Profiles
    prof_row = QHBoxLayout()
    self.profile_combo = QComboBox(); self.profile_combo.addItems(["(none)"])
    self.profile_combo.currentTextChanged.connect(self.apply_profile)
    self.load_profiles_btn = QPushButton("Load Profiles")
    self.load_profiles_btn.clicked.connect(self.load_profiles)
    prof_row.addWidget(QLabel("Profile:"))
    prof_row.addWidget(self.profile_combo)
    prof_row.addWidget(self.load_profiles_btn)
    self.layout.addLayout(prof_row)

    # Options
    opts = QHBoxLayout()
    self.headless_check = QCheckBox("Headless"); self.headless_check.setChecked(True)
    self.stealth_check = QCheckBox("Stealth-ish"); self.stealth_check.setChecked(True)
    self.disable_images_check = QCheckBox("Block images/fonts/media"); self.disable_images_check.setChecked(True)
    opts.addWidget(self.headless_check); opts.addWidget(self.stealth_check); opts.addWidget(self.disable_images_check)
    self.layout.addLayout(opts)

    # Proxy
    px = QHBoxLayout()
    self.proxy_input = QLineEdit(); self.proxy_input.setPlaceholderText("Proxy URL or path to .txt list")
    self.load_proxy_btn = QPushButton("Load Proxy List")
    self.load_proxy_btn.clicked.connect(self.load_proxy_list)
    px.addWidget(QLabel("Proxy:")); px.addWidget(self.proxy_input); px.addWidget(self.load_proxy_btn)
    self.layout.addLayout(px)

    # Buttons
    btns = QHBoxLayout()
    self.scrape_button = QPushButton("Scrape"); self.scrape_button.clicked.connect(self.start_scrape)
    self.crawl_button = QPushButton("Crawl"); self.crawl_button.clicked.connect(self.start_crawl)
    self.cancel_button = QPushButton("Cancel"); self.cancel_button.clicked.connect(self.cancel_tasks)
    self.save_button = QPushButton("Save Results"); self.save_button.clicked.connect(self.save_results)
    btns.addWidget(self.scrape_button); btns.addWidget(self.crawl_button); btns.addWidget(self.cancel_button); btns.addWidget(self.save_button)
    # in your ScraperGUI.__init__/init_ui (PyQt6)
    self.autofill_btn = QPushButton("Autofill Media")
    self.autofill_btn.clicked.connect(self.autofill_media_file)
    # add near other buttons
    btns_layout = self.layout.itemAt(self.layout.count()-1).layout() if self.layout.count() else None
    (btns_layout or self.layout).addWidget(self.autofill_btn)

    self.layout.addLayout(btns)

    # Output
    self.output_label = QLabel("Output:")
    self.output_text = QTextEdit(); self.output_text.setReadOnly(True)
    self.layout.addWidget(self.output_label); self.layout.addWidget(self.output_text)

    # Logs
    self.log_label = QLabel("Logs:")
    self.log_text = QTextEdit(); self.log_text.setReadOnly(True)
    self.layout.addWidget(self.log_label); self.layout.addWidget(self.log_text)

# ---------- profiles ----------
def load_profiles(self):
    path, _ = QFileDialog.getOpenFileName(self, "Load Selector Profiles", "", "JSON (*.json)")
    if not path: return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            self.profiles = json.load(f)
        self.profile_combo.clear(); self.profile_combo.addItems(["(none)"] + list(self.profiles.keys()))
        self.log(f"Loaded profiles from {path}")
    except Exception as e:
        self.log(f"Error loading profiles: {e}")

def apply_profile(self):
    name = self.profile_combo.currentText()
    if name != "(none)" and name in self.profiles:
        p = self.profiles[name]
        self.selectors_input.setPlainText(json.dumps(p.get('selectors', {}), indent=2))
        self.wait_for_input.setText(p.get('wait_for',''))
        self.next_selector_input.setText(p.get('next_selector',''))
        self.log(f"Applied profile: {name}")

# ---------- proxies ----------
def load_proxy_list(self):
    path, _ = QFileDialog.getOpenFileName(self, "Load Proxy List", "", "Text (*.txt);;All Files (*)")
    if not path: return
    try:
        with open(path,'r',encoding='utf-8') as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        self.proxy_input.setText(path)
        self.log(f"Loaded {len(lines)} proxies")
    except Exception as e:
        self.log(f"Error loading proxy list: {e}")
def get_proxy_pool(self) -> List[str]:
    p = self.proxy_input.text().strip()
    if not p: return []
    if p.endswith('.txt'):
        try:
            with open(p,'r',encoding='utf-8') as f:
                return [ln.strip() for ln in f if ln.strip()]
        except Exception:
            return []
    return [p]

# ---------- actions ----------
def start_scrape(self):
    url = self.url_input.text().strip()
    if not url:
        self.log("Please enter a URL"); return
    try:
        selectors = json.loads(self.selectors_input.toPlainText().strip() or "{}")
    except json.JSONDecodeError:
        self.log("Invalid selectors JSON"); return
    cfg = EmulatorConfig(
        engine=self.engine_combo.currentText(),
        headless=self.headless_check.isChecked(),
        proxy_pool=self.get_proxy_pool(),
        stealth_mode=self.stealth_check.isChecked(),
        disable_images=self.disable_images_check.isChecked()
    )
    task = {'url': url, 'wait_for': self.wait_for_input.text().strip() or None, 'selectors': selectors}
    self.toggle_buttons(False)
    w = ScrapeWorker(cfg, task)
    w.result_signal.connect(self.display_results)
    w.log_signal.connect(self.log_text.append)
    w.finished.connect(lambda: self.toggle_buttons(True))
    self.workers.append(w); w.start()

def start_crawl(self):
    url = self.url_input.text().strip()
    if not url:
        self.log("Please enter a URL"); return
    try:
        selectors = json.loads(self.selectors_input.toPlainText().strip() or "{}")
    except json.JSONDecodeError:
        self.log("Invalid selectors JSON"); return
    cfg = EmulatorConfig(
        engine=self.engine_combo.currentText(),
        headless=self.headless_check.isChecked(),
        proxy_pool=self.get_proxy_pool(),
        stealth_mode=self.stealth_check.isChecked(),
        disable_images=self.disable_images_check.isChecked()
    )
    task = {
        'url': url,
        'selectors': selectors,
        'next_selector': self.next_selector_input.text().strip() or None,
        'same_host_only': self.same_host_check.isChecked(),
        'max_pages': self.max_pages_input.value(),
        'max_depth': self.max_depth_input.value()
    }
    self.toggle_buttons(False)
    w = CrawlWorker(cfg, task)
    w.result_signal.connect(self.display_results)
    w.log_signal.connect(self.log_text.append)
    w.finished.connect(lambda: self.toggle_buttons(True))
    self.workers.append(w); w.start()

def cancel_tasks(self):
    for w in self.workers:
        try: w.cancel()
        except Exception: pass
    self.workers.clear()
    self.toggle_buttons(True)
    self.log("All tasks cancelled")
# top of your file


# inside ScraperGUI
def autofill_media_file(self):
    from abstract_paths import get_files_and_dirs
    dirs,files = get_files_and_dirs('/var/www/TDD/thedailydialectics/src/pages/problems-and-solutions')
    files = [file for file in files if file and os.path.basename(file) == 'variables.json']
    for file in files:
        #path, _ = QFileDialog.getOpenFileName(self, f"Open {file}", "", "JSON (*.json)")
        #if not path: return
        try:
            enriched = load_and_enrich(file)
            # show preview in the output pane
            #self.output_text.setPlainText(json.dumps(enriched.get("media", []), indent=2, ensure_ascii=False))
            # prompt save
            #out_path, _ = QFileDialog.getSaveFileName(self, "Save enriched variables.json", path, "JSON (*.json)")
            #if out_path:
            save_json(enriched, file)
            self.log_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Saved enriched file to {out_path}")
        except Exception as e:
            self.log_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Autofill failed: {e}")

# ---------- results / export ----------
def display_results(self, res: Dict[str, Any]):
    self.last_result = res
    if 'pages' in res:
        short = {'status': res.get('status'), 'pages': [
            {'url': p.get('url'), 'title': p.get('title'), 'status': p.get('status'), 'data': p.get('data')}
            for p in res.get('pages', [])
        ]}
        self.output_text.setPlainText(json.dumps(short, indent=2, ensure_ascii=False))
    else:
        short = {k: res.get(k) for k in ('url','title','status','data','cookies')}
        self.output_text.setPlainText(json.dumps(short, indent=2, ensure_ascii=False))

def _slug(self, s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9._-]+','_', s)[:120]

def save_results(self):
    if not self.last_result:
        self.log("No results to save"); return
    out_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
    if not out_dir: return
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    try:
        if 'pages' in self.last_result:
            pages = self.last_result['pages']
            # JSONL
            with open(out/'results.jsonl','w',encoding='utf-8') as f:
                for p in pages: f.write(json.dumps(p, ensure_ascii=False) + '\n')
            # CSV
            keys = sorted({k for p in pages for k in ['url','title','status'] | set((p.get('data') or {}).keys())})
            with open(out/'results.csv','w',encoding='utf-8',newline='') as f:
                w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
                for p in pages:
                    row = {'url': p.get('url'), 'title': p.get('title'), 'status': p.get('status')}
                    for k,v in (p.get('data') or {}).items():
                        row[k] = '|'.join(v) if isinstance(v, list) else v
                    w.writerow(row)
            # HTML dumps present?
            for p in pages:
                html = p.get('html')
                if html:
                    fname = self._slug(urlparse(p['url']).path or 'index') + '.html'
                    (out/fname).write_text(html, encoding='utf-8')
            self.log(f"Saved crawl results to: {out_dir}")
        else:
            (out/'results.json').write_text(json.dumps(self.last_result, indent=2, ensure_ascii=False), encoding='utf-8')
            self.log(f"Saved results to: {out_dir}/results.json")
    except Exception as e:
        self.log(f"Error saving results: {e}")

# ---------- util ----------
def toggle_buttons(self, enabled: bool):
    self.scrape_button.setEnabled(enabled)
    self.crawl_button.setEnabled(enabled)

def log(self, msg: str):
    self.log_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def closeEvent(self, event):
    self.cancel_tasks()
    event.accept()
