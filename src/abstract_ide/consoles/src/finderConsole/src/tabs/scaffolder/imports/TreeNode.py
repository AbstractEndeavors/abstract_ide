from .src import *
class NodeType(Enum):
    DIRECTORY = auto()
    FILE = auto()
@dataclass
class TreeNode:
    """Schema for a parsed tree node."""
    TreeNode=[]
    name: str
    node_type: NodeType
    depth: int
    children: list[TreeNode] = field(default_factory=list)
    parent: Optional[TreeNode] = None

    @property
    def is_file(self) -> bool:
        return self.node_type == NodeType.FILE

    @property
    def is_directory(self) -> bool:
        return self.node_type == NodeType.DIRECTORY
