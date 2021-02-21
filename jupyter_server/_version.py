"""
store the current version info of the server.
"""
import re

# Version string must appear intact for tbump versioning
__version__ = '1.5.1.dev0'

# Build up the version info tuple from the version string
pattern = '''
(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)
((?P<channel>a|b|rc|.dev)(?P<release>\d+))?
'''.strip().replace('\n', '')
values = re.match(pattern, __version__).groupdict()
version_info = [
    int(values['major']),
    int(values['minor']),
    int(values['patch'])
]
if values['channel']:
    version_info.append(values['channel'] + values['release'])
version_info = tuple(version_info)
