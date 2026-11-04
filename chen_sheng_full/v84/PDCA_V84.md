# Chen Sheng V8.4 — feedback applied

User feedback: subtitles looked too small, too long, weakly animated and insufficiently colored. Visual storytelling lacked event icons/effects and had dead air. The user reiterated distinct city colors and glowing Jedi borders and asked for the best quality.

| Observed cause in V8.3 | V8.4 correction | Evidence/check |
| --- | --- | --- |
| 37 coarse scenes with mostly the same marching formations | 107 source-phrase illustration events; separate collision, retreat and capture phases | `visual_events.json`, encoded event samples |
| 60 px captions with a small 110→100% entrance | 74 px captions, 130→96→106→100% entrance, gold/red/cyan emphasis | Caption bounds and actual encoded frames |
| Thai tokenizer split historical names | Custom dictionary for person/place names | Aocang and other name cues remain intact in ASS/SRT |
| Missing subject-specific illustrations | Retain final generated PNGs and alpha provenance; use event-specific subject art | Asset manifest and event inventory |
| Only small city circles indicated control | Distinct transparent city cells, glowing edges, red/gold side flags; capture changes coincide with narration | Before/after capture bases and final encoded event frames |
| Qin victory at Aocang needs an explicit losing-side action | Rebel formation retreats/fades while Qin remains; image switches from collision to Qin victory | Scene 25 before/during/after samples |
| File/decode success was overused as a proxy for story quality | Separate technical/audio results from visual inspection and user approval | `QA_V84.json`; no blanket user approval |

Intermediate file failures are blocked before delivery by decoding PNGs, unique temporary MP4 paths, frame-count checks, atomic publication and bounded scene rebuilds. These checks do not replace visual review.

Exact locked-script comparison and continuous direct listening have not been performed in this environment. Source narration is preserved and its two earlier directional discrepancies remain documented. Geographic cells are illustrative local influence areas, not researched ancient county boundaries.
