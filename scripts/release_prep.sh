# Publish Action
set -ex

# Handle the target branch
BRANCH=${BRANCH}
FULL_BRANCH="${REMOTE}/${BRANCH}"

## Install package with publishing deps
pip install -e .[publishing]

# Bump the verison
${VERSION_COMMAND} ${VERSION}

# For lab we would `yarn publish:js` and `yarn prepare:python-release` here
# For notebook we would `npm install -g po2json` here

# Finalize the changelog and write changelog entry file
python scripts/finalize_changelog.py ${TARGET} ${CHANGELOG} --branch ${FULL_BRANCH} -o ${CHANGELOG_OUTPUT}

# TODO: The rest is a separate script that takes an optional test command
# to run
#    - defaults to `python -m pytest --pyargs <package_name>`
#    - for lab it would run `release_test.sh`

# Build and check the dist files
rm -f dist
if [ -f ./pyproject.toml ]; then
    python -m build .
else
    python setup.py sdist
    python setup.py bdist_wheel
fi
twine check dist/*

# Test sdist in venv
NAME=$(python setup.py --name)
virtualenv -p $(which python3) test_sdist
fname=$(ls dist/*.tar.gz)
#./test_sdist/bin/pip install -q ${fname}[test]
#./test_sdist/bin/pytest --pyargs "${NAME}"

# Test wheel in venv
virtualenv -p $(which python3) test_wheel
fname=$(ls dist/*.whl)
#./test_wheel/bin/pip install -q ${fname}[test]
#./test_wheel/bin/pytest --pyargs "${NAME}"

# Create the commit with shas
python scripts/create_release_commit.py

# Create the annotated release tag
git tag ${VERSION} -a -m "Release ${VERSION}"

# Bump to post version if given
if [ -n ${POST_VERSION} ]; then
    ${VERSION_COMMAND} ${POST_VERSION}
    git commit -a -m "Bump to ${POST_VERSION}"
fi

# Test push to PyPI
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# Verify the commits and tags
git --no-pager diff HEAD ${FULL_BRANCH} > diff.diff
cat diff.diff | grep ${VERSION}
if [ -n ${POST_VERSION} ]; then
    cat diff.diff | grep ${POST_VERSION}
fi
git --no-pager tag | grep ${VERSION}

# Verify the changelog output for the GitHub release
cat ${CHANGELOG_OUTPUT} | grep "# ${VERSION}"

# Follow up actions
echo "\n\n\n**********\n"
echo "Release Prep Complete!"
echo "Push to PyPI with \`twine upload dist/*\`"
echo "Push changes with \`git push upstream ${BRANCH} --tags\`"
echo "Make a GitHub release with the following output"
cat ${CHANGELOG_OUTPUT} 