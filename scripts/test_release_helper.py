from unittest.mock import call, patch
from click.testing import CliRunner
import json
import os
import os.path as osp
import shlex
import shutil
from subprocess import run
import sys

from pytest import fixture

HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, osp.dirname(HERE))
from scripts import __main__ as main


CHANGELOG_ENTRY = """
# master@{2019-09-01}...master@{2019-11-01}

([full changelog](https://github.com/executablebooks/github-activity/compare/479cc4b2f5504945021e3c4ee84818a10fabf810...ed7f1ed78b523c6b9fe6b3ac29e834087e299296))

## Merged PRs

* defining contributions [#14](https://github.com/executablebooks/github-activity/pull/14) ([@choldgraf](https://github.com/choldgraf))
* updating CLI for new tags [#12](https://github.com/executablebooks/github-activity/pull/12) ([@choldgraf](https://github.com/choldgraf))
* fixing link to changelog with refs [#11](https://github.com/executablebooks/github-activity/pull/11) ([@choldgraf](https://github.com/choldgraf))
* adding contributors list [#10](https://github.com/executablebooks/github-activity/pull/10) ([@choldgraf](https://github.com/choldgraf))
* some improvements to `since` and opened issues list [#8](https://github.com/executablebooks/github-activity/pull/8) ([@choldgraf](https://github.com/choldgraf))
* Support git references etc. [#6](https://github.com/executablebooks/github-activity/pull/6) ([@consideRatio](https://github.com/consideRatio))
* adding authentication information [#2](https://github.com/executablebooks/github-activity/pull/2) ([@choldgraf](https://github.com/choldgraf))
* Mention the required GITHUB_ACCESS_TOKEN [#1](https://github.com/executablebooks/github-activity/pull/1) ([@consideRatio](https://github.com/consideRatio))

## Contributors to this release

([GitHub contributors page for this release](https://github.com/executablebooks/github-activity/graphs/contributors?from=2019-09-01&to=2019-11-01&type=c))

[@betatim](https://github.com/search?q=repo%3Aexecutablebooks%2Fgithub-activity+involves%3Abetatim+updated%3A2019-09-01..2019-11-01&type=Issues) | [@choldgraf](https://github.com/search?q=repo%3Aexecutablebooks%2Fgithub-activity+involves%3Acholdgraf+updated%3A2019-09-01..2019-11-01&type=Issues) | [@consideRatio](https://github.com/search?q=repo%3Aexecutablebooks%2Fgithub-activity+involves%3AconsideRatio+updated%3A2019-09-01..2019-11-01&type=Issues)
"""


@fixture
def git_repo(tmp_path):
    def r(cmd):
        run(shlex.split(cmd), cwd=tmp_path)

    r('git init')
    r('git checkout -b foo')
    r('touch foo.txt')
    r('git add .')
    r('git commit -m "foo"')
    r('git tag v0.0.1')
    r('git checkout -b bar')
    r(f'git remote add upstream {tmp_path}')
    r('git config user.name "snuffy"')
    r('git config user.email "snuffy@sesame.com"')
    return tmp_path


@fixture
def py_package(git_repo):
    def r(cmd):
        run(shlex.split(cmd), cwd=git_repo)

    setuppy = git_repo.joinpath("setup.py")
    setuppy.write_text("""
import setuptools
import os

setup_args = dict(
    name="foo",
    version="0.0.1",
    url="foo url",
    author="foo author",
    author_email="foo email",
    py_modules=["foo"],
    description="foo package",
    long_description="long_description",
    long_description_content_type="text/markdown",
    zip_safe=False,
    include_package_data=True,
)
if __name__ == "__main__":
    setuptools.setup(**setup_args)
""")

    tbump = git_repo.joinpath("tbump.toml")
    tbump.write_text(r"""
[version]
current = "0.0.1"
regex = '''
  (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)
  ((?P<channel>a|b|rc|.dev)(?P<release>\d+))?
'''

[git]
message_template = "Bump to {new_version}"
tag_template = "v{new_version}"

[[file]]
src = "setup.py"
""")

    foopy = git_repo.joinpath("foo.py")
    foopy.write_text('print("hello, world!")')

    changelog = git_repo.joinpath("CHANGELOG.md")
    changelog.write_text(f"""
# Changelog

{main.START_MARKER}
{main.END_MARKER}
""")

    pyproject = git_repo.joinpath("pyproject.toml")
    pyproject.write_text("""
[build-system]
requires = ["setuptools>=40.8.0", "wheel"]
build-backend = "setuptools.build_meta"
""")

    readme = git_repo.joinpath("README.md")
    readme.write_text("Hello from foo project")

    r('git add .')
    r('git commit -m "initial python package"')
    return git_repo


@fixture
def npm_package(git_repo):
    def r(cmd):
        run(shlex.split(cmd), cwd=git_repo)

    r('npm init -y')
    r('git add .')
    r('git commit -m "initial npm package"')
    return git_repo


def test_get_branch(git_repo):
    prev_dir = os.getcwd()
    os.chdir(git_repo)
    assert main.get_branch() == 'bar'
    os.chdir(prev_dir)


def test_get_repository(git_repo):
    prev_dir = os.getcwd()
    os.chdir(git_repo)
    repo = f'{git_repo.parent.name}/{git_repo.name}'
    assert main.get_repository('upstream') == repo
    os.chdir(prev_dir)


def test_get_version_python(py_package):
    prev_dir = os.getcwd()
    os.chdir(py_package)
    assert main.get_version() == '0.0.1'
    print(str(py_package))
    cmd = shlex.split('tbump --non-interactive --only-patch 0.0.2a0')
    run(cmd, cwd=py_package)
    assert main.get_version() == '0.0.2a0'
    os.chdir(prev_dir)


def test_get_version_npm(npm_package):
    prev_dir = os.getcwd()
    os.chdir(npm_package)
    assert main.get_version() == '1.0.0'
    print(str(py_package))
    cmd = shlex.split('npm version patch')
    run(cmd, cwd=npm_package)
    assert main.get_version() == '1.0.1'
    os.chdir(prev_dir)


def test_format_pr_entry():
    with patch('scripts.__main__.requests.get') as mocked_get:
         resp = main.format_pr_entry('foo', 121, auth='baz')
         mocked_get.assert_called_with('https://api.github.com/repos/foo/pulls/121', headers={'Authorization': 'token baz'})

    assert resp.startswith('- ')


def test_get_changelog_entry(py_package):
    changelog = py_package / 'CHANGELOG.md'
    prev_dir = os.getcwd()
    os.chdir(py_package)
    version = main.get_version()

    with patch('scripts.__main__.generate_activity_md') as mocked_gen:
        resp = main.get_changelog_entry('foo', 'bar/baz', changelog, version)
        mocked_gen.assert_called_with('bar/baz', since='v0.0.1',
            kind='pr', auth=None)

    assert f'## {version}' in resp

    with patch('scripts.__main__.generate_activity_md') as mocked_gen:
        mocked_gen.return_value = CHANGELOG_ENTRY
        resp = main.get_changelog_entry('foo', 'bar/baz', changelog, version, resolve_backports=True, auth='bizz')
        mocked_gen.assert_called_with('bar/baz', since='v0.0.1',
            kind='pr', auth='bizz')

    assert f'## {version}' in resp
    os.chdir(prev_dir)


def test_compute_sha256(py_package):
    sha = '9ff86928054a7791ed023c799702b0fa343f4a371127c43bdf583d4b0ee3a6f3'
    assert main.compute_sha256(py_package / 'CHANGELOG.md') == sha


def test_create_release_commit(py_package):
    def r(cmd):
        run(shlex.split(cmd), cwd=py_package)

    prev_dir = os.getcwd()
    os.chdir(py_package)
    r('tbump --non-interactive --only-patch 0.0.2a0')
    version = main.get_version()
    r('python -m build .')
    shas = main.create_release_commit(version)
    assert 'dist/foo-0.0.2a0.tar.gz' in shas
    assert 'dist/foo-0.0.2a0-py3-none-any.whl' in shas
    shutil.rmtree(py_package / 'dist')

    # Add an npm package and test with that
    r('npm init -y')
    r('git add .')
    with open(py_package / "package.json") as fid:
        data = json.load(fid)
    data['version'] = version
    with open(py_package / "package.json", "w") as fid:
        json.dump(data, fid, indent=4)
    txt = (py_package / "tbump.toml").read_text()
    txt += """
[[file]]
src = "package.json"
search = '"version": "{current_version}"'
"""
    (py_package / "tbump.toml").write_text(txt)
    r('tbump --non-interactive --only-patch 0.0.2a1')
    version = main.get_version()
    r('python -m build .')
    shas = main.create_release_commit(version)
    npm_dist = f'{py_package.name}-0.0.2a1.tgz'
    assert npm_dist in shas
    assert 'dist/foo-0.0.2a1.tar.gz' in shas
    os.chdir(prev_dir)


def test_prep_env(py_package, tmp_path):
    prev_dir = os.getcwd()
    os.chdir(py_package)
    runner = CliRunner()

    # Standard local run with no env variables
    result = runner.invoke(main.cli, ['prep-env', '--version-spec', '1.0.1'])
    assert result.exit_code == 0
    assert 'branch=bar' in result.output
    assert 'version=1.0.1' in result.output
    assert 'is_prerelease=false' in result.output

    # With GITHUB_BASE_REF (Pull Request)
    result = runner.invoke(main.cli, ['prep-env'], env=dict(GITHUB_BASE_REF='foo', VERSION_SPEC='1.0.1'))
    assert result.exit_code == 0
    assert 'branch=foo' in result.output

    # Full GitHub Actions simulation (Push)
    env_file = tmp_path.joinpath('github.env')
    version_spec = '1.0.1a1'
    env = dict(
        GITHUB_REF='refs/heads/foo', VERSION_SPEC=version_spec,
        GITHUB_ACTIONS='true', GITHUB_REPOSITORY='foo/bar',
        GITHUB_ENV=str(env_file)
    )
    with patch('scripts.__main__.run') as mock_run:
        # Fake out the version response
        mock_run.return_value = version_spec
        result = runner.invoke(main.cli, ['prep-env'], env=env)
        mock_run.assert_has_calls([
            call(f'tbump --non-interactive --only-patch {version_spec}'),
            call('python setup.py --version', quiet=True),
            call('git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"'),
            call('git config --global user.name "GitHub Action"'),
            call('git remote add upstream https://github.com/foo/bar'),
            call('git fetch upstream foo --tags')
        ])

    assert result.exit_code == 0
    text = env_file.read_text()
    assert 'BRANCH=foo' in text
    assert f'VERSION={version_spec}' in text
    assert 'IS_PRERELEASE=true' in text

    os.chdir(prev_dir)


def test_prep_changelog(py_package):
    prev_dir = os.getcwd()
    os.chdir(py_package)
    runner = CliRunner()
    changelog = py_package / 'CHANGELOG.md'

    with patch('scripts.__main__.generate_activity_md') as mocked_gen:
        mocked_gen.return_value = CHANGELOG_ENTRY
        result = runner.invoke(main.cli, ['prep-changelog', '--path', changelog])
    assert result.exit_code == 0
    text = changelog.read_text()
    assert main.START_MARKER in text
    assert main.END_MARKER in text
    assert '[#14](https://github.com/executablebooks/github-activity/pull/14)' in text
    os.chdir(prev_dir)


# Notes
# Create a python package and git local repo
#   https://github.com/jupyter/jupyter-packaging/blob/master/tests/conftest.py
# Stub out generate_activity_md - all local
# Need to make a target branch and add tags - see script below
# Then we can run the following cases:
#   - local (no GITHUB_ set except GITHUB_ACCESS_TOKEN)
#   - PR - GITHUB_BASE_REF, GITHUB_REPOSITORY, and GITHUB_ACTIONS set
#   - PUSH - GITHUB_REF, GITHUB_REPOSITORY, and GITHUB_ACTIONS set
# Also need to stub out requests.get for format_pr_entry - add fake meeseeks


# GIT BOOTSTRAP SCRIPT
# git init
# git checkout -b bar
# git checkout -b foo
# touch foo.txt
# git add .
# git commit -m "foo"
# git tag v0.0.1
# git checkout bar
# git remote add upstream ${PWD}
