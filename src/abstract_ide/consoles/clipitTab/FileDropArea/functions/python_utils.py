from ..imports import *
def _parse_functions(self, file_path: str, text: str) -> None:
    try:
        tree = ast.parse(text, filename=file_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_code = "\n".join(text.splitlines()[node.lineno-1:node.end_lineno])
                imports = self._extract_imports(tree)
                self.functions.append({
                    'name': node.name,
                    'file': file_path,
                    'line': node.lineno,
                    'code': func_code,
                    'imports': imports
                })
    except SyntaxError as e:
        self._log(f"Syntax error in {file_path}: {e}")

def _extract_imports(self, tree: ast.AST) -> list[str]:
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                imports.append(f"from {module} import {alias.name}")
    return imports


def map_function_dependencies(self, function_info: dict) -> None:
    combined_lines = []
    combined_lines.append(f"=== Function: {function_info['name']} ===\n")
    combined_lines.append(function_info['code'])
    combined_lines.append("\n\n=== Imports ===\n")
    combined_lines.extend(function_info['imports'])
    project_files = collect_filepaths(
        [os.path.dirname(function_info['file'])],
        exclude_dirs=self.exclude_dir_patterns,
        exclude_file_patterns=self.exclude_file_patterns
    )
    combined_lines.append("\n\n=== Project Reach ===\n")
    for file_path in project_files:
        if file_path != function_info['file'] and file_path.endswith('.py'):
            combined_lines.append(f"--- {file_path} ---\n")
            try:
                text = read_file_as_text(file_path)
                combined_lines.append(text)
            except Exception as exc:
                combined_lines.append(f"[Error reading {os.path.basename(file_path)}: {exc}]\n")
            combined_lines.append("\n")
    QtWidgets.QApplication.clipboard().setText("\n".join(combined_lines))
    self.status.setText(f"✅ Copied function {function_info['name']} and dependencies to clipboard!")
    self._log(f"Copied function {function_info['name']} with dependencies")


def map_import_chain(self, file_info: dict) -> None:
    try:
        module_paths, imports = get_py_script_paths([file_info['path']])
        combined_lines = []
        combined_lines.append(f"=== Import Chain for {file_info['path']} ===\n")
        combined_lines.append("Modules:\n")
        if module_paths:
            combined_lines.extend(f"- {p}" for p in module_paths)
        else:
            combined_lines.append("- None\n")
        combined_lines.append("\nImports:\n")
        if imports:
            combined_lines.extend(f"- {imp}" for imp in imports)
        else:
            combined_lines.append("- None\n")
        QtWidgets.QApplication.clipboard().setText("\n".join(combined_lines))
        self.status.setText(f"✅ Copied import chain for {os.path.basename(file_info['path'])} to clipboard!")
        self._log(f"Copied import chain for {file_info['path']}")
    except Exception as e:
        tb = traceback.format_exc()
        self.status.setText(f"⚠️ Error mapping import chain: {e}")
        self._log(f"map_import_chain ERROR:\n{tb}")

