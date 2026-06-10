# Selectora

Selectora es un sistema personal i social de curadoria de continguts digitals. Es un monolit Django senzill: autenticacio estandard, admin, canals personals, items enriquits amb metadades i una presentacio visual tipus canal cultural.

## Funcionalitat actual

- Afegir una URL des del dashboard privat i enriquir-la automàticament amb metadades.
- Registre i entrada sense contrasenya amb `magic link` per email, protegit amb captcha aritmètic server-side i honeypot anti-spam.
- Portada compacta amb rails horitzontals, fletxes de navegació, canals públics i seccions dinàmiques.
- Panell inicial de presentació de Selectora amb logo, vídeo, tancament amb `ESC` i opció de no tornar-lo a mostrar.
- Botons `Temes` i `Cerca` en mode toggle: activen i amaguen els panells de filtres sense recarregar la pàgina.
- Usuaris autenticats poden reordenar les seccions de portada arrossegant-les; l'ordre queda recordat al navegador.
- Canal personal compacte amb capçalera visual, rails, seccions dinàmiques i filtres per text, tipus, plataforma, autor, idioma i ordre.
- Col·leccions públiques i privades amb pàgina pròpia, collage de portada i suport per compartir.
- Share module amb URL públiques per item, col·lecció, canal i la pròpia Selectora, botó de compartir, `copy link`, `copy text` i Web Share API quan existeix.
- Metadades Open Graph i Twitter Card per compartir Selectora amb títol, descripció i logo.
- Visibilitat bàsica `public` / `private` per items, col·leccions i canals.
- Seguiment d’items visitats per usuari, amb marca visual a les cards, secció `Has estat veient` i secció d’items pendents de veure quan hi ha login.
- Fitxa d’item amb vista pública, enllaç a l’origen, accions de compartir i interruptor per marcar visitat o pendent.
- Edició d’items amb eliminació segura: cal obrir el panell d’alerta, marcar confirmació i tornar a clicar `Elimina`.
- PWA instal·lable en mòbil amb manifest, icones PNG, service worker, share target i botó `Instal·la` a la navegació.
- Navegació responsive amb menú d’usuari compacte en mòbil.
- Publicació al canal propi des de Telegram mitjançant bot i webhook.
- Admin millorat per `Channel`, `ContentItem`, `Collection`, `Tag` i visites d’items.
- Tests de metadades, creació, filtres, accés public/privat, share module, visites, PWA, reordenació de seccions i eliminació d’items.

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
├── media/pwa/                # Icones PWA generades per instal·lació mòbil
├── manage.py
├── requirements.txt
├── .env.example
├── CHANGELOG.md
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
- Eliminar item propi: `POST /items/<id>/delete/`
- Configuracio del canal i vinculacio Telegram: `/dashboard/channel/`
- Explorar continguts públics: `/explore/`
- Manifest PWA: `/manifest.webmanifest`
- Service worker: `/sw.js`
- Share target PWA: `/share/`
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

La suite actual cobreix 58 tests.

## Changelog

Mantingues `CHANGELOG.md` actualitzat amb tots els canvis rellevants abans de cada push. L'entrada `Unreleased` resumeix el que hi ha al working tree des del darrer push.

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
