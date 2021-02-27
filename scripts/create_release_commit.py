import argparse
import json
from glob import glob
import hashlib
import os
import os.path as osp
import sys

HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from utils import get_version, run

BUF_SIZE = 65536
DEFAULT_GLOB = "dist/*"

DESCRIPTION = "Generate a git commit for a release."
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    "--version", "-v",
    default=get_version(),
    help="""The new version.""",
)


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


def main(version):
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


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    main(args.version, glob_pattern=args.glob)
