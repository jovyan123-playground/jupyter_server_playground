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
parser.add_argument(
    "--postprocess-command", "-pc",
    help="""The command to run to postprocess the changelog entry.""",
)
parser.add_argument(
    "--output", "-o",
    help="""The output path to store the new change entry if needed.""",
)


def main(args):
    """Handle the creation of a new changelog entry"""
    branch = args.branch
    version_spec = args.version
    version_command = args.version_command
    postprocess_command = args.postprocess_command
    changelog = args.file
    output_file = args.output

    ## Bump the verison
    run(f'{version_command} {version_spec}')

    # Get the new version
    version = get_version()

    ## Check out any files affected by the version bump
    run('git checkout .')

    ## Prepare the changelog
    new_entry = prepare_changelog(args)

    # Run the pre release command if given
    if postprocess_command:
        run(postprocess_command)

    ## Verify the change for the PR
    # Only one uncommitted file
    assert len(run('git diff --numstat')).splitlines() == 1
    # New version entry in the diff
    diff = run(f'git --no-pager diff')
    assert f"# {version}" in diff

    if output_file:
        with open(output_file, 'w') as fid:
            fid.write(new_entry)

    # Follow up actions
    print("Changelog Prep Complete!")
    print("Create a PR for the Changelog change")


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    main(args)
