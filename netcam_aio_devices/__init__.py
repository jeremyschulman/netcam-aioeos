import importlib.metadata as importlib_metadata
from .register import register

__version__ = importlib_metadata.version(__name__)
