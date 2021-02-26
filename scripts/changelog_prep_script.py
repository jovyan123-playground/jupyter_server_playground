# ChangeLog Action
import os
import os.path as osp
import re
import sys


HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from prepare_changelog import parser, main as prepare_changelog
from utils import run, get_version

# Extend the prepare_changelog CLI
parser.description = "Run the Changelog Prep Script"
parser.add_argument(
    "--version-command", "-vc",
    default="tbump --non-interactive --only-patch",
    help="""The version command to run.""",
)


def main(args):
    """Handle the creation of a new changelog entry"""
    branch = args.branch
    version_spec = args.version
    version_command = args.version_command
    changelog = args.file

    ## Bump the verison
    run(f'{version_command} {version_spec}')

    # Get the new version
    version = get_version()

    ## Check out any files affected by the version bump
    run('git checkout .')

    ## Prepare the changelog
    prepare_changelog(args)

    ## Verify the change for the PR
    # Only one uncommitted file
    assert len(run('git diff --numstat').splitlines()) == 1
    # New version entry in the diff
    diff = run(f'git --no-pager diff')
    assert f"# {version}" in diff

    # Follow up actions
    print("Changelog Prep Complete!")
    print("Create a PR for the Changelog change")


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    main(args)
