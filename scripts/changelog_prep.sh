# ChangeLog Action
set -ex

# Fetch the target branch
git fetch origin ${BRANCH}

## Install package with packaging deps
pip install -e .[packaging]

## Bump the verison
tbump --non-interactive --only-patch ${VERSION}

## Prepare the changelog
python scripts/prepare_changelog.py "jupyter-server/jupyter_server" CHANGELOG.md --branch ${BRANCH}

## Commit the changelog
git add CHANGELOG.md
git commit -m "Prep changelog for ${VERSION}"

## Check out any files affected by the version bump
git checkout .

## Verify the change for the PR
git diff --numstat | wc -l | grep "0"
git diff --numstat HEAD~1 HEAD | grep "1"
git --no-pager diff HEAD origin/${BRANCH} > diff.diff
cat diff.diff
cat diff.diff > grep "# ${VERSION}"

# Follow up actions
# - Create a PR