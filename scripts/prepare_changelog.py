import argparse
import os
import os.path as osp
import re
import sys

from github_activity import generate_activity_md

HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from utils import get_branch, get_version, run

START_MARKER = '<!-- <START NEW CHANGELOG ENTRY> -->'
END_MARKER = '<!-- <END NEW CHANGELOG ENTRY> -->'

DESCRIPTION = "Prepare the changelog entry with changes since the last tag."
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


def format_pr_entry(target, number, auth=None):
    """Format a PR entry in the style used by our changelogs.
    
    Parameters
    ----------
    target : str
        The GitHub organization/repo
    number : int
        The PR number to resolve
    auth : str, optional
        The GitHub authorization token

    Returns
    -------
    str
        A formatted PR entry
    """
    api_token = auth or os.environ['GITHUB_ACCESS_TOKEN']
    headers = {'Authorization': 'token %s' % api_token}
    r = requests.get(f'https://api.github.com/repos/{target}/pulls/{orig_pr}', headers=headers)
    data = r.json()
    title = data['title']
    number = data['number']
    url = data['url']
    user_name = data['user']['login']
    user_url = data['user']['html_url']
    return f"- {title} [{number}]({url}) [@{user_name}]({user_url})"


def get_changelog_entry(target, branch, version, auth=None, resolve_backports=False):
    """Get a changelog for the changes since the last tag on the given branch.

    Parameters
    ----------
    target : str
        The GitHub organization/repo
    branch : str
        The target branch
    auth : str, optional
        The GitHub authorization token
    resolve_backports: bool, optional
        Whether to resolve backports to the original PR

    Returns
    -------
    str
        A formatted changelog entry with markers
    """
    since = run(f'git tag --merged {branch}')
    if not since:
        raise ValueError(f'No tags found on branch {branch}')
    since = since.splitlines()[-1]
    print(f'Getting changes to {target} since {since}...')

    md = generate_activity_md(
        target,
        since=since,
        kind="pr",
        auth=auth
    )
        
    if not md:
        print('No PRs found')
        return f"## {version}\n## Merged PRs\nNone!"

    md = md.splitlines()

    start = -1
    full_changelog = ''
    for (ind, line) in enumerate(md):
        if '[full changelog]' in line:
            full_changelog = line.replace('full changelog', 'Full Changelog')
        elif line.strip().startswith('## Merged PRs'):
            start = ind + 1

    prs = md[start:]

    if resolve_backports:
        for (ind, line) in enumerate(prs):
            if re.search("[@meeseeksmachine]", line) is not None:
                match = re.search("Backport PR #(\d+)", line)
                prs[ind] = format_pr_entry(match.groups()[0])

    prs = '\n'.join(prs).strip()

    # Move the contributor list to a heading level 3
    prs = prs.replace('## Contributors', '### Contributors')

    # Replace "*" unordered list marker with "-" since this is what
    # Prettier uses
    prs = re.sub('^\* ', '- ', prs)
    prs = re.sub('\n\* ', '\n- ', prs)

    output = f"""
## {version}

{full_changelog}

{prs}
""".strip()
    
    return output


def main(args):
    """Create a new changelog entry for a given branch and version.
    """
    version = args.version
    branch = args.branch
    target = args.target
    path = args.file
    auth = args.auth
    resolve_backports = args.resolve_backports

    with open(path) as fid:
        changelog = fid.read()

    marker = f"{START_MARKER}\n{END_MARKER}"

    if marker not in changelog:
        raise ValueError('Missing insert marker for changelog')

    if changelog.find(START_MARKER) != changelog.rfind(START_MARKER):
        raise ValueError('Insert marker appears more than once in changelog')

    entry = get_changelog_entry(target, branch, version, auth=auth, resolve_backports=resolve_backports)
   
    template = f"{START_MARKER}\n{entry}\n{END_MARKER}"
    changelog = changelog.replace(marker, template)

    with open(path, 'w') as fid:
        fid.write(changelog)

    return entry


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    main(args)
