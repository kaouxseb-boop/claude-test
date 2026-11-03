# V8 · India to Kra · 5-second map test

This folder is separate from the existing **Holodomor V8** project in the same repository. No existing files or preview videos have been overwritten.

## What it makes
A 5-second 1080×1920 H.264 silent preview using:
- Actual Esri World Imagery satellite tiles, positioned with Web Mercator math.
- Official Natural Earth 1:50m geographic country polygons.
- An illustrative curved sea crossing from a **modern Chennai coordinate** toward the **modern Ranong coordinate**, followed by a short highlighted crossing to **modern Chumphon**.
- A zoom on the Kra Peninsula, cyan sea line, gold land line, anchored arrowhead, legible Thai labels/captions.

The sailing path is a **schematic interpretation**, NOT a documented ancient GPS route or proof that all ships departed from Chennai and crossed exactly at Ranong/Chumphon. Modern satellite terrain and borders are used to illustrate the geography, not ancient political borders.

This is an **unvoiced technical map test**. Original logo/mascot and TTS were not supplied here, so those QA gates remain unpassed.

## How to get MP4
Go to GitHub **Actions → Render India–Kra V8 5s → run → Artifacts → india-kra-v8-5s**.
A successful workflow also commits the publicly viewable clip to `kra/preview/V8_India_Kra_5sec_SILENT.mp4`.

## Run by yourself
```sh
python -m pip install Pillow
python kra/render.py
```
Requires FFmpeg, ffprobe, internet and around 3 GB RAM.

## Sources and credit
- Esri World Imagery: `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer` — imagery attribution: Esri and its imagery contributors.
- Natural Earth 1:50m boundaries: `https://github.com/nvkelso/natural-earth-vector` (public-domain geographic data).
- Thai Sarabun font: Google Fonts OFL.

For full V8 acceptance, a reviewer must check historical evidence, media license, real soundtrack alignment, logo/mascot and the exported 150 decoded frames. `qa.json` verifies the file/container gate only.
