# Publish Action
set -ex

# Handle the target branch
BRANCH=${BRANCH}
FULL_BRANCH="${REMOTE}/${BRANCH}"


# Provide default version bump command
if [ -z ${VERSION_COMMAND} ]; then
    VERSION_COMMAND="tbump --non-interactive --only-patch"
fi

# Bump the verison
${VERSION_COMMAND} ${VERSION}

# Run the pre release command if given
if [ -n ${PRELEASE_COMMAND} ]; then
    # For lab we run `yarn publish:js && yarn prepare:python-release`
    ${PRELEASE_COMMAND}
fi

# Finalize the changelog and write changelog entry file
python scripts/finalize_changelog.py ${TARGET} ${CHANGELOG} --branch ${FULL_BRANCH} -o ${CHANGELOG_OUTPUT}

NAME=$(python setup.py --name)

# Use a test command if given or default to pytest
if [ -z ${TEST_COMMAND} ]; then
    TEST_COMMAND="pytest --pargs $NAME"
fi

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
virtualenv -p $(which python3) test_sdist
fname=$(ls dist/*.tar.gz)
source ./test_sdist/bin/activate
pip install -q ${fname}[test]
${TEST_COMMAND}
source ./test_sdist/bin/deactivate

# Test wheel in venv
virtualenv -p $(which python3) test_wheel
fname=$(ls dist/*.whl)
source ./test_wheel/bin/activate
pip install -q ${fname}[test]
${TEST_COMMAND}
source ./test_wheel/bin/deactivate

# Create the commit with shas
python scripts/create_release_commit.py

# Create the annotated release tag
git tag ${VERSION} -a -m "Release ${VERSION}"

# Bump to post version if given
if [ -n ${POST_VERSION} ]; then
    ${VERSION_COMMAND} ${POST_VERSION}
    git commit -a -m "Bump to ${POST_VERSION}"
fi

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

# TODO
#- test the full workflow against the playground and the test pypi server
