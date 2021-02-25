# Publish Action
from glob import glob
import os
import os.path as osp
import re
import shutil
import sys


HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from create_release_commit import main as create_release_commit
from finalize_changelog import parser, main as finalize_changelog
from utils import run, get_version, get_name

# Extend the finalize_changelog CLI
parser.description = "Run the Release Prep Script"
parser.add_argument(
    '--prerelease-command', '-pc',
    help="""The prelease command to run after bumping version"""
)
parser.add_argument(
    '--test-command', '-tc',
    default=f"pytest --pyargs {get_name()}"
    help="""The prelease command to run after bumping version"""
)
parser.add_argument(
    '--post-version', '-pv',
    help="The post release version (usually a dev version)"
)


def main():
    """Handle the creation of a new changelog entry"""
    args = parser.parse_args(sys.argv[1:])
    branch = args.branch
    version_spec = args.version
    version_command = args.version_command
    prerelease_command = args.prerelease_command
    test_command = args.test_command
    post_version = args.post_version
    output_file = args.output

    assert output_file is not None, 'Output file not given!'

    remote = 'origin'
    orig_branch = branch
    if '/' in branch:
        remote, branch = branch.split('/')[0]

    ## Bump the verison
    run(f'{version_command} {version_spec}')

    # Get the new version
    version = get_version()

    # Run the pre release command if given
    if prerelease_command:
        run(prerelease_command)

    # Finalize the changelog and write changelog entry file - let it parse CLI
    finalize_changelog()

    # Build and check the dist files
    shutil.rmtree('./dist')

    if osp.exists('./pyproject.toml'):
        run('python -m build .')
    else:
        run('python setup.py sdist')
        run('python setup.py bdist_wheel')

    run('twine check dist/*')

    # Test sdist in venv
    run('virtualenv -p $(which python) test_sdist')
    fname = glob('dist/*.tar.gz')[0]
    run(f'./test_sdist/bin/pip install -q {fname}[test]')
    run(f'./test_sdist/bin/{test_command}')

    # Test wheel in venv
    run('virtualenv -p $(which python) test_wheel')
    fname = glob('dist/*.whl')[0]
    run(f'./test_sdist/bin/pip install -q {fname}[test]')
    run(f'./test_sdist/bin/{test_command}')

    # Create the commit with shas
    create_release_commit()

    # Create the annotated release tag
    run('git tag {version} -a -m "Release {version}"')

    # Bump to post version if given
    if post_version:
        run(f'{version_command} {post_version}')
        run('git commit -a -m "Bump to {post_version}"')

    # Verify the commits and tags
    diff = run(f'git --no-pager diff HEAD {orig_branch}')
    assert version in diff
    if post_version:
        assert post_version in diff

    tags = run('git --no-pager tag').splitlines()
    assert version in tags

    # Verify the changelog output for the GitHub release
 
    with open(output_file) as fid:
        output = fid.read()

    assert f'# {version}' in output

    # Follow up actions
    print("\n\n\n**********\n")
    print("Release Prep Complete!")
    print("Push to PyPI with \`twine upload dist/*\`")
    print("Push changes with \`git push {remote} {branch} --tags\`")
    print("Make a GitHub release with the following output")
    print(output)


if __name__ == "__main__":
    main()

# TODO
#- test the full workflow against the playground and the test pypi server