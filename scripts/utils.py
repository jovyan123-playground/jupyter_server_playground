import os.path as osp
import shlex
from subprocess import check_output

HERE = osp.abspath(osp.dirname(__file__))

def run(cmd, **kwargs):
    """Run a command as a subprocess and get the output as a string"""
    return check_output(shlex.split(cmd), **kwargs).decode('utf-8')

def get_branch():
    """Get the name of the current git branch"""
    return run('git branch --show-current')


def get_version():
    """Get the name of the current version"""
    parent = osp.abspath(osp.join(HERE, '..'))
    cmd = 'python setup.py --version'.split()
    return run(cmd, cwd=parent)