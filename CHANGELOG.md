# Changelog

Tots els canvis rellevants del projecte s'han de documentar aquí abans de fer push.

## Unreleased - 2026-06-10

Canvis acumulats des del darrer push (`28dcfe8`, `Ignore exported data file`).

### Afegit

- Capa informativa inicial a la portada amb logo, vídeo, botó de tancament, suport per `ESC` i opció `No mostris mes aquest missatge` persistida al navegador.
- Botó global `Compartir` a la navegació per compartir Selectora.
- Metadades `description`, canonical, Open Graph i Twitter Card per millorar la previsualització quan es comparteix Selectora.
- Suport PWA més complet: manifest enriquit, icones PNG `192x192`, `512x512`, `apple-touch-icon`, service worker amb cache bàsic, share target i botó `Instal·la`.
- Secció `Has estat veient` amb els darrers items visitats per l'usuari autenticat.
- Marca visual de visitat a la cantonada superior dreta de la imatge de cada item.
- Reordenació de seccions de portada per a usuaris autenticats amb drag and drop i persistència a `localStorage`.
- Menú compacte d'opcions d'usuari en mòbil, situat al costat del botó `+`.
- Eliminació segura d'items propis des del formulari d'edició amb panell d'alerta i checkbox de confirmació.

### Canviat

- Els botons `Temes` i `Cerca` ara són toggles: s'activen en clicar, es desactiven si es tornen a clicar i amaguen el panell corresponent.
- La navegació de compartir tanca el panell després de copiar enllaç o text.
- El formulari d'edició usa `Desa` i `Cancel·la` i afegeix `Elimina` només quan s'edita un item existent.
- Les seccions de portada tenen claus estables per poder recordar l'ordre personalitzat.
- El badge `Embed` passa a la cantonada superior esquerra per no tapar la marca de visitat.

### Tècnic

- Nova ruta `POST /items/<id>/delete/` per eliminar items propis.
- Nova helper de queryset `with_viewer_visit_state` per anotar items visitats sense consultes per card.
- El service worker es serveix amb capçalera `Service-Worker-Allowed: /`.
- S'han afegit proves per PWA, menú d'usuari mòbil, reordenació de seccions, marca de visitat i eliminació d'items.

### Verificació

- `python manage.py test`: 58 tests OK.
