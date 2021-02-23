# ChangeLog Action
set -ex

# Handle the target branch
BRANCH=${BRANCH}
FULL_BRANCH="${REMOTE}/${BRANCH}"

## Install package with packaging deps
pip install -e .[packaging]

## Bump the verison
${VERSION_COMMAND} ${VERSION}

## Prepare the changelog
python scripts/prepare_changelog.py ${TARGET} ${CHANGELOG} --branch ${FULL_BRANCH}

## TODO allow a post changelog script
## This would be used by lumino to add JS packages

## Commit the changelog
git add CHANGELOG.md
git commit -m "Prep changelog for ${VERSION}"

## Check out any files affected by the version bump
git checkout .

## Verify the change for the PR
git diff --numstat | wc -l | grep "0"
git diff --numstat HEAD~1 HEAD | wc -l | grep "1"
git --no-pager diff HEAD ${FULL_BRANCH} > diff.diff
cat diff.diff | grep "# ${VERSION}"

# Follow up actions
echo "Changelog Prep Complete!"
echo "Create a PR for the Changelog change"
