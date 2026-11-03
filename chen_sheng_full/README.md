# กบฏเฉินเซิ่ง — V8 full 60 FPS
This folder is separate from earlier 5-second previews. GitHub Actions rebuilds the 402.12-second original narration from 5 byte-preserved AAC parts, rebuilds the original channel's VP9 alpha mascot from 12 parts, and overlays the original PNG logo.

- Source narration: Thai 24 kHz mono WAV, 402.12 seconds, converted for repository transport to AAC 48 kbps.
- Geography: Esri World Imagery zoom 8 + Natural Earth present-day geographic outlines. Historic place pins are **approximations**.
- 36 geographic storyboard beats derived from the supplied Chen Sheng script.
- 1080x1920, 60 fps, H.264 CRF16, FFmpeg full-stream decode QA.
- 60fps MP4 is intended to be delivered as a GitHub Release asset, not committed into Git history.

**Important editorial limitation:** Scenes are timed proportionally by narrative weight, not forced-aligned with actual Thai words. This build retains original narration but has concise geographic scene headings, **not a fully speech-synchronized subtitle track**. Thus a technical PASS is not final V8 editorial approval. Exact narration-aligned Thai subtitles and visual review remain mandatory for final release readiness.

Original speech audio is kept complete; no generated or substituted narrator.
