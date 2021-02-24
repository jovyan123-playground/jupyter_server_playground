import os
import os.path as osp
import re
import sys

from github_activity import generate_activity_md

HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from utils import get_version

# Get the final version string for the current version
print(re.match('(\d+\.\d+\.\d+)', get_version()).groups()[0])