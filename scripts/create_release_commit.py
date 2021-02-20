import argparse
import hashlib
import os
import shlex
import subprocess
import sys

BUF_SIZE = 65536

DESCRIPTION = "Generate a git commit for a release."
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    "version",
    help="""The new version.""",
)

def main():
    """Generate a release commit that has the sha256 digests for the release files.
    """
    args = parser.parse_args(sys.argv[1:])
    cmd = f'git commit -am "Publish {args.version}" -m "SHA256 hashes:"'
    files = os.listdir('dist')
    if not len(files) == 2:
        raise ValueError('Missing distribution files')

    for fname in files:
        if not args.version in fname:
            raise ValueError('Wrong version in distribution files')

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

    subprocess.run(shlex.split(cmd))


if __name__ == "__main__":
    main()
