
# Variables to be set by env
version = "1.5.1"
branch = "master"
post_version = "1.6.0.dev0"
auth = ${GITHUB_ACCESS_TOKEN}

# ChangeLog Action

## Install package with packaging deps
pip install -e .[packaging]

## Bump the verison
tbump --non-interactive --only-patch ${version}

## Prepare the changelog
python scripts/prepare_changelog.py "jupyter-server/jupyter_server" CHANGELOG.md --branch ${branch} --auth ${auth}

## Commit the changelog
git add CHANGELOG.md
git commit -m "Prep changelog for ${version}"

## Check out any files affected by the version bump
git checkout .

## Here is where a PR to the branch would go
git --no-pager diff HEAD ${branch} > diff.diff
cat diff.diff
cat diff.diff > grep "# ${version}"

# Publish Action

## Bump the verison
tbump --non-interactive --only-patch ${version}

## Finalize the changelog and write changelog entry file
python scripts/finalize_changelog.py "jupyter-server/jupyter_server" CHANGELOG.md --branch ${branch} --auth ${auth} -o changelog_entry.md

## Build the dist files
rm -f dist
python setup.py sdist
python setup.py bdist_wheel
twine check dist/*

## Test sdist in venv
virtualenv -p $(which python3) test_sdist
fname=$(ls dist/*.tar.gz)
./test_sdist/bin/pip install -q ${fname}[test]
./test_sdist/bin/pytest --pyargs "jupyter_server"

# Test wheel in venv
virtualenv -p $(which python3) test_wheel
fname=$(ls dist/*.whl)
./test_wheel/bin/pip install -q ${fname}[test]
./test_wheel/bin/pytest --pyargs "jupyter_server"

## Create the commit with shas
python scripts/create_release_commit.py

## Create the release tag
git tag ${version} -m "Release ${version}"

# Bump to post version if given
if [ -n ${post_version} ]; then
    tbump --non-interactive --only-patch ${post_version}
    git commit -a -m "Bump to ${post_version}"
fi 

## Here is were we would push to PyPI
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

## Here is where we would push the commit(s) and tag(s) to the target branch
git --no-pager diff HEAD ${branch}
git --no-pager tag | grep ${version}

## Here is where we would make a GitHub release using changelog_entry.md
cat changelog_entry.md 
cat changelog_entry.md | grep "# ${version}"
