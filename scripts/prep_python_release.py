import argparse
from glob import glob
import os
import os.path as osp
import sys


HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
from utils import run, get_version, get_name

# Extend the finalize_changelog CLI
DESCRIPTION = "Build and test the python package"
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    '--test-command', '-tc',
    default=f"pytest --pyargs {get_name()}",
    help="""The test command to run.  The command is run in a venv"""
)


def main(args):
    """Handle the creation of a new changelog entry"""
    # Get the new version and the package name
    version = get_version()
    name = get_name()

    # Test the library
    #run(args.test_command)

    # Build and check the dist files
    shutil.rmtree('./dist', ignore_errors=True)

    if osp.exists('./pyproject.toml'):
        run('python -m build .')
    else:
        run('python setup.py sdist')
        run('python setup.py bdist_wheel')

    run('twine check dist/*')

    # Install and import sdist and wheel in venv
    for asset in ['gz', 'whl']:
        env_name = f"./test_{asset}"
        fname = glob(f'dist/*.{asset}')[0]
        # Create the virtual environment, upgrade pip,
        # install, and import
        run(f'python -m venv {env_name}')
        run(f'{env_name}/bin/python -m pip install -U -q pip')
        run(f'{env_name}/bin/pip install -q {fname}')
        cmd = 'python -c "import {name}; print({name}.__version__)"'
        output = run(f'{env_name}/bin/{cmd}')
        assert output == version


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    main(args)
