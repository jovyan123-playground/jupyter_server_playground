"""
store the current version info of the server.

"""
from jupyter_packaging import get_version_info

# Version string must appear intact for tbump versioning
__version__ = '100.100.1'
version_info = get_version_info(__version__)
