import sys, os, subprocess, json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QPushButton, QTextEdit, QListWidget, QInputDialog
)

ROOT = "/var/www/modules/packages"

class testRunnerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Abstract Packages Explorer")
        layout = QVBoxLayout()

        self.func_list = QListWidget()
        layout.addWidget(self.func_list)

        btn_all = QPushButton("Run All Tests")
        btn_all.clicked.connect(self.run_all)
        layout.addWidget(btn_all)

        btn_func = QPushButton("Run Selected Function")
        btn_func.clicked.connect(self.run_function)
        layout.addWidget(btn_func)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.setLayout(layout)
        self.load_functions()

    def run_all(self):
        for pkg in os.listdir(ROOT):
            test_dir = os.path.join(ROOT, pkg, "test")
            if not os.path.isdir(test_dir):
                self.log.append(f"⚠️ Skipping {pkg}, no test dir")
                continue
            self.log.append(f"🔍 Running tests for {pkg}...")
            proc = subprocess.run(
                ["npm", "test"], cwd=test_dir,
                capture_output=True, text=True
            )
            if proc.returncode == 0:
                self.log.append(f"✅ {pkg} passed\n{proc.stdout}")
            else:
                self.log.append(f"❌ {pkg} failed\n{proc.stderr}")

    def load_functions(self):
        pkg_name = "@putkoff/abstract-apis"
        # use absolute file:// path for Node import
        pkg_path = os.path.join(ROOT, "abstract-apis", "dist", "functions", "secure_utils", "src", "secure_utils.js")

        script = f"""
        import * as pkg from 'file://{pkg_path}';
        console.log(JSON.stringify(Object.keys(pkg)));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            capture_output=True, text=True
        )
        try:
            funcs = json.loads(result.stdout)
        except Exception as e:
            self.log.append(f"❌ Failed to load functions: {e}\n{result.stderr}")
            funcs = []
        for fn in funcs:
            self.func_list.addItem(f"{pkg_name}:{fn}")

    def run_function(self):
        item = self.func_list.currentItem()
        if not item:
            return
        pkg, fn = item.text().split(":")

        args, ok = QInputDialog.getText(
            self, "Run Function",
            f"Enter args for {fn} as JSON array:"
        )
        if not ok:
            return

        pkg_path = os.path.join(ROOT, "abstract-apis", "dist", "index.js")
        script = f"""
        import * as pkg from 'file://{pkg_path}';
        (async () => {{
          try {{
            const result = await pkg['{fn}'](...{args});
            console.log(JSON.stringify(result));
          }} catch (err) {{
            console.error("ERR", err?.message || err);
          }}
        }})();
        """
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            capture_output=True, text=True
        )
        output = result.stdout or result.stderr
        self.log.append(f"▶️ {fn}({args})\n{output}")

