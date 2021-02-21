
import argparse
import os
import os.path as osp
import re
import sys

HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from utils import get_branch, get_version

DESCRIPTION = "Verify the changelog for the new release."
parser = argparse.ArgumentParser(description=DESCRIPTION)
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

def main():
    """Runs a changelog verification on the new entry.  

    Finds the entry for the version using the delimiter. 
    Makes sure all of the relevant PRs are in there by PR number 
      (titles might have been edited).
    Writes the changelog entry out to a file.
    Removes the comment delimiters and overwrites changelog.
    """
    args = parser.parse_args(sys.argv[1:])
    version = args.version
    branch = args.branch

    with open('CHANGELOG.md') as fid:
        changelog = fid.read()

    # get the changelog entry from `get_changelog_entry`
    sys.path.insert(0, HERE)
    from generate_changelog import CHANGELOG_FILE, get_changelog_entry, get_delimiters

    start_delimiter, end_delimiter = get_delimiters(version)

    start = changelog.find(start_delimiter)
    end = changelog.find(end_delimiter)

    if start == -1 or end == -1:
        raise ValueError(f'No changelog entry found for {version}')

    new_entry = changelog[start + len(start_delimiter): end]

    orig_entry = get_changelog_entry(branch, version)

    new_prs = re.findall('\[#(\d+)\]', new_entry)
    orig_prs = re.findall('\[#(\d+)\]', orig_entry)
    for pr in orig_prs:
        if not f'[#{pr}]' in new_entry:
            raise ValueError(f'Missing PR #{pr} in the changelog')
    for pr in new_prs:
        if not f'[#{pr}]' in orig_entry:
            raise ValueError(f'PR #{pr} does not belong in the changelog for {version}')
    
    entry_file = osp.abspath(osp.join(HERE, '..', f'changelog_{version}.md'))
    with open(entry_file, 'w') as fid:
        fid.write(new_entry)

    changelog = changelog.replace(start_delimiter, '')
    changelog = changelog.replace(end_delimiter, '')

    with open(CHANGELOG_FILE, 'w') as fid:
        fid.write(changelog)
    


if __name__ == "__main__":
    main()
