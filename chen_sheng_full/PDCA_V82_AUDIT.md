# Chen Sheng V8 -> V8.2: PDCA visual audit (3 November 2026)
Status: **NOT APPROVED** for publication. This file records observed evidence; passing FFmpeg decode is not visual acceptance.

## Actual evidence
- Input release: `chen-sheng-v8-full-60fps` (402.12 sec; 1080x1920; 60 fps)
- Observed native middle frame at t=180s: “หลี่โหยวป้องกันเมือง” over largely empty satellite terrain; one red pin, very small top-right logo, mascot at lower right.
- Large opaque top headline occupies excessive height.
- No spoken-line subtitles at that moment; only a scene title.
- No legible troop formations, fortresses, battle state, captured-city shading, or visible advancing route in the inspected frame.
- Natural Earth geometry is modern geographic reference only; do not portray it as Qin dynasty surveyed boundaries.

## Root causes in renderer
1. Whole scene is rendered to one static JPG, looped for many seconds. This creates slideshow pacing.
2. Map camera centers each destination regardless of origin, leaving long routes and theater context offscreen.
3. Troop and fortress AI atlas never loaded; route merely draws a straight line when both coordinates appear.
4. Audio scene durations allocated by hand weights rather than measured narration timing.
5. Subtitle track absent from full film.
6. A technical report named “PASS” validates container/codec/frames, not historical and visual standards.

## V8.2 repair gates
- Gate A: extract native frame sheets at 0, 30, 60, ... end, plus frames at every scene transition. Verify all labels, safe areas, mascot.
- Gate B: ASR speech timing draft followed by correction against user-locked Thai script. Full transcript must cover every spoken phrase with no omissions.
- Gate C: rebuild actual map-motion events with moving army formations and directional route traces, changing controlled city states; do not stretch historical area borders.
- Gate D: raise 1-2-line spoken subtitles above mascot, white/black stroke, gold keywords, <=0.18s pop, and no full-width dark panel.
- Gate E: produce 10-20s corrective prototype; inspect decoded native frames; only then rerender all 402s.
- Gate F: compare native render with approved India-Kra sharpness and reject pixelation, harsh zooming, fake map borders.
- Gate G: verify audio duration and contents, 60fps frames and no decode errors, then visual scene QA. Preserve V8 release as historical baseline; publish V8.2 separately.
