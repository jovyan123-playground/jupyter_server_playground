import argparse
from subprocess import check_output
import os
import os.path as osp
import sys

from github_activity import generate_activity_md

HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from utils import get_branch, get_version

CHANGELOG_FILE = osp.abspath(osp.join(HERE, '..', 'CHANGELOG.md'))
INSERTION_MARKER = '<!-- <INSERT CHANGELOG BELOW> -->'

DESCRIPTION = "Generate the changelog entry since the last release."
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


def get_delimiters(version):
    """Get the start and end delimiters as a tuple."""
    start_delimiter = f'<!-- <START CHANGELOG FOR VERSION {version}> -->'
    end_delimiter = f'<!-- <END CHANGELOG FOR VERSION {version}> -->'
    return start_delimiter, end_delimiter


def get_changelog_entry(branch, version):
    since = check_output(f'git tag --merged {branch}'.split())
    since = since.decode('utf-8').splitlines()[-1]
    print(f'Getting changes since {since}...')

    md = generate_activity_md(
        "jupyter-server/jupyter_server",
        since=since,
        kind="pr"
    )
        
    if not md:
        raise ValueError('No PRs found')

    md = md.splitlines()

    start = -1
    end = -1
    full_changelog = ''
    for (ind, line) in enumerate(md):
        if '[full changelog]' in line:
            full_changelog = line.replace('full changelog', 'Full Changelog')
        elif line.strip().startswith('## Merged PRs'):
            start = ind + 1
        elif line.strip().startswith('## Contributors to this release'):
            end = ind

    prs = '\n'.join(md[start:end]).strip()
    output = f"""
## {version}

{full_changelog}

{prs}
""".strip()

    print(output)
    start_delimiter, end_delimiter = get_delimiters(version)

    return f"""
{start_delimiter}
{output}
{end_delimiter}
    """.strip()


def main():
    """Create a new changelog entry for a given branch and version.
    """
    args = parser.parse_args(sys.argv[1:])
    version = args.version
    branch = args.branch

    with open(CHANGELOG_FILE) as fid:
        changelog = fid.read()

    entry = get_changelog_entry(branch, version)
   
    template = f"{INSERTION_MARKER}\n{entry}"
    changelog = changelog.replace(INSERTION_MARKER, template)

    with open(CHANGELOG_FILE, 'w') as fid:
        fid.write(changelog)


if __name__ == "__main__":
    main()
