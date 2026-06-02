# Selectora

Selectora es un sistema personal i social de curadoria de continguts digitals. Es un monolit Django senzill: autenticacio estandard, admin, canals personals, items enriquits amb metadades i una presentacio visual tipus canal cultural.

## Funcionalitat actual

- Afegir una URL des del dashboard privat.
- Registre i entrada sense contrasenya amb magic link per email.
- Intent automatic d'obtenir metadades publiques: Open Graph, Twitter Cards, Schema.org JSON-LD, metadades HTML, imatges, favicon, autor, idioma, data, embed de YouTube quan es pot inferir.
- Edicio manual dels camps principals quan les metadades no existeixen o no son bones.
- Canal personal amb capcalera visual, targetes grans, rails horitzontals i seccions per tipus de contingut.
- Filtres GET per text, tipus, plataforma, autor i idioma.
- Ordenacio per mes recent, mes antic, titol, plataforma i tipus.
- Pagina de detall de cada item.
- Publicacio al canal propi des de Telegram mitjancant un bot i webhook.
- Admin millorat per `Channel`, `ContentItem` i `Tag`.
- Tests basics de metadades, creacio, filtres i acces public/privat.

## Estructura

```text
.
├── core/
│   ├── admin.py
│   ├── content_services.py     # Creacio d'items reutilitzable per web i Telegram
│   ├── forms.py
│   ├── metadata_fetcher.py     # Servei intern d'extraccio de metadades
│   ├── migrations/
│   ├── models.py               # Channel, ContentItem, Tag i integracions
│   ├── telegram.py             # Processament del webhook de Telegram
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── selectora_project/
│   └── settings/
│       ├── base.py
│       ├── dev.py
│       └── prod.py
├── static/css/styles.css
├── templates/
├── manage.py
├── requirements.txt
├── .env.example
└── .gitignore
```

## Instal.lacio local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Despres obre `http://127.0.0.1:8000/`.

## Us local

- Pagina publica inicial: `/`
- Login: `/accounts/login/`
- Magic link enviat: `/accounts/check-email/`
- Dashboard privat: `/dashboard/`
- Afegir contingut: `/items/new/`
- Detall d'item: `/items/<id>/`
- Editar item propi: `/items/<id>/edit/`
- Configuracio del canal i vinculacio Telegram: `/dashboard/channel/`
- Webhook de Telegram: `/integrations/telegram/webhook/`
- Canal public, si el canal esta marcat com a public: `/@<username>/`
- Admin Django: `/admin/`

Els usuaris es creen ara mateix amb `createsuperuser` o des de l'admin. Quan un usuari entra al dashboard o afegeix contingut, Selectora crea automaticament el seu canal personal si encara no existeix.

Per fer visible un canal publicament, marca `is_public` al model `Channel` des de l'admin.

## Telegram

Selectora pot publicar URLs al canal propi a partir de missatges enviats o compartits amb un bot de Telegram.

Flux:

1. Crea un bot amb BotFather i desa el token a `TELEGRAM_BOT_TOKEN`.
2. Defineix un secret llarg a `TELEGRAM_WEBHOOK_SECRET`.
3. Registra el webhook cap al teu domini HTTPS:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=https://selectora.example.com/integrations/telegram/webhook/" \
  -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
```

4. Entra a Selectora i ves a `/dashboard/channel/`.
5. Copia el comandament `/connect CODI` i envia'l al bot.
6. A partir d'aqui, envia o comparteix una URL amb el bot i Selectora la publicara al teu canal.

El webhook accepta missatges de text i captions amb URL. Si la URL ja existeix al mateix canal, no la duplica.

## Metadades

La logica viu a `core/metadata_fetcher.py` i esta separada de models i views.

Quan es desa una URL, Selectora intenta obtenir:

- titol, descripcio i imatge
- thumbnail, favicon i site name
- autor, idioma i data de publicacio
- tipus de contingut
- plataforma/font
- URL canonica
- embed URL quan es pot inferir
- etiquetes suggerides
- metadades originals dins `metadata_json`

Si la URL falla, triga massa o no te metadades, l'aplicacio no es trenca: crea un item amb dades fallback i permet editar-lo manualment.

## Dependències

- Django
- psycopg per PostgreSQL en produccio
- requests per descarregar HTML
- beautifulsoup4 per parsejar metadades HTML
- python-dateutil per normalitzar dates

## Tests

```bash
python manage.py test
```

## Variables d'entorn

El projecte llegeix variables directament de l'entorn. El fitxer `.env.example` documenta les claus esperades, pero Django no carrega `.env` automaticament per evitar una dependencia extra inicial.

En local, per defecte `manage.py` usa `selectora_project.settings.dev`.

Per produccio, configura com a minim:

```bash
export DJANGO_SETTINGS_MODULE=selectora_project.settings.prod
export DJANGO_SECRET_KEY='una-clau-secreta-llarga'
export DJANGO_ALLOWED_HOSTS='selectora.example.com'
export POSTGRES_DB='selectora'
export POSTGRES_USER='selectora'
export POSTGRES_PASSWORD='...'
export POSTGRES_HOST='localhost'
export TELEGRAM_BOT_TOKEN='...'
export TELEGRAM_WEBHOOK_SECRET='una-clau-llarga-per-validar-el-webhook'
```

## GitHub i branques

Repositori previst:

```text
https://github.com/jaumet/selectora
```

Branques recomanades:

```bash
git init
git branch -M dev
git remote add origin git@github.com:jaumet/selectora.git
git add .
git commit -m "Initial Django project"
git push -u origin dev

git checkout -b prod
git push -u origin prod
git checkout dev
```

## Desplegament Linux basic

1. Clona la branca `prod` al servidor.
2. Crea un virtualenv i instal.la `requirements.txt`.
3. Crea una base PostgreSQL i configura variables d'entorn de produccio.
4. Executa:

```bash
python manage.py migrate
python manage.py collectstatic
```

5. Serveix l'app amb Gunicorn o uWSGI darrere Nginx. Gunicorn encara no esta afegit a `requirements.txt`; afegeix-lo quan preparis el desplegament real.

## Properes passes

- Registre public d'usuaris.
- Edicio de configuracio del canal des del dashboard.
- Col.leccions i etiquetes mes potents.
- Extraccio de metadades en segon pla per no bloquejar requests.
- Integracions opcionals amb APIs externes.
- Imports des de plataformes externes.
