
import argparse
import os
import os.path as osp
import re
import sys

HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from prep_changelog import (
    get_changelog_entry, START_MARKER, END_MARKER
)
from utils import get_branch, get_version

DESCRIPTION = "Finalize the changelog for the new release."
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


def main(args):
    """Finalizes the changelog for the release.

    - Runs a changelog verification on the new entry.
      - Finds the entry for the version using the delimiter.
      - Makes sure all of the relevant PRs are in there by PR number
      (titles might have been edited).
    - Optionally writes the changelog entry out to a file.
    - Updates the comment markers and overwrites changelog.
    """
    version = args.version
    branch = args.branch
    output = args.output
    target = args.target
    path = args.file
    auth = args.auth
    resolve_backports = args.resolve_backports

    with open(path) as fid:
        changelog = fid.read()

    start = changelog.find(START_MARKER)
    end = changelog.find(END_MARKER)

    if start == -1 or end == -1:
        raise ValueError('Missing new changelog entry delimiter(s)')

    if start != changelog.rfind(START_MARKER):
        raise ValueError('Insert marker appears more than once in changelog')

    final_entry = changelog[start + len(START_MARKER): end]

    raw_entry = get_changelog_entry(target, branch, version, auth=auth, resolve_backports=resolve_backports)

    if f'# {version}' not in final_entry:
        raise ValueError(f'Did not find entry for {version}')

    final_prs = re.findall('\[#(\d+)\]', final_entry)
    raw_prs = re.findall('\[#(\d+)\]', raw_entry)

    for pr in raw_prs:
        # Allow for the changelog PR to not be in the changelog itself
        skip = False
        for line in raw_entry.splitlines():
            if f'[#{pr}]' in line and 'changelog' in line.lower():
                skip = True
                break
        if skip:
            continue
        if not f'[#{pr}]' in final_entry:
            raise ValueError(f'Missing PR #{pr} in the changelog')
    for pr in final_prs:
        if not f'[#{pr}]' in raw_entry:
            raise ValueError(f'PR #{pr} does not belong in the changelog for {version}')

    if output:
        with open(output, 'w') as fid:
            fid.write(final_entry)

    # Clear out the insertion markers
    changelog = changelog.replace(END_MARKER, '')
    marker = f'{START_MARKER}\n{END_MARKER}\n'
    changelog = changelog.replace(START_MARKER, marker)

    with open(path, 'w') as fid:
        fid.write(changelog)


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    main(args)
