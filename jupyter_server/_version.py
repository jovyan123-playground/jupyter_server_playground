"""
store the current version info of the server.

"""
from jupyter_packaging import get_version_info

# Version string must appear intact for tbump versioning
__version__ = '100.101.0.dev0'
version_info = get_version_info(__version__)
