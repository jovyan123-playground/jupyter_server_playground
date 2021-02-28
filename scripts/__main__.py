import json
import os
import os.path as osp
import re
import shlex
from subprocess import check_output

import click

HERE = osp.abspath(osp.dirname(__file__))
START_MARKER = '<!-- <START NEW CHANGELOG ENTRY> -->'
END_MARKER = '<!-- <END NEW CHANGELOG ENTRY> -->'
BUF_SIZE = 65536


def run(cmd, **kwargs):
    """Run a command as a subprocess and get the output as a string"""
    if not kwargs.pop('quiet', False):
        print(f'+ {cmd}')
    return check_output(shlex.split(cmd), **kwargs).decode('utf-8').strip()


def get_branch():
    """Get the local git branch"""
    return run('git branch --show-current', quiet=True)


def get_repository(remote):
    """Get the remote repository org and name"""
    url = run(f'git remote get-url {remote}')
    parts = url.split('/')[-2:]
    if ':' in parts[0]:
        parts[0] = parts[0].split(':')[-1]
    return ''.join(parts)


def get_version():
    """Get the current package version"""
    parent = osp.abspath(osp.join(HERE, '..'))
    if osp.exists(osp.join(parent, 'setup.py')):
        return run('python setup.py --version', cwd=parent, quiet=True)
    elif osp.exists(osp.join(parent, 'package.json')):
        with open(osp.join(parent, 'package.json')) as fid:
            return json.load(fid)['version']


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


def get_changelog_entry(branch, repository, path, version, auth=None, resolve_backports=False):
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
                match = re.search(r"Backport PR #(\d+)", line)
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

    if osp.exists('setup.py'):
        files = glob('dist/*')
        if not len(files) == 2:
            raise ValueError('Missing distribution files')

        for path in files:
            sha256 = compute_sha256(path)
            cmd += f' -m "{path}: {sha256}"'

    if osp.exists('package.json'):
        with open('package.json') as fid:
            data = json.load(fid)
        if not data.get('private', False):
            filename = run('npm pack')
            sha256 = compute_sha256(filename)
            os.remove(filename)
            cmd += f' -m "{filename}: {shasum}'

    run(cmd)

@click.group()
def cli():
    pass


@cli.command()
@click.option('--version', help='The new version specifier.',
              envvar='VERSION')
@click.option('--version-command', help='The version command.',
              default="tbump --non-interactive --only-patch",
              envvar='VERSION_COMMAND')
@click.option('--remote', help='The git remote name.',
              default='upstream', envvar='REMOTE')
@click.option('--repository', help='The git repository.',
              envvar='GITHUB_REPOSITORY')
def prep_env(version, version_command, remote, repository):
    """Prep the environment.  Bump the version, set up Git, store variables if on GitHub Actions."""
    if not version:
        raise ValueError('No new version specified')

    # Bump the version
    run(f'{version_command} {version}')

    # Get the branch
    if 'GITHUB_BASE_REF' in os.environ:
        # GitHub Action PR Event
        branch = os.environ['GITHUB_BASE_REF']
    elif 'GITHUB_REF' in os.environ:
        # GitHub Action Push Event
        # e.g. refs/heads/feature-branch-1
        branch = os.environ['GITHUB_REF'].split('/')[-1]
    else:
        branch = get_branch()

    print(branch)

    if not repository:
        repository = get_repository(remote)

    # Set up Git Config if on github actions
    if 'GITHUB_ACTIONS' in os.environ:
        # Use email address for the GitHub Actions bot
        # https://github.community/t/github-actions-bot-email-address/17204/6
        run('git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"')
        run('git config --global user.name "GitHub Action"')
        run(f'git remote add {remote} https://github.com/{repository}')

    run(f'git fetch {remote} {branch} --tags')

    print(repository)

    final_version = re.match("([0-9]+.[0-9]+.[0-9]+)", version).groups()[0]
    print(final_version)

    if 'GITHUB_ENV' in os.environ:
        with open(os.environ['GITHUB_ENV'], 'w') as fid:
            fid.write(f'BRANCH={branch}\n')
            fid.write(f'REMOTE={remote}\n')
            fid.write(f'FINAL_VERSION={final_version}')


@cli.command()
@click.option('--branch', help='The target branch.',
              envvar='BRANCH')
@click.option('--remote', help='The git remote name.',
              default='upstream', envvar='REMOTE')
@click.option('--repository', help='The git repository.',
              envvar='GITHUB_REPOSITORY')
@click.option('--path', help='The path to the changelog file.',
              envvar='CHANGELOG')
@click.option('--auth', help='The GitHub auth token.',
              envvar='GITHUB_ACCESS_TOKEN')
@click.option('--resolve-backports', is_flag=True,
              help='Resolve backport PRs to their originals.',
              envvar='RESOLVE_BACKPORTS')
def prep_changelog(branch, repository, path, auth):
    """Prep the changelog entry."""
    branch = branch or get_branch()

    # Get the new version
    version = get_version()

    ## Check out any files affected by the version bump
    run('git checkout .')

    # Get the existing changelog and run some validation
    with open(path) as fid:
        changelog = fid.read()

    marker = f"{START_MARKER}\n{END_MARKER}"

    if marker not in changelog:
        raise ValueError('Missing insert marker for changelog')

    if changelog.find(START_MARKER) != changelog.rfind(START_MARKER):
        raise ValueError('Insert marker appears more than once in changelog')

    # Get the changelog entry
    entry = get_changelog_entry(f'{remote}/{branch}', repository, path, version, auth=auth, resolve_backports=resolve_backports)

    # Insert the entry into the file
    template = f"{START_MARKER}\n{entry}\n{END_MARKER}"
    changelog = changelog.replace(marker, template)

    with open(path, 'w') as fid:
        fid.write(changelog)

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
@click.option('--branch', help='The target branch.',
              envvar='BRANCH')
@click.option('--remote', help='The git remote name.',
              default='upstream', envvar='REMOTE')
@click.option('--repository', help='The git repository.',
              envvar='GITHUB_REPOSITORY')
@click.option('--path', help='The path to the changelog file.',
              envvar='CHANGELOG')
@click.option('--auth', help='The GitHub auth token.',
              envvar='GITHUB_ACCESS_TOKEN')
@click.option('--resolve-backports', is_flag=True,
              help='Resolve backport PRs to their originals.',
              envvar='RESOLVE_BACKPORTS')
@click.option('--version', help='The new version specifier.',
              envvar='VERSION')
@click.option('--version-command', help='The version command.',
              default="tbump --non-interactive --only-patch",
              envvar='VERSION_COMMAND')
@click.option('--output', help='The output file for changelog entry.',
              envvar='CHANGELOG_OUTPUT')
def prep_release(branch, repository, path, auth, resolve_backports, version, version_command, output):
    """Prep the release - version bump and extract changelog entry."""
    if not version:
        raise ValueError('No new version specified')

    # Bump the version
    run(f'{version_command} {version}')

    # Finalize the changelog
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
        with open(output, 'w') as fid:
            fid.write(final_entry)

    # Clear out the insertion markers
    changelog = changelog.replace(END_MARKER, '')
    marker = f'{START_MARKER}\n{END_MARKER}\n'
    changelog = changelog.replace(START_MARKER, marker)

    with open(path, 'w') as fid:
        fid.write(changelog)


@cli.command()
@click.option('--test-command', help='The command to run in a venv.',
              envvar='PY_TEST_COMMAND')
def prep_python(test_command):
    """Build and check the python dist files."""
    if not test_command:
        test_command = f'python -c "import {name}; print({name}.__version__)"'

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
        output = run(f'{env_name}/bin/{test_command}')
        assert output == version


@cli.command()
@click.option('--test-command', help='The command to run in isolated install.',
              envvar='NPM_TEST_COMMAND')
def prep_npm(test_command):
    """Validate the npm package."""
    # Do a dry-run publish
    run('npm publish --dry-run')

    # npm pack
    tarball = osp.join(os.getcwd(), run('npm pack'))

    # Get the package data
    with open("package.json") as fid:
        data = json.load(fid)

    name = data['name']

    if not test_command:
        test_command = f'node -e "require(\'{name}\')"'

    # Install in a temporary directory and verify import
    with TemporaryDirectory() as tempdir:
        run('npm init -y', cwd=tempdir)
        run(f'npm install {tarball}', cwd=tempdir)
        run(test_command, cwd=tempdir)

    # Remove the tarball
    os.remove(tarball)


@cli.command()
@click.option('--branch', help='The target branch.',
              envvar='BRANCH')
@click.option('--remote', help='The git remote name.',
              default='upstream', envvar='REMOTE')
@click.option('--post-version',
              help='The post release version (usually dev).',
              envvar='POST_VERSION')
@click.option('--version-command', help='The version command.',
              default="tbump --non-interactive --only-patch",
              envvar='VERSION_COMMAND')
def finalize_release(branch, remote, post_version, version_command):
    """Finalize the release prep - create commits and tag."""
    # Get the new version
    version = get_version()

    # Create the release commit
    create_release_commit(version)

    # Create the annotated release tag
    tag_name = f'v{version}'
    run(f'git tag {tag_name} -a -m "Release {tag_name}"')

    # Bump to post version if given
    if post_version:
        run(f'{version_command} {post_version}')
        run(f'git commit -a -m "Bump to {post_version}"')

    # Verify the commits and tags
    diff = run(f'git --no-pager diff HEAD {orig_branch}')
    assert version in diff

    tags = run('git --no-pager tag').splitlines()
    assert tag_name in tags, tags

    # Follow up actions
    print("\n\n\n**********\n")
    print("Release Prep Complete!")
    print(r"Push to PyPI with \`twine upload dist/*\`")
    print(f"Push changes with `git push {remote} {branch} --tags`")
    print("Make a GitHub release")


if __name__ == '__main__':
    cli()
