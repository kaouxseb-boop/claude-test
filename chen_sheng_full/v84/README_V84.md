# เฉินเซิ่ง V8.4 — visual story repair

Preserves the complete 402.12-second original narration, original logo and animated mascot. Output is 1080×1920 at 60 fps. This edition rebuilds the picture from referenced locations and cached terrain; it does not reuse the old army-stack picture segments.

Changes from V8.3:

- Shorter 74 px captions with 130→96→106→100% entrance animation, white/black outlines, and gold/red/cyan emphasis. A custom Thai dictionary preserves complete person and city names when wrapping and grouping.
- 107 illustration events anchored to phrases in the repaired source transcript. One primary event image appears at a time; screen placement avoids labels and city pins.
- Distinct, transparent city colors and glowing edges. Red/gold flags and army badges identify rebels/Qin. Colored areas are schematic local influence cells around reference places, not researched Qin county boundaries.
- March, siege, collision, defeat/retreat and capture are separate visual phases. At Aocang the rebel army retreats and the Qin force remains; siege alone does not change city ownership.
- PNG and MP4 intermediates are validated and renamed atomically, with unique MP4 temporary names.

The media/timing ZIP contains the finalized generated PNGs, atlas provenance, original voice, cached imagery, geographic records, cue data and QA. Source code is stored separately in Git. Extract the ZIP at repository root, then run:

```bash
PREP_ONLY=1 python chen_sheng_full/render_v84.py
python chen_sheng_full/v83/build_captions_v84.py
python chen_sheng_full/render_v84.py
python chen_sheng_full/v84/verify_v84.py
```

Dependencies: Pillow, numpy, scipy, pythainlp, FFmpeg/ffprobe with libass, libvpx-vp9 and libx264. The final overlay explicitly uses the VP9 decoder that preserves mascot alpha. Generated media is provided; no image service is needed to reconstruct the render.

QA separates technical file integrity, complete encoded narration preservation, extracted encoded-frame inspection and user approval. A successful decode does not prove enjoyable pacing or final subtitle accuracy. Direct continuous listening and comparison with the exact locked script remain unperformed. The unchanged narration retains two directional discrepancies noted in V8.3. Geographic sources and locality-proxy limitations are preserved in the media package.

No historic event photograph is claimed: portraits, troops and event illustrations are reconstructions. Original map imagery/credits and CHGIS location records are retained from the V8.3 source package.
