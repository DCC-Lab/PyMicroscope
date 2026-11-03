try:
    from pymicroscope._version import __version__, version
except ImportError:
    __version__ = version = "0.0.0.dev0"
