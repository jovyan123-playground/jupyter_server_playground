
import argparse
import os
import os.path as osp
import re
import sys

HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from update_changelog import get_changelog_entry, START_MARKER, END_MARKER
from utils import get_branch, get_version

DESCRIPTION = "Verify the changelog for the new release."
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    "target",
    help="""The GitHub organization/repo."""
)
parser.add_argument(
    "file",
    help="""The changelog file path."""
)
parser.add_argument(
    "--branch", "-b",
    default=get_branch(),
    help="""The target branch.""",
)
parser.add_argument(
    "--version", "-v",
    default=get_version(),
    help="""The new version.""",
)
parser.add_argument(
    "--output", "-o",
    default="",
    help="""The output path to store the new change entry if needed.""",
)
parser.add_argument(
    "--auth",
    default=None,
    help=(
        "An authentication token for GitHub. If None, then the environment "
        "variable `GITHUB_ACCESS_TOKEN` will be tried."
    ),
)
parser.add_argument(
    "--resolve-backports",
    action='store_true',
    default=False,
    help="""Whether to resolve meeseeks backports to their original PRS.""",
)


def main():
    """Runs a changelog verification on the new entry.  

    Finds the entry for the version using the delimiter. 
    Makes sure all of the relevant PRs are in there by PR number 
      (titles might have been edited).
    Writes the changelog entry out to a file.
    Updates the comment markers and overwrites changelog.
    """
    args = parser.parse_args(sys.argv[1:])
    version = args.version
    branch = args.branch
    output = args.output
    target = args.target
    path = args.path
    auth = args.auth
    resolve_backports = args.resolve_backports

    with open(path) as fid:
        changelog = fid.read()

    start = changelog.find(START_MARKER)
    end = changelog.find(END_MARKER)

    if start == -1 or end == -1:
        raise ValueError('Missing new changelog entry delimiter(s)')

    if start !== changelog.rfind(START_MARKER):
        raise ValueError('Insert marker appears more than once in changelog')

    new_entry = changelog[start + len(START_MARKER): end]

    orig_entry = get_changelog_entry(target, branch, version, auth=auth, resolve_backports=resolve_backports)

    if f'# {version}' not in new_entry:
        raise ValueError(f'Did not find entry for {version}')

    new_prs = re.findall('\[#(\d+)\]', new_entry)
    orig_prs = re.findall('\[#(\d+)\]', orig_entry)
    for pr in orig_prs:
        if not f'[#{pr}]' in new_entry:
            raise ValueError(f'Missing PR #{pr} in the changelog')
    for pr in new_prs:
        if not f'[#{pr}]' in orig_entry:
            raise ValueError(f'PR #{pr} does not belong in the changelog for {version}')
    
    if output:
        with open(output, 'w') as fid:
            fid.write(new_entry)

    # Clear out the insertion markers
    changelog = changelog.replace(END_MARKER, '')
    marker = f'{START_MARKER}\n{END_MARKER}\n'
    changelog = changelog.replace(START_MARKER, marker)

    with open(path, 'w') as fid:
        fid.write(changelog)
    

if __name__ == "__main__":
    main()