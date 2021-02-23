# Publish Action
set -ex

# Fetch the target branch
git remote add upstream https://github.com/${TARGET} || true
git fetch upstream ${BRANCH} --tags
ORIG_BRANCH=${BRANCH}
BRANCH="upstream/${BRANCH}"

## Install package with packaging deps
pip install -e .[packaging]

# Bump the verison
tbump --non-interactive --only-patch ${VERSION}

# Finalize the changelog and write changelog entry file
python scripts/finalize_changelog.py ${TARGET} ${CHANGELOG} --branch ${BRANCH} -o ${CHANGELOG_OUTPUT}

# Build and check the dist files
rm -f dist
python setup.py sdist
python setup.py bdist_wheel
twine check dist/*

# Test sdist in venv
virtualenv -p $(which python3) test_sdist
fname=$(ls dist/*.tar.gz)
./test_sdist/bin/pip install -q ${fname}[test]
./test_sdist/bin/pytest --pyargs "jupyter_server"

# Test wheel in venv
virtualenv -p $(which python3) test_wheel
fname=$(ls dist/*.whl)
./test_wheel/bin/pip install -q ${fname}[test]
./test_wheel/bin/pytest --pyargs "jupyter_server"

# Create the commit with shas
python scripts/create_release_commit.py

# Create the annotated release tag
git tag ${VERSION} -a -m "Release ${VERSION}"

# Bump to post version if given
if [ -n ${POST_VERSION} ]; then
    tbump --non-interactive --only-patch ${POST_VERSION}
    git commit -a -m "Bump to ${POST_VERSION}"
fi 

# Test push to PyPI
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# Verify the commits and tags
git --no-pager diff HEAD ${BRANCH} > diff.diff
cat diff.diff | grep ${VERSION}
if [ -n ${POST_VERSION} ]; then
    cat diff.dif | grep ${POST_VERSION}
fi
git --no-pager tag | grep ${VERSION}

# Verify the changelog output for the GitHub release
cat ${CHANGELOG_OUTPUT} 
cat ${CHANGELOG_OUTPUT} | grep "# ${VERSION}"

# Follow up actions
echo "Release Prep Complete!"
echo("Push to PyPI with `twine upload dist/*`")
echo("Push changes with `git push upstream ${ORIG_BRANCH} --tags`")
echo("Make a GitHub release with ${CHANGELOG_OUTPUT}")
