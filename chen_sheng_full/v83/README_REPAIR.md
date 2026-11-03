# เฉินเซิ่ง V8.3 — ฉบับตรวจรับ

แก้ต่อจาก V8/V8.2 เดิม ใช้ WAV ต้นฉบับ 402.12 วินาที ไม่ตัดหรือเปลี่ยนถ้อยคำในเสียง ส่งออกภาพ 1080×1920, 60 fps, H.264 พร้อมเสียง AAC ที่เข้ารหัสจาก WAV ครั้งเดียวแล้ว copy mux

- 38 visual beats (อ่านจำนวนจริงจาก beats.json); จุดเปลี่ยนฉากอ้างเวลาเสียง ASR จริง
- ทหารเคลื่อนบนสมการเส้นเดียวกับเส้นทาง ใช้ภาพเจนโปร่งใส มีสถานะเดินทัพ ล้อมเมือง โต้กลับ ถอนตัว และธงเมืองเปลี่ยนหลังยึดได้
- ภาพบุคคล/เมืองเป็นภาพจำลอง ไม่ใช่ภาพเหมือนหรือการสำรวจโบราณสถาน
- ซับแก้คำสะกดจาก ASR และรับช่วงเวลาเดิมของคำที่ถอดผิด ไม่กระจายเวลาเท่ากันจากจำนวนคำ; ยังไม่รับรอง forced alignment และยังเทียบกับ SCRIPT MASTER เดิมครบถ้วนไม่ได้
- ทิศขึ้นเหนือสู่ Yuyang แสดงเป็นจุดหมายที่ได้รับคำสั่ง ยังไม่แสดงว่าเดินทางถึงจริง
- Xingyang ใช้เมืองโบราณตาม CHGIS แทนตัวเมืองปัจจุบัน; Hangu ใช้ด่านฉินที่ Lingbao ไม่ใช่ด่านฮั่นที่ Xin'an
- ไม่สร้างเส้นพรมแดนฉินหรือขอบเขตยึดครองปลอม วงแสงแสดงสถานะเฉพาะจุดเมือง
- เก็บฉบับ V8/V82 เดิมไว้ทั้งหมด

## การรัน

วาง assets/timing package ที่แนบใน `chen_sheng_full/v83/` และ WAV ต้นฉบับเป็น `chen_sheng_full/inputs/chen_sheng.wav` หรือกำหนด SOURCE_WAV

```bash
python -m pip install Pillow numpy pythainlp
python chen_sheng_full/v83/build_captions.py
python chen_sheng_full/render_v83.py
```

ต้องมี FFmpeg พร้อม libx264/libvpx-vp9/libass ตัว renderer ไม่ดึงแผนที่จากเครือข่ายอีก ใช้ภาพฐานที่มี extent กำกับและภาพกระเบื้องเดิมที่บันทึกไว้ในแพ็กสื่อ ผสมขอบเพื่อไม่ให้เห็นรอยต่อความละเอียด แต่บางบริเวณยังมีรายละเอียดพื้นหลังต่ำ

## ข้อที่ต้องตรวจรับแยกจากการถอดรหัส MP4

1. ฟังซับทุกช่วงเทียบเสียงและ SCRIPT MASTER เดิม โดยเฉพาะคำเชื่อมราว 282 วินาที
2. เสียงกล่าวถึงเมืองเฉินว่าเคลื่อนขึ้นเหนือ แต่จุดอ้างอิงเมืองแสดงทิศตะวันตกค่อนไปทางใต้จากเฉียว; เก็บเสียงเดิมและให้ภาพอิงภูมิศาสตร์จริง
3. ข้อความตำแหน่งเมืองจ้านในเสียงกล่าวตะวันตกเฉียงใต้ของหย่งเฉิง ขณะที่ CHGIS อยู่ทางตะวันตกค่อนไปเหนือ ต้องยืนยันบทก่อนแก้เสียง
4. หมุด Dazexiang เป็นจุดอ้างอิงตำบลปัจจุบัน; Xiachengfu เป็น area proxy แถบตะวันตกเฉียงเหนือของ Guoyang ไม่ใช่พิกัดจุดเสียชีวิตที่สำรวจแล้ว
5. ตัวเลขผลตรวจจริงและ hash อยู่ใน QA.json; ห้ามตีความ technical pass ว่าเป็นการอนุมัติภาพและบทโดยผู้ใช้

## แหล่งข้อมูลและเครดิต

- WAV ต้นฉบับ: เฉินเซิ่ง.wav, Library ID libfile_8cc754179ce88191b5a35f2406229d59
- ภาพฐาน Esri World Imagery; Esri / Vantor-Maxar / Earthstar Geographics / GIS Community; ภูมิศาสตร์ปัจจุบัน
- CHGIS, Harvard/Fudan, Temporal Gazetteer, point features queried at 209 BCE; records saved in geography/*.json. Source license stated CC BY-NC 4.0. https://tgaz.fudan.edu.cn/tgaz/placename/hvd_82124
- แหล่งโบราณคดีเมืองจื้อ: https://www.sxx.gov.cn/mhsx/sxgk/wwgj/60876925.html
- เรื่องกบฏและสถานที่: https://www.zhoukou.gov.cn/page_pc/zjzk/zkyx/rwzk/articleADD58E749CE0480F8AFED38AA38900CA.html
- ด่านฉินหานกู่: https://www.smxmuseum.com/News/Article/980
- พื้นที่ต้าเจ๋อเซียง: https://www.ahsz.gov.cn/hdjl/dwzsk/12870773.html
- ภาพประกอบ: image_gen สร้างในงานนี้; provenance.json ระบุการครอปและ hash
- Font: Noto Sans Thai, SIL Open Font License; ดูไฟล์ license ที่แนบ
