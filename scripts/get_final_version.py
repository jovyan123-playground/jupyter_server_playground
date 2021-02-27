import argparse
import re
import sys


DESCRIPTION = "Extract the final version"
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    "version",
    help="""The full version.""",
)


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    version = args.version
    print(re.match("(\d+\.\d+\.\d+)", version).groups()[0])
