#!/bin/bash
set -e

SERVER="root@165.22.16.53"
REMOTE_DEPLOY="/server/selectora.cc/deploy.sh"

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
git push origin dev

echo "==> Canviant a main..."
git checkout main

echo "==> Actualitzant main remota..."
git pull origin main

echo "==> Fusionant dev a main..."
git merge dev

echo "==> Pujant main..."
git push origin main

echo "==> Tornant a dev..."
git checkout dev

echo "==> Executant deploy al servidor..."
ssh "$SERVER" "$REMOTE_DEPLOY"

echo "==> Publicació completada."
