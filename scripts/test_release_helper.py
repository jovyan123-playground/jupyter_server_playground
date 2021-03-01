from unittest.mock import patch
import os
import os.path as osp
import shlex
from subprocess import run
import sys

from pytest import fixture

HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, osp.dirname(HERE))
from scripts import __main__ as main


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
    return tmp_path


@fixture
def py_package(git_repo):
    setuppy = git_repo.joinpath("setup.py")
    setuppy.write_text("""
import setuptools
import os

setup_args = dict(
    name="foo",
    version="0.0.1",
    url="foo url",
    author="foo author",
    py_module="foo",
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


def test_get_version(py_package):
    prev_dir = os.getcwd()
    os.chdir(py_package)
    assert main.get_version() == '0.0.1'
    print(str(py_package))
    cmd = shlex.split('tbump --non-interactive --only-patch 0.0.2a0')
    run(cmd, cwd=py_package)
    assert main.get_version() == '0.0.2a0'
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
         main.get_changelog_entry('foo', 'bar/baz', changelog, version)
         mocked_gen.assert_called_with('hi')

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
