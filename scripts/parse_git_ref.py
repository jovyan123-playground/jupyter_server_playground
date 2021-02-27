import argparse
import re
import sys


DESCRIPTION = "Extract the base name of a git ref"
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    "ref",
    help="""The git reference, # e.g. refs/heads/feature-branch-1""",
)


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    ref = args.ref
    print(ref.split('/')[-1])
