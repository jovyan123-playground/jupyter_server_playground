from glob import glob
import hashlib
import json
import os
import os.path as osp
from pathlib import Path
import re
import requests
import shlex
import shutil
from subprocess import check_output, CalledProcessError
from tempfile import TemporaryDirectory

import click
from github_activity import generate_activity_md

HERE = osp.abspath(osp.dirname(__file__))
START_MARKER = '<!-- <START NEW CHANGELOG ENTRY> -->'
END_MARKER = '<!-- <END NEW CHANGELOG ENTRY> -->'
BUF_SIZE = 65536
TBUMP_CMD = 'tbump --non-interactive --only-patch'


#"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
# Helper Functions
#"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

def run(cmd, **kwargs):
    """Run a command as a subprocess and get the output as a string"""
    if not kwargs.pop('quiet', False):
        print(f'+ {cmd}')
    return check_output(shlex.split(cmd), **kwargs).decode('utf-8').strip()


def get_branch():
    """Get the local git branch"""
    return run('git branch --show-current', quiet=True)


def get_repo(remote):
    """Get the remote repo org and name"""
    url = run(f'git remote get-url {remote}')
    parts = url.split('/')[-2:]
    if ':' in parts[0]:
        parts[0] = parts[0].split(':')[-1]
    return '/'.join(parts)


def get_version():
    """Get the current package version"""
    if osp.exists('setup.py'):
        return run('python setup.py --version', quiet=True)
    elif osp.exists('package.json'):
        return json.loads(Path('package.json').read_text())['version']


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
    r = requests.get(f'https://api.github.com/repos/{target}/pulls/{number}', headers=headers)
    data = r.json()
    title = data['title']
    number = data['number']
    url = data['url']
    user_name = data['user']['login']
    user_url = data['user']['html_url']
    return f"- {title} [{number}]({url}) [@{user_name}]({user_url})"


def get_source_repo(target, auth=None):
    """Get the source repo for a given repo.

    Parameters
    ----------
    target : str
        The GitHub organization/repo
    auth : str, optional
        The GitHub authorization token

    Returns
    -------
    str
        A formatted PR entry
    """
    api_token = auth or os.environ['GITHUB_ACCESS_TOKEN']
    headers = {'Authorization': 'token %s' % api_token}
    r = requests.get(f'https://api.github.com/repos/{target}', headers=headers)
    data = r.json()
    return data['source']['full_name']


def get_changelog_entry(branch, repo, path, version, *, auth=None, resolve_backports=False):
    """Get a changelog for the changes since the last tag on the given branch.

    Parameters
    ----------
    branch : str
        The target branch
    respository : str
        The GitHub organization/repo
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
    print(f'Getting changes to {repo} since {since}...')

    md = generate_activity_md(
        repo,
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
            if re.search(r"\[@meeseeksmachine\]", line) is not None:
                match = re.search(r"Backport PR #(\d+)", line)
                if match:
                    prs[ind] = format_pr_entry(match.groups()[0])

    prs = '\n'.join(prs).strip()

    # Move the contributor list to a heading level 3
    prs = prs.replace('## Contributors', '### Contributors')

    # Replace "*" unordered list marker with "-" since this is what
    # Prettier uses
    prs = re.sub(r'^\* ', '- ', prs)
    prs = re.sub(r'\n\* ', '\n- ', prs)

    output = f"""
## {version}

{full_changelog}

{prs}
""".strip()

    return output

def compute_sha256(path):
    """Compute the sha256 of a file"""
    sha256 = hashlib.sha256()

    with open(path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)

    return sha256.hexdigest()


def create_release_commit(version):
    """Generate a release commit that has the sha256 digests for the release files.
    """
    cmd = f'git commit -am "Publish v{version}" -m "SHA256 hashes:"'

    shas = dict()

    if osp.exists('setup.py'):
        files = glob('dist/*')
        if not len(files) == 2:
            raise ValueError('Missing distribution files')

        for path in files:
            sha256 = compute_sha256(path)
            shas[path] = sha256
            cmd += f' -m "{path}: {sha256}"'

    if osp.exists('package.json'):
        data = json.loads(Path('package.json').read_text())
        if not data.get('private', False):
            filename = run('npm pack')
            sha256 = compute_sha256(filename)
            shas[filename] = sha256
            os.remove(filename)
            cmd += f' -m "{filename}: {sha256}"'

    run(cmd)

    return shas


def _bump_version(version_spec, version_cmd=''):
    """Bump the version"""
    # Look for config files to determine version command if not given
    if not version_cmd:
        for name in 'bumpversion', '.bumpversion', 'bump2version', '.bump2version':
            if osp.exists(name + '.cfg'):
                version_cmd = 'bump2version'

        if osp.exists('tbump.toml'):
            version_cmd = version_cmd or TBUMP_CMD

        if osp.exists('pyproject.toml'):
            if 'tbump' in Path('pyproject.toml').read_text():
                version_cmd = version_cmd or TBUMP_CMD

        if osp.exists('setup.cfg'):
            if 'bumpversion' in Path('setup.cfg').read_text():
                version_cmd = version_cmd or 'bump2version'

    if not version_cmd:
        raise ValueError('Please specify a version bump command to run')

    # Bump the version
    run(f'{version_cmd} {version_spec}')


#"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
# Start CLI
#"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

class NaturalOrderGroup(click.Group):
    """Click group that lists commmands in the order added."""
    def list_cmds(self, ctx):
        return self.commands.keys()


@click.group(cls=NaturalOrderGroup)
def cli():
    """Release helper scripts."""
    pass


# Extracted common options
version_options = [
    click.option('--version-cmd', envvar='VERSION_CMD',
        help='The version command.')
]

branch_options = [
    click.option('--branch', envvar='BRANCH',
        help='The target branch.'),
    click.option('--remote', envvar='REMOTE',
        default='upstream',
        help='The git remote name.'),
    click.option('--repo', envvar='REPOSITORY',
        help='The git repo.')
]

changelog_options = branch_options + [
    click.option('--path', envvar='CHANGELOG',
        default="CHANGELOG.md",
        help='The path to the changelog file.'),
    click.option('--auth', envvar='GITHUB_ACCESS_TOKEN',
        help='The GitHub auth token.'),
    click.option('--resolve-backports', envvar='RESOLVE_BACKPORTS',
        is_flag=True,
        help='Resolve backport PRs to their originals.')
]


def add_options(options):
    """Add extracted common options to a click command."""
    # https://stackoverflow.com/a/40195800
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func
    return _add_options


@cli.command()
@click.option('--version-spec', envvar='VERSION_SPEC',
        required=True,
        help='The new version specifier.')
@add_options(version_options)
def bump_version(version_spec, version_cmd):
    """Bump the version."""
    _bump_version(version_spec, version_spec)


@cli.command()
@add_options(branch_options)
def prep_env(branch, remote, repo):
    """Prep the environment.  Set up Git, store variables if on GitHub Actions."""
    version = get_version()
    print(f'version={version}')

    # Get the branch
    if not branch:
        if os.environ.get('GITHUB_BASE_REF'):
            print('base ref')
            # GitHub Action PR Event
            branch = os.environ['GITHUB_BASE_REF']
        elif os.environ.get('GITHUB_REF'):
            import pdb; pdb.set_trace()
            print('github ref')
            # GitHub Action Push Event
            # e.g. refs/heads/feature-branch-1
            branch = os.environ['GITHUB_REF'].split('/')[-1]
        else:
            print('get branch')
            branch = get_branch()

    print(f'branch={branch}')

    gh_repo = os.environ.get('GITHUB_REPOSITORY')

    # Set up git config if on GitHub Actions
    if 'GITHUB_ACTIONS' in os.environ:
        # Use email address for the GitHub Actions bot
        # https://github.community/t/github-actions-bot-email-address/17204/6
        run('git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"')
        run('git config --global user.name "GitHub Action"')
        if not repo:
            # Get the source repo
            repo = get_source_repo(gh_repo)

        run(f'git remote add {remote} https://github.com/{repo}')

    if not repo:
        repo = get_repo(remote)

    run(f'git fetch {remote} {branch} --tags')

    # Make sure the workflow file is the same
    if gh_repo and repo != gh_repo:
        workflow == os.environ['GITHUB_WORKFLOW']
        path = f'./github/workflows/{workflow}'
        diff = run(f'git diff HEAD {remote}/{branch} -- {path}')
        msg = f'Workflow file {workflow} differs from upstream repo {repo}'
        if len(diff) != 0:
            print(diff)

            raise ValueError(msg)

    print(f'repo={repo}')

    final_version = re.match("([0-9]+.[0-9]+.[0-9]+)", version).groups()[0]
    is_prerelease = str(final_version != version).lower()
    print(f'is_prerelease={is_prerelease}')

    if 'GITHUB_ENV' in os.environ:
        Path(os.environ['GITHUB_ENV']).write_text(f"""
BRANCH={branch}
VERSION={version}
REPOSITORY={repo}
IS_PRERELEASE={is_prerelease}
""".strip())
        print('Wrote env variables to GITHUB_ENV file')


@cli.command()
@add_options(changelog_options)
def prep_changelog(branch, remote, repo, path, auth, resolve_backports):
    """Prep the changelog entry."""
    branch = branch or get_branch()

    # Make sure we have the branch fetched
    run(f'git fetch {remote} {branch}')

    # Get the new version
    version = get_version()

    ## Check out any files affected by the version bump
    run('git checkout .')

    # Get the existing changelog and run some validation
    changlog = Path(path).read_text()

    marker = f"{START_MARKER}\n{END_MARKER}"

    if marker not in changelog:
        raise ValueError('Missing insert marker for changelog')

    if changelog.find(START_MARKER) != changelog.rfind(START_MARKER):
        raise ValueError('Insert marker appears more than once in changelog')

    # Get the changelog entry
    repo = repo or get_repo(remote)
    entry = get_changelog_entry(f'{remote}/{branch}', repo, path, version, auth=auth, resolve_backports=resolve_backports)

    # Insert the entry into the file
    template = f"{START_MARKER}\n{entry}\n{END_MARKER}"
    changelog = changelog.replace(marker, template)

    Path(path).write_text(changelog)

    ## Verify the change for the PR
    # Only one uncommitted file
    assert len(run('git diff --numstat').splitlines()) == 1
    # New version entry in the diff
    diff = run(f'git --no-pager diff')
    assert f"# {version}" in diff

    # Follow up actions
    print("Changelog Prep Complete!")
    print("Create a PR for the Changelog change")


@cli.command()
@add_options(changelog_options)
@click.option('--output', envvar='CHANGELOG_OUTPUT',
              help='The output file for changelog entry.')
def extract_changelog(branch, remote, repo, path, auth, resolve_backports, output):
    """Extract the changelog entry."""
    if not version_spec:
        raise ValueError('No new version specified')

    branch = branch or get_branch()

    # Get the new version
    version = get_version()

    # Finalize the changelog
    changelog = Path(path).read_text()

    start = changelog.find(START_MARKER)
    end = changelog.find(END_MARKER)

    if start == -1 or end == -1:
        raise ValueError('Missing new changelog entry delimiter(s)')

    if start != changelog.rfind(START_MARKER):
        raise ValueError('Insert marker appears more than once in changelog')

    final_entry = changelog[start + len(START_MARKER): end]

    repo = repo or get_repo(remote)
    raw_entry = get_changelog_entry(f'{remote}/{branch}', repo, path, version, auth=auth, resolve_backports=resolve_backports)

    if f'# {version}' not in final_entry:
        raise ValueError(f'Did not find entry for {version}')

    final_prs = re.findall(r'\[#(\d+)\]', final_entry)
    raw_prs = re.findall(r'\[#(\d+)\]', raw_entry)

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
        Path(output).write_text(final_entry)

    # Clear out the insertion markers and rewrite
    changelog = changelog.replace(END_MARKER, '')
    marker = f'{START_MARKER}\n{END_MARKER}\n'
    changelog = changelog.replace(START_MARKER, marker)

    Path(path).write_text(changelog)


@cli.command()
@click.option('--test-cmd', envvar='PY_TEST_CMD',
              help='The command to run in the test venvs.')
def prep_python_dist(test_cmd):
    """Build and check the python dist files."""
    if not test_cmd:
        name = run('python setup.py --name')
        test_cmd = f'python -c "import {name}"'

    shutil.rmtree('./dist', ignore_errors=True)

    if osp.exists('./pyproject.toml'):
        run('python -m build .')
    else:
        run('python setup.py sdist')
        run('python setup.py bdist_wheel')

    run('twine check dist/*')

    # Create venvs to install sdist and wheel
    # run the test command in the venv
    for asset in ['gz', 'whl']:
        env_name = f"./test_{asset}"
        fname = glob(f'dist/*.{asset}')[0]
        # Create the virtual environment, upgrade pip,
        # install, and import
        run(f'python -m venv {env_name}')
        run(f'{env_name}/bin/python -m pip install -U -q pip')
        run(f'{env_name}/bin/pip install -q {fname}')
        run(f'{env_name}/bin/{test_cmd}')


@cli.command()
@add_options(branch_options)
@add_options(version_options)
@click.option('--post-version-spec', envvar='POST_VERSION_SPEC',
              help='The post release version (usually dev).')
def finalize_release(branch, remote, repo, version_cmd, post_version_spec):
    """Finalize the release prep - create commits and tag."""
    # Get the new version
    version = get_version()

    # Get the branch
    branch = branch or get_branch()

    # Check out the remote branch so we can push to it
    run(f'git checkout -b release {remote}/{branch}')

    # Create the release commit
    create_release_commit(version)

    # Create the annotated release tag
    tag_name = f'v{version}'
    run(f'git tag {tag_name} -a -m "Release {tag_name}"')

    # Bump to post version if given
    if post_version_spec:
        bump_version(post_version_spec, version_cmd)
        post_version = get_version()
        print(f'Bumped version to {post_version}')
        run(f'git commit -a -m "Bump to {post_version}"')

    # Verify the commits and tags
    diff = run(f'git --no-pager diff HEAD {remote}/{branch}')

    # If running in unit test, the branches are one and the same
    # Since the remote is a local directory
    url = run(f'git remote get-url {remote}')
    if url != os.getcwd():
        assert version in diff

    tags = run('git --no-pager tag').splitlines()
    assert tag_name in tags, tags

    # Follow up actions
    print("\n\n\n**********\n")
    print("Release Prep Complete!")
    print(r"Push to PyPI with \`twine upload dist/*\`")
    print(f"Push changes with `git push {remote} release --tags`")
    print("Make a GitHub release")


if __name__ == '__main__':
    cli()
