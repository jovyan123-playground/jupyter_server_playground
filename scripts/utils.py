import os.path as osp
import shlex
from subprocess import check_output

HERE = osp.abspath(osp.dirname(__file__))

def run(cmd, **kwargs):
    """Run a command as a subprocess and get the output as a string"""
    print(f'+ {cmd}')
    return check_output(shlex.split(cmd), **kwargs).decode('utf-8').strip()


def get_branch():
    """Get the name of the current git branch"""
    return run('git branch --show-current')


def get_version():
    """Get the current package version"""
    parent = osp.abspath(osp.join(HERE, '..'))
    return run('python setup.py --version', cwd=parent)


def get_name():
    """Get the package name"""
    parent = osp.abspath(osp.join(HERE, '..'))
    return run('python setup.py --name', cwd=parent)