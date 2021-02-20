import argparse
from subprocess import getoutput
import sys

from github_activity import generate_activity_md

DESCRIPTION = "Update the changelog since the last release."
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    "branch",
    help="""The target branch.""",
)
parser.add_argument(
    "version",
    help="""The new version.""",
)

def update_changelog(branch, version):
    since = getoutput(f'git tag --merged {branch}').splitlines()[-1]
    print(f'Getting changes since {since}')

    output = ''

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

    with open('CHANGELOG.md') as fid:
        changelog = fid.read()

    insertion_marker = '<!-- <INSERT CHANGELOG BELOW> -->'
    delimiter = f'<!-- CHANGELOG FOR VERSION {version} -->'
    template = f"""
{insertion_marker}

{delimiter}
{output}
{delimiter}
    """.strip()

    changelog = changelog.replace(insertion_marker, template)

    with open('CHANGELOG.md', 'w') as fid:
        fid.write(changelog)


def main():
    args = parser.parse_args(sys.argv[1:])
    update_changelog(args.branch, args.version)


if __name__ == "__main__":
    main()
