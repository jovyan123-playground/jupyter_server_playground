import argparse
import os
import os.path as osp
import sys
from tempfile import TemporaryDirectory

HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from utils import run

# Extend the finalize_changelog CLI
DESCRIPTION = "Test and Validate the npm Package"
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    '--test-command', '-tc',
    default="npm run test",
    help="""The test command to run"""
)


def main(args):
    """Test and validate the npm package"""
    # Test the library
    run(args.test_command)

    # Do a dry-run publish
    run('npm publish --dry-run')

    # npm pack
    tarball = osp.join(os.getcwd(), run('npm pack'))

    # Get the package data
    with open("package.json") as fid:
        data = json.load(fid)

    name = data['name']

    # Install in a temporary directory and verify import
    with TemporaryDirectory() as tempdir:
        run('npm init -y', cwd=tempdir)
        run(f'npm install {tarball}', cwd=tempdir)
        run(f'node -e "require(\'{name}\')"', cwd=tempdir)

    # Remove the tarball
    os.remove(tarball)


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    main(args)
