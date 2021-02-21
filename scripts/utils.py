import os.path as osp
from subprocess import check_output

HERE = osp.abspath(osp.dirname(__file__))


def get_branch():
    """Get the name of the current git branch"""
    return check_output('git branch --show-current'.split()).decode('utf-8')


def get_version():
    """Get the name of the current version"""
    parent = osp.abspath(osp.join(HERE, '..'))
    cmd = 'python setup.py --version'.split()
    return check_output(cmd, cwd=parent).decode('utf-8')