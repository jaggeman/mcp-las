#!/usr/bin/env bash
# Dedikerat runtime-konto för MCP-LAS Cloud Run-tjänsten.
#
# BAKGRUND
# `gcloud run deploy mcp-las` kördes tidigare utan --service-account. Då kör
# tjänsten som projektets default compute service account
# (PROJEKTNUMMER-compute@developer.gserviceaccount.com), som i GCP:s
# standarduppsättning har rollen Editor på HELA paygap-prod. Eftersom Novro
# ligger i samma projekt och samma Firestore-databas innebar det att
# LAS-servern hade läs- och skrivbehörighet till Novros anställningsuppgifter,
# löner och lönekartläggningar. Ingen kodväg gjorde det - men behörigheten
# fanns, och en bugg eller en komprometterad nyckel hade räckt.
#
# VAD DET HÄR SKRIPTET GÖR
# Skapar ett eget konto för LAS runtime med enbart Firestore-åtkomst, inte
# Editor. Kör det en gång, sätt sedan GitHub-variabeln (sista steget) så
# plockar ci.yml upp kontot vid nästa deploy.
#
# VAD DET INTE GÖR
# roles/datastore.user gäller hela databasen - Firestore har ingen IAM på
# collection-nivå. Kontot kan alltså fortfarande läsa Novros collections i den
# DELADE databasen. Det här steget tar bort Editor-behörigheten (stort), men
# fullständig separation kräver att LAS får en egen databas eller ett eget
# projekt. Se avsnittet om separation i CLAUDE.md.
set -euo pipefail

PROJECT="paygap-prod"
ACCOUNT="mcp-las-runtime"
EMAIL="${ACCOUNT}@${PROJECT}.iam.gserviceaccount.com"

echo "==> Skapar tjänstekontot ${EMAIL}"
gcloud iam service-accounts create "${ACCOUNT}" \
  --project="${PROJECT}" \
  --display-name="MCP-LAS Cloud Run runtime" \
  --description="Kör mcp-las. Endast Firestore. Aldrig Novro-behörigheter." \
  || echo "    (finns redan - fortsätter)"

echo "==> Ger Firestore-åtkomst (och ingenting annat)"
gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${EMAIL}" \
  --role="roles/datastore.user" \
  --condition=None

echo "==> Låter deploy-kontot agera som runtime-kontot"
# Utan detta nekas deployen: den som driftsätter måste ha actAs på det konto
# tjänsten ska köra som.
gcloud iam service-accounts add-iam-policy-binding "${EMAIL}" \
  --project="${PROJECT}" \
  --member="serviceAccount:github-deployer@${PROJECT}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

cat <<EOF

==> Klart. Sista steget görs i GitHub:

    gh variable set GCP_RUNTIME_SERVICE_ACCOUNT --body "${EMAIL}"

    (eller Settings -> Secrets and variables -> Actions -> Variables)

==> Verifiera efter nästa deploy att tjänsten faktiskt bytt konto:

    gcloud run services describe mcp-las \\
      --project=${PROJECT} --region=europe-west3 \\
      --format='value(spec.template.spec.serviceAccountName)'

    Ska skriva ut ${EMAIL}, inte ...-compute@developer.gserviceaccount.com

==> Kontrollera att default compute-kontot inte längre behövs av LAS, och
    granska separat om det fortfarande ska ha Editor för Novros skull:

    gcloud projects get-iam-policy ${PROJECT} \\
      --flatten="bindings[].members" \\
      --filter="bindings.members:compute@developer.gserviceaccount.com" \\
      --format="table(bindings.role)"

EOF
