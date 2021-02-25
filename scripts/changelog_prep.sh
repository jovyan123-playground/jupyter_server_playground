# ChangeLog Action
set -ex

# Handle the target branch
BRANCH=${BRANCH}
FULL_BRANCH="${REMOTE}/${BRANCH}"

# Provide default version bump command
if [ -z ${VERSION_COMMAND} ]; then
    VERSION_COMMAND="tbump --non-interactive --only-patch"
fi

## Bump the verison
${VERSION_COMMAND} ${VERSION}

## Prepare the changelog
python scripts/prepare_changelog.py ${TARGET} ${CHANGELOG} --branch ${FULL_BRANCH}

# Run the pre release command if given
if [ -n ${POSTPROCESS_CHANGELOG_COMMAND} ]; then
    ##  lumino would add JS package versions to the changelog entry
    ${POSTPROCESS_CHANGELOG_COMMAND}
fi

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
