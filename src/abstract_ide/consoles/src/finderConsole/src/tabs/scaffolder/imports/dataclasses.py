from .src import *
from .TreeNode import *




@dataclass
class FileEntry:
    """Schema for a file in the registry."""

    relative_path: Path
    absolute_path: Path
    content: str = ""
    is_dirty: bool = False
    exists_on_disk: bool = False


@dataclass
class Config:
    """Explicit configuration schema."""

    root_path: Optional[Path] = None
    tree_indent_chars: tuple[str, ...] = ("│", "├", "└", "─", "    ", "   ")
    file_extensions: tuple[str, ...] = (".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml")
