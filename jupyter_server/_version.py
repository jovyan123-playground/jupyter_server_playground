"""
store the current version info of the server.

"""
from pkg_resources import parse_version

# Version string must appear intact for tbump versioning
__version__ = '1.7.0.dev0'

# Build up the version info tuple from the version string
parsed = parse_version(__version__)
version_info = [parsed.major, parsed.minor, parsed.micro]
if parsed.base_version != parsed.public:
    version_info.append(parsed.public[len(parsed.base_version):])
version_info = tuple(version_info)
