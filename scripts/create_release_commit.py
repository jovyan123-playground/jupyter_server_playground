import argparse
import hashlib
import os
import os.path as osp
import sys

HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from utils import get_version, run

BUF_SIZE = 65536

DESCRIPTION = "Generate a git commit for a release."
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    "--version", "-v",
    default=get_version(),
    help="""The new version.""",
)

def main(version):
    """Generate a release commit that has the sha256 digests for the release files.
    """
    cmd = f'git commit -am "Publish v{version}" -m "SHA256 hashes:"'
    files = os.listdir('dist')
    if not len(files) == 2:
        raise ValueError('Missing distribution files')

    for fname in files:
        if not str(version) in fname:
            raise ValueError(f'Version {version} not found in {fname}')

        sha256 = hashlib.sha256()

        with open(os.path.join('dist', fname), 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                sha256.update(data)

        sha256 = sha256.hexdigest()
        print(fname, sha256)
        cmd += f' -m "{fname}: {sha256}"'

    run(cmd)


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    main(args.version)