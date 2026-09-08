from .node import MiniMaxH3Remote


__version__ = "0.1.1"

NODE_CLASS_MAPPINGS = {"MiniMaxH3Remote": MiniMaxH3Remote}
NODE_DISPLAY_NAME_MAPPINGS = {"MiniMaxH3Remote": "MiniMax H3 (remote)"}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "__version__"]
