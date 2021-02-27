import argparse
import os
import os.path as osp
import sys


HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from utils import run

DESCRIPTION = "Update the version"
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    "version",
    help="""The new version.""",
)
parser.add_argument(
    "--version-command", "-vc",
    default="tbump --non-interactive --only-patch",
    help="""The version command to run""",
)


def main(version, version_command):
    """Handle the new version"""
    ## Bump the verison
    run(f'{version_command} {version_spec}')


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    main(args.version, args.version_command)
