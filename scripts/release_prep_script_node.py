# Publish Action
from glob import glob
import os
import os.path as osp
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from create_release_commit import main as create_release_commit
from finalize_changelog import parser, main as finalize_changelog
from utils import run, get_version, get_name

# Extend the finalize_changelog CLI
parser.description = "Run the Release Prep Script"
parser.add_argument(
    "--version-command", "-vc",
    default="tbump --non-interactive --only-patch",
    help="""The version command to run""",
)
parser.add_argument(
    '--prerelease-command', '-pc',
    help="""The prelease command to run after bumping version"""
)
parser.add_argument(
    '--test-command', '-tc',
    default=f"npm run test",
    help="""The test command to run"""
)
parser.add_argument(
    '--post-version', '-pv',
    help="The post release version (usually a dev version)"
)


# TODO: scripts for:
   # bump_version --version_spec --version-command
   # finalize_changelog (done)
   # prep_node - build, test, publish --dry-run, pack, node -e "require('.')", shasum  
   # prep_python - build, test, shasum --test_command
   # finish_release_prep - commit, tag, validate

def main(args):
    """Handle the creation of a new changelog entry"""
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
        parts = branch.split('/')
        remote, branch = parts

    ## Bump the verison
    run(f'{version_command} {version_spec}')

    # Get the new version
    version = get_version()

    # Run the pre release command if given
    if prerelease_command:
        run(prerelease_command)

    # Finalize the changelog and write changelog entry file
    finalize_changelog(args)

    # Test the library
    run(test_command)

    # Create a commit with the shasum
    with TemporaryDirectory() as tempdir:
        output = run('npm pack --dry-run', stderr=subprocess.STDOUT)
        shasum = re.search('shasum:\W+([a-z0-9]+)', output).groups()[0]
        cmd = f'git commit -am "Publish v{version}" -m "shasum:" {shasum}'
        run(cmd)
        
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
    if post_version:
        assert post_version in diff

    tags = run('git --no-pager tag').splitlines()
    assert tag_name in tags, tags

    # Verify the changelog output for the GitHub release
 
    with open(output_file) as fid:
        output = fid.read()

    assert f'# {version}' in output

    # Follow up actions
    print("\n\n\n**********\n")
    print("Release Prep Complete!")
    print("Push to PyPI with \`twine upload dist/*\`")
    print(f"Push changes with \`git push {remote} {branch} --tags\`")
    print("Make a GitHub release with the following output")
    print(output)


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    main(args)
