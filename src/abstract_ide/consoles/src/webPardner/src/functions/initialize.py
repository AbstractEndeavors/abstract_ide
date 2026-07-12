from ..imports import *

# Recovered 2026-07-11 from the orphaned functions/__pycache__/initialize.cpython-313.pyc
# blueprint (the migration lost the source). Method set + wiring reconstructed
# from bytecode; the scraper engine (imports/*) was intact.


def init_ui(self):
    self.central_widget = QWidget()
    self.setCentralWidget(self.central_widget)
    layout = QVBoxLayout(self.central_widget)

    # engine
    engine_row = QHBoxLayout()
    engine_row.addWidget(QLabel("Engine:"))
    self.engine_combo = QComboBox()
    self.engine_combo.addItems(["Playwright", "Selenium"])
    engine_row.addWidget(self.engine_combo)
    layout.addLayout(engine_row)

    # url
    self.url_label = QLabel("URL to Scrape:")
    layout.addWidget(self.url_label)
    self.url_input = QLineEdit()
    self.url_input.setPlaceholderText("https://example.com")
    layout.addWidget(self.url_input)

    # wait-for selector
    self.wait_for_label = QLabel("Wait for Selector (optional):")
    layout.addWidget(self.wait_for_label)
    self.wait_for_input = QLineEdit()
    self.wait_for_input.setPlaceholderText(".content")
    layout.addWidget(self.wait_for_input)

    # crawl row
    crawl_row = QHBoxLayout()
    crawl_row.addWidget(QLabel("Next Page Selector:"))
    self.next_selector_input = QLineEdit()
    self.next_selector_input.setPlaceholderText(".next a")
    crawl_row.addWidget(self.next_selector_input)
    crawl_row.addWidget(QLabel("Max Pages:"))
    self.max_pages_input = QSpinBox()
    self.max_pages_input.setRange(1, 100000)
    self.max_pages_input.setValue(20)
    crawl_row.addWidget(self.max_pages_input)
    crawl_row.addWidget(QLabel("Max Depth:"))
    self.max_depth_input = QSpinBox()
    self.max_depth_input.setRange(0, 100)
    self.max_depth_input.setValue(2)
    crawl_row.addWidget(self.max_depth_input)
    self.same_host_check = QCheckBox("Same Host Only")
    self.same_host_check.setChecked(True)
    crawl_row.addWidget(self.same_host_check)
    layout.addLayout(crawl_row)

    # selectors
    self.selectors_label = QLabel("Extract Selectors JSON (e.g. {\"title\": \"h1\", \"body\": \".article p\"})")
    layout.addWidget(self.selectors_label)
    self.selectors_input = QTextEdit()
    self.selectors_input.setPlaceholderText('{"title": "h1", "body": ".article p"}')
    layout.addWidget(self.selectors_input)

    # profiles
    prof_row = QHBoxLayout()
    prof_row.addWidget(QLabel("Profile:"))
    self.profile_combo = QComboBox()
    self.profile_combo.addItems(["(none)"])
    self.profile_combo.currentTextChanged.connect(self.apply_profile)
    prof_row.addWidget(self.profile_combo)
    self.load_profiles_btn = QPushButton("Load Profiles")
    self.load_profiles_btn.clicked.connect(self.load_profiles)
    prof_row.addWidget(self.load_profiles_btn)
    layout.addLayout(prof_row)

    # options
    opts = QHBoxLayout()
    self.headless_check = QCheckBox("Headless")
    self.headless_check.setChecked(True)
    self.stealth_check = QCheckBox("Stealth-ish")
    self.stealth_check.setChecked(True)
    self.disable_images_check = QCheckBox("Block images/fonts/media")
    self.disable_images_check.setChecked(True)
    opts.addWidget(self.headless_check)
    opts.addWidget(self.stealth_check)
    opts.addWidget(self.disable_images_check)
    layout.addLayout(opts)

    # proxy
    px = QHBoxLayout()
    px.addWidget(QLabel("Proxy:"))
    self.proxy_input = QLineEdit()
    self.proxy_input.setPlaceholderText("Proxy URL or path to .txt list")
    px.addWidget(self.proxy_input)
    self.load_proxy_btn = QPushButton("Load Proxy List")
    self.load_proxy_btn.clicked.connect(self.load_proxy_list)
    px.addWidget(self.load_proxy_btn)
    layout.addLayout(px)

    # action buttons
    self.scrape_button = QPushButton("Scrape")
    self.scrape_button.clicked.connect(self.start_scrape)
    self.crawl_button = QPushButton("Crawl")
    self.crawl_button.clicked.connect(self.start_crawl)
    self.cancel_button = QPushButton("Cancel")
    self.cancel_button.clicked.connect(self.cancel_tasks)
    self.save_button = QPushButton("Save Results")
    self.save_button.clicked.connect(self.save_results)
    self.autofill_btn = QPushButton("Autofill Media")
    self.autofill_btn.clicked.connect(self.autofill_media_file)
    btns = [self.scrape_button, self.crawl_button, self.cancel_button,
            self.save_button, self.autofill_btn]
    btns_layout = QHBoxLayout()
    for b in btns:
        btns_layout.addWidget(b)
    layout.addLayout(btns_layout)

    # output + logs
    self.output_label = QLabel("Output:")
    layout.addWidget(self.output_label)
    self.output_text = QTextEdit()
    self.output_text.setReadOnly(True)
    layout.addWidget(self.output_text)

    self.log_label = QLabel("Logs:")
    layout.addWidget(self.log_label)
    self.log_text = QTextEdit()
    self.log_text.setReadOnly(True)
    layout.addWidget(self.log_text)


def load_profiles(self):
    path, _ = QFileDialog.getOpenFileName(self, "Load Selector Profiles", "", "JSON (*.json)")
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            self.profiles = json.load(f)
        self.profile_combo.clear()
        self.profile_combo.addItems(["(none)"] + list(self.profiles.keys()))
        self.log("Loaded profiles from " + path)
    except Exception as e:
        self.log("Error loading profiles: " + str(e))


def apply_profile(self):
    name = self.profile_combo.currentText()
    if name == "(none)":
        return
    p = self.profiles.get(name, {})
    self.selectors_input.setPlainText(json.dumps(p.get("selectors", {}), indent=2))
    self.wait_for_input.setText(p.get("wait_for", ""))
    self.next_selector_input.setText(p.get("next_selector", ""))
    self.log("Applied profile: " + name)


def load_proxy_list(self):
    path, _ = QFileDialog.getOpenFileName(self, "Load Proxy List", "", "Text (*.txt);;All Files (*)")
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        self.proxy_input.setText(path)
        self.log("Loaded " + str(len(lines)) + " proxies")
    except Exception as e:
        self.log("Error loading proxy list: " + str(e))


def get_proxy_pool(self):
    p = self.proxy_input.text().strip()
    if not p:
        return None
    if p.endswith(".txt"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return [ln.strip() for ln in f if ln.strip()]
        except Exception:
            return None
    return [p]


def start_scrape(self):
    url = self.url_input.text().strip()
    if not url:
        self.log("Please enter a URL")
        return
    try:
        selectors = json.loads(self.selectors_input.toPlainText() or "{}")
    except json.JSONDecodeError:
        self.log("Invalid selectors JSON")
        return
    cfg = EmulatorConfig(
        engine=self.engine_combo.currentText(),
        headless=self.headless_check.isChecked(),
        proxy_pool=self.get_proxy_pool(),
        stealth_mode=self.stealth_check.isChecked(),
        disable_images=self.disable_images_check.isChecked(),
    )
    task = {"url": url, "wait_for": self.wait_for_input.text().strip() or None, "selectors": selectors}
    self.toggle_buttons(False)
    w = ScrapeWorker(cfg, task)
    w.result_signal.connect(self.display_results)
    w.log_signal.connect(self.log_text.append)
    w.finished.connect(lambda: self.toggle_buttons(True))
    self.workers.append(w)
    w.start()


def start_crawl(self):
    url = self.url_input.text().strip()
    if not url:
        self.log("Please enter a URL")
        return
    try:
        selectors = json.loads(self.selectors_input.toPlainText() or "{}")
    except json.JSONDecodeError:
        self.log("Invalid selectors JSON")
        return
    cfg = EmulatorConfig(
        engine=self.engine_combo.currentText(),
        headless=self.headless_check.isChecked(),
        proxy_pool=self.get_proxy_pool(),
        stealth_mode=self.stealth_check.isChecked(),
        disable_images=self.disable_images_check.isChecked(),
    )
    task = {
        "url": url,
        "selectors": selectors,
        "next_selector": self.next_selector_input.text().strip() or None,
        "same_host_only": self.same_host_check.isChecked(),
        "max_pages": self.max_pages_input.value(),
        "max_depth": self.max_depth_input.value(),
    }
    self.toggle_buttons(False)
    w = CrawlWorker(cfg, task)
    w.result_signal.connect(self.display_results)
    w.log_signal.connect(self.log_text.append)
    w.finished.connect(lambda: self.toggle_buttons(True))
    self.workers.append(w)
    w.start()


def cancel_tasks(self):
    for w in self.workers:
        try:
            w.cancel()
        except Exception:
            pass
    self.workers.clear()
    self.toggle_buttons(True)
    self.log("All tasks cancelled")


def autofill_media_file(self):
    try:
        import os
        from abstract_paths import get_files_and_dirs
        dirs, files = get_files_and_dirs(
            "/var/www/TDD/thedailydialectics/src/pages/problems-and-solutions")
        for file in files:
            if os.path.basename(file) == "variables.json":
                enriched = load_and_enrich(file)
                out_path = file
                save_json(enriched, out_path)
                self.log_text.append(
                    "[" + time.strftime("%Y-%m-%d %H:%M:%S") + "] Saved enriched file to " + out_path)
    except Exception as e:
        self.log_text.append(
            "[" + time.strftime("%Y-%m-%d %H:%M:%S") + "] Autofill failed: " + str(e))


def display_results(self, res):
    self.last_result = res
    if isinstance(res, dict) and res.get("pages"):
        short = [{k: p.get(k) for k in ("url", "title", "status")} for p in res["pages"]]
        self.output_text.setPlainText(json.dumps(short, indent=2))
    else:
        self.output_text.setPlainText(json.dumps(res.get("data", res) if isinstance(res, dict) else res, indent=2))


def _slug(self, s):
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s)


def save_results(self):
    if not self.last_result:
        self.log("No results to save")
        return
    out_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
    if not out_dir:
        return
    try:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        pages = self.last_result.get("pages") if isinstance(self.last_result, dict) else None
        if pages:
            # crawl result: jsonl + csv + per-page html
            with open(out / "results.jsonl", "w", encoding="utf-8") as f:
                for p in pages:
                    f.write(json.dumps(p) + "\n")
            keys = sorted(set().union(*[set((p.get("data") or {}).keys()) for p in pages])) if pages else []
            with open(out / "results.csv", "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["url", "title", "status"] + keys)
                w.writeheader()
                for p in pages:
                    row = {"url": p.get("url"), "title": p.get("title"), "status": p.get("status")}
                    for k, v in (p.get("data") or {}).items():
                        row[k] = "|".join(v) if isinstance(v, list) else v
                    w.writerow(row)
                    html = p.get("html")
                    if html:
                        fname = self._slug(urlparse(p.get("url", "index")).path or "index") + ".html"
                        (out / fname).write_text(html, encoding="utf-8")
            self.log("Saved crawl results to: " + str(out))
        else:
            (out / "results.json").write_text(json.dumps(self.last_result, indent=2), encoding="utf-8")
            self.log("Saved results to: " + str(out) + "/results.json")
    except Exception as e:
        self.log("Error saving results: " + str(e))


def toggle_buttons(self, enabled):
    self.scrape_button.setEnabled(enabled)
    self.crawl_button.setEnabled(enabled)


def log(self, msg):
    self.log_text.append("[" + time.strftime("%Y-%m-%d %H:%M:%S") + "] " + str(msg))


def closeEvent(self, event):
    self.cancel_tasks()
    event.accept()
