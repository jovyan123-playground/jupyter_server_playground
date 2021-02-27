import argparse
import os
import os.path as osp
import sys


HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from bump_version import main as bump_version
from create_release_commit import main as create_release_commit
from utils import run, get_version, get_branch

DESCRIPTION = "Finalize the Release Prep"
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    "--branch", "-b",
    default=get_branch(),
    help="""The target branch.""",
)
parser.add_argument(
    "--version-command", "-vc",
    default="tbump --non-interactive --only-patch",
    help="""The version command to run""",
)
parser.add_argument(
    '--post-version', '-pv',
    help="The post release version (usually a dev version)"
)


def main(args):
    """Finalize the release prep"""
    branch = args.branch
    post_version = args.post_version
    version_command = args.version_command

    remote = 'origin'
    orig_branch = branch
    if '/' in branch:
        parts = branch.split('/')
        remote, branch = parts

    # Get the new version
    version = get_version()

    # Create the release commit
    create_release_commit(version)

    # Create the annotated release tag
    tag_name = f'v{version}'
    run(f'git tag {tag_name} -a -m "Release {tag_name}"')

    # Bump to post version if given
    if post_version:
        bump_version(post_version, version_command)
        run(f'git commit -a -m "Bump to {post_version}"')

    # Verify the commits and tags
    diff = run(f'git --no-pager diff HEAD {orig_branch}')
    assert version in diff

    tags = run('git --no-pager tag').splitlines()
    assert tag_name in tags, tags

    # Follow up actions
    print("\n\n\n**********\n")
    print("Release Prep Complete!")
    print("Push to PyPI with \`twine upload dist/*\`")
    print(f"Push changes with \`git push {remote} {branch} --tags\`")
    print("Make a GitHub release")


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    main(args)

# TODO
#- refactor out the actions into changelog_core, release_core, release_test, changelog, and release
#  to save duplication
