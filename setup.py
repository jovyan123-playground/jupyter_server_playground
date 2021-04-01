from setuptools import setup

try:
    from jupyter_packaging import create_cmdclass, install_npm
    cmdclass = create_cmdclass('jsdeps')
    cmdclass['jsdeps'] = install_npm()
except ImportError:
    cmdclass = {}

setup(cmdclass=cmdclass)
