import argparse
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
parser.add_argument(
    "--glob", "-g",
    default=DEFAULT_GLOB,
    help="""The glob pattern of file(s) report hashes on.""",
)


def main(version, glob_pattern="dist/*"):
    """Generate a release commit that has the sha256 digests for the release files.
    """
    cmd = f'git commit -am "Publish v{version}" -m "SHA256 hashes:"'
    files = glob(glob_pattern)
    if not len(files) == 2:
        raise ValueError('Missing distribution files')

    for path in files:

        sha256 = hashlib.sha256()

        with open(path, 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                sha256.update(data)

        sha256 = sha256.hexdigest()
        print(path, sha256)
        cmd += f' -m "{path}: {sha256}"'

    run(cmd)


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    main(args.version, glob_pattern=args.glob)