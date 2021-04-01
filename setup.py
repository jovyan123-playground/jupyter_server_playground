from setuptools import setup

try:
    from jupyter_packaging import wrap_installers, npm_builder
    cmdclass = wrap_installers(pre_develop=npm_builder())
except ImportError:
    cmdclass = {}

setup(cmdclass=cmdclass)
