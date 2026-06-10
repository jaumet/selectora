#!/bin/bash
set -e

SERVER="root@165.22.16.53"
REMOTE_DEPLOY="/server/selectora.cc/deploy.sh"
REMOTE_APP="/server/selectora.cc/prod"

COMMIT_MESSAGE="$1"

if [ -z "$COMMIT_MESSAGE" ]; then
  echo "Has d'escriure un missatge de commit."
  echo "Ús:"
  echo "./publish-prod.sh \"Canvis\""
  exit 1
fi

echo "==> Comprovant que som al repo..."
git status >/dev/null

echo "==> Canviant a dev..."
git checkout dev

echo "==> Afegint canvis..."
git add .

echo "==> Fent commit si hi ha canvis..."
if git diff --cached --quiet; then
  echo "No hi ha canvis per commitejar a dev."
else
  git commit -m "$COMMIT_MESSAGE"
fi

echo "==> Pujant dev..."
git push --force origin dev

echo "==> Canviant a main..."
git checkout main

echo "==> Alineant main amb dev..."
git merge --ff-only dev

echo "==> Pujant main..."
git push --force origin main

echo "==> Tornant a dev..."
git checkout dev

echo "==> Sincronitzant codi al servidor..."
ssh "$SERVER" "cd '$REMOTE_APP' && git fetch origin main && git checkout main && git reset --hard origin/main"

echo "==> Executant deploy al servidor..."
ssh "$SERVER" "$REMOTE_DEPLOY"

echo "==> Publicació completada."
