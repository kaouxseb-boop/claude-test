# Chen Sheng Uprising / กบฏเฉินเซิ่ง — V8

## Deliverable
Technical 5-second opening preview with the supplied Thai narration excerpt:
- Real geographically registered satellite map (Esri World Imagery z7).
- Modern country outlines (Natural Earth 1:50m) separately colored with Jedi triple-glow, *not* represented as Qin historical borders.
- Qin capital Xianyang and Dazexiang markers are approximate modern geographic proxies.
- Generated 2D transparent Chen Sheng character PNG, historical reconstruction.
- 3240 x 5760 3x source before LANCZOS 1080 x 1920; 30 fps; H.264 CRF16.
- 5-sec AAC excerpt converted from the user’s 402.12-second, 24kHz mono WAV. This preview is **not** the full narration, and editorial text here is not word-aligned SRT.
- GitHub Actions on push runs actual FFmpeg encode/ffprobe/decode QA and publishes MP4/contact sheet/QA into `chen_sheng/preview/`.

## Story and historical reference
Sima Qian, *Shiji* 史記 卷四十八 陳涉世家: https://www.chinakongzi.org/kzsf/wxxs/mingpian/shiji/200705/t20070524_25198.htm

Historical itinerary (to be verified per scene before full render):
大澤鄉 (Dazexiang) -> 蕲 (Qi) -> 铚/酂/苦/柘/谯 -> 陳 (Chen, Huaiyang);
Wu Guang -> 荥阳 (Xingyang);
Zhou Wen -> 函谷關 (Hangu Pass) -> 戏 (Xi) -> 曹阳 (Caoyang) -> 渑池 (Mianchi);
Zhang Han -> 荥阳 -> 陳 -> 下城父 (Xiachengfu).

The map labels are modern reference proxies and do not indicate precise surveyed ancient GPS. No ancient Qin border polygon is claimed.

## Required before a full 402.12s film
Full narration WAV must be handed into the build workflow and aligned accurately with the script, scenes, captions, original channel logo/mascot, and complete AI-generated historical object atlas. A complete preview pass does not constitute full production acceptance.
