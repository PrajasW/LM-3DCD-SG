# Builds the GitHub Pages site in docs/ from the repository artefacts.
#
# The site is plain static HTML/CSS/JS with no build step: docs/index.html is the page,
# docs/assets/ holds the stylesheet and scripts, docs/img/ holds the figures.
# This script only refreshes the files that are generated from elsewhere in the repo, so
# that the page never shows an out-of-date report or figure.
#
# Usage:  bash scripts/build_pages.sh
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p docs/paper

# The mid-submission report, served directly from the page.
cp -v report/main.pdf docs/paper/mid-report.pdf

# Jekyll would otherwise strip files that begin with an underscore.
touch docs/.nojekyll

echo
echo "docs/ is ready. To publish:"
echo "  1. git add docs && git commit -m 'Update project page'"
echo "  2. git push origin main"
echo "  3. the site appears at https://prajasw.github.io/LM-3DCD-SG/"
echo
echo "If the site is not live yet, a repo admin has to enable it once:"
echo "  Settings -> Pages -> Source: Deploy from a branch -> main / (root) / docs"
