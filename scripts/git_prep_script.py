# ChangeLog Action
import argparse
import os
import os.path as osp
import re
import sys


HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from utils import run


DESCRIPTION = "Finalize the changelog for the new release."
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    "repository",
    help="""The GitHub organization/repo."""
)
parser.add_argument(
    "branch",
    help="""The target branch."""
)
parser.add_argument(
    "--remote", "-r",
    default="upstream",
    help="""The git remote name."""
)


def main():
    """Set up the Git config for the GitHub Action"""
    args = parser.parse_args(sys.argv[1:])
    remote = args.remote
    repository = args.repository
    branch = args.branch

    # Use email address for the GitHub Actions bot
    # https://github.community/t/github-actions-bot-email-address/17204/6
    run('git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"')
    run('git config --global user.name "GitHub Action"')
    run(f'git remote add {remote} https://github.com/{repository}')
    run(f'git fetch {remote} {branch} --tags')


if __name__ == "__main__":
    main()
