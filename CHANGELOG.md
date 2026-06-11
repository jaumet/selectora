# Changelog

Tots els canvis rellevants del projecte s'han de documentar aquí abans de fer push.

## Unreleased - 2026-06-10

Canvis acumulats des del darrer push (`28dcfe8`, `Ignore exported data file`).

### Afegit

- Capa informativa inicial a la portada amb logo, vídeo, botó de tancament, suport per `ESC` i opció `No mostris mes aquest missatge` persistida al navegador.
- Pàgina pública `/que-es-selectora/` amb hero visual, logo horitzontal, autor i graella de funcionalitats de Selectora.
- La pàgina `Què és Selectora?` incorpora el vídeo de presentació al costat del text de la hero.
- La pàgina `Què és Selectora?` afegeix la feature d'items privats marcats amb llaç vermell.
- Botó global `Compartir` a la navegació per compartir Selectora.
- Metadades `description`, canonical, Open Graph i Twitter Card per millorar la previsualització quan es comparteix Selectora.
- Suport PWA més complet: manifest enriquit, icones PNG `192x192`, `512x512`, `apple-touch-icon`, service worker amb cache bàsic, share target i botó `Instal·la`.
- Secció `Has estat veient` amb els darrers items visitats per l'usuari autenticat.
- Marca visual de visitat a la cantonada superior dreta de la imatge de cada item.
- Sistema de valoració d'items amb una valoració principal i fins a 3 matisos.
- Registre de visites per item, incloses les visites pròpies, amb data, comptador total i sparkline temporal a la fitxa d'item.
- Els usuaris poden valorar també els seus propis items.
- Reordenació de seccions de portada per a usuaris autenticats amb drag and drop i persistència a `localStorage`.
- Menú compacte d'opcions d'usuari en mòbil, situat al costat del botó `+`.
- Eliminació segura d'items propis des del formulari d'edició amb panell d'alerta i checkbox de confirmació.
- Captcha aritmètic server-side al formulari d'entrada/registre amb resposta guardada en sessió.
- Honeypot anti-spam ocult al formulari d'entrada/registre.
- La sessió iniciada amb magic link dura 60 dies.
- Document `HOT_TO_Telegram.txt` amb passes per configurar `@selectoracc_bot`, webhook, vinculació i ús en grups.
- Documents `HOW_TO-selectora-hierarqui.txt`, `HOW_TO-set-resend.txt` i `HOW_TO_Telegram.txt` reformatejats amb Markdown ric.
- Ruta del Django admin canviada de `/admin/` a `/entra-per-darrere/`.
- Fallback d'embed de YouTube ampliat per reconèixer URLs `/live/`, `/embed/`, `/v/` i `youtube-nocookie.com`, útil quan els items arriben des de Telegram i YouTube no retorna metadades completes.
- Els items existents sense `embed_url` es refresquen quan es torna a afegir la mateixa URL, evitant que un YouTube creat prèviament des de Telegram quedi sense reproductor incrustat.
- El fallback de YouTube ara també s'aplica quan YouTube retorna HTML sense metadades útils o una pàgina intermèdia, usant sempre la URL original enviada.
- `og:image` i `twitter:image` passen d'un SVG a `media/logos/selectora-og-horizontal.png` en format PNG 1200x630 per millorar la previsualització a WhatsApp.
- Migració perquè tots els canals existents passin a públics i els canals nous neixin públics per defecte.

### Canviat

- El formulari de canal ja no exposa el control `is_public`; la visibilitat del contingut es decideix a cada item o col·lecció.
- El formulari d'item mostra la visibilitat al costat del títol amb estat visual verd `Públic` o vermell `Privat` i text explicatiu.
- La fitxa d'item mostra de manera destacada el canal d'origen, amb miniatura, nom del canal i autor/a abans del títol.
- La fitxa d'item incorpora una zona visual de vot sota el media/embed per valorar publicacions.
- Les cards de seccions mostren comptadors compactes de visites i valoracions a l'esquerra d'`Obrir` i `Compartir`.
- Les valoracions i matisos a les cards es mostren desglossats per icona i contador, amb el nom de cada valoració o matís al hover.
- La fitxa d'item mostra també les valoracions i matisos al costat del sparkline de visites.
- El botó `Instal·la` de la navegació queda destacat amb el taronja del logo.
- La navegació reparteix les accions principals al centre (`Temes`, `+`, `Cerca`), agrupa `Temes`/`Cerca` sota una lupa en mòbil i mostra Dashboard, canal i sortir com a icones amb hover.
- El botó global de compartir Selectora passa a icona amb hover `Comparteix Selectora.cc`.
- `Temes` i `Cerca` passen a icones amb hover `Cerca per temes` i `Cerca`; el botó `+` mostra hover `Afegeix continguts`.
- El grup central de la nav queda ordenat com `Què és?`, compartir, `+`, lupa i `#`; el compartir surt de la dreta i usa icona de compartir.
- El botó `Instal·la` mostra hover `Instal·la al mòbil` i les visites a les cards usen icona amb hover `Visites`.
- Les cards d'items privats mostren un ribbon vermell `Privat` només al propietari.
- El propietari veu els seus items privats també al seu canal, marcats amb el ribbon `Privat`.
- Els botons `Temes` i `Cerca` ara són toggles: s'activen en clicar, es desactiven si es tornen a clicar i amaguen el panell corresponent.
- La navegació de compartir tanca el panell després de copiar enllaç o text.
- El formulari d'edició usa `Desa` i `Cancel·la` i afegeix `Elimina` només quan s'edita un item existent.
- Les seccions de portada tenen claus estables per poder recordar l'ordre personalitzat.
- El badge `Embed` passa a la cantonada superior esquerra per no tapar la marca de visitat.

### Tècnic

- Nova ruta `POST /items/<id>/delete/` per eliminar items propis.
- Nova helper de queryset `with_viewer_visit_state` per anotar items visitats sense consultes per card.
- El model `Channel` força `is_public=True` en desar i l'admin ja no exposa aquest camp.
- Els scripts de publicació alineen `main` amb `dev`, fan push forçat quan cal i sincronitzen el clon de producció amb `origin/main` abans del deploy.
- Nou model `ContentItemRating`, ruta `POST /items/<id>/rating/` i admin per consultar valoracions.
- Nou model `ContentItemViewEvent` per desar cada visita amb data i generar mètriques temporals.
- El service worker es serveix amb capçalera `Service-Worker-Allowed: /`.
- S'han afegit proves per PWA, menú d'usuari mòbil, reordenació de seccions, marca de visitat i eliminació d'items.
- S'han afegit proves per validar captcha correcte, captcha incorrecte i honeypot omplert.
- S'han afegit proves per validar canals públics per defecte i el nou control visual de visibilitat dels items.

### Verificació

- `python manage.py test`: 74 tests OK.
