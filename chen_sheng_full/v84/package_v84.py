"""Bundle media and timing; keep source code in the linked Git commit."""
import json
import sys
import zipfile
from pathlib import Path

P=Path(__file__).resolve().parent;ROOT=P.parent;OLD=ROOT/'v83'
commit=sys.argv[1]
assert len(commit)==40 and all(c in '0123456789abcdef' for c in commit)
qa=json.loads((P/'QA_V84.json').read_text())
assert qa['technical_file_pass'] and qa['complete_encoded_reference_preserved']
resume={'edition':'Chen Sheng V8.4 REVIEW','source_code_commit':commit,'source_code_url':'https://github.com/kaouxseb-boop/claude-test/tree/'+commit,'video_sha256':qa['sha256'],'source_audio_sha256':qa['source_integrity']['sha256'],'instructions':['Download source code at the exact commit URL.','Unpack this media/timing archive at repository root.','Run PREP_ONLY=1 python chen_sheng_full/render_v84.py','Run python chen_sheng_full/v83/build_captions_v84.py','Run python chen_sheng_full/render_v84.py','Run python chen_sheng_full/v84/verify_v84.py'],'known_limits':qa['known_limits'],'user_final_approval':False}
(P/'RESUME_V84.json').write_text(json.dumps(resume,ensure_ascii=False,indent=2))
files=[]
for f in (OLD/'assets').iterdir():
 if f.is_file() and not f.name.startswith('.') and f.name not in {'atlas.webp','mascot.webm'}:files.append(f)
for f in (OLD/'tiles').glob('*.jpg'):
 if not f.name.startswith('fallback_'):files.append(f)
files.extend((OLD/'geography').glob('*.json'))
for name in ['beats.json','asr_turbo.json','asr_repairs.json','corrections.tsv','source_integrity.json','narration_reference.m4a']:files.append(OLD/name)
for f in (P/'assets').iterdir():
 if f.is_file() and f.suffix in {'.png','.webm','.ttf','.txt','.json'} and f.name!='generated_contact.png':files.append(f)
for name in ['captions_v84.ass','ChenSheng_V84_Thai.srt','caption_units_v84.json','caption_qa_v84.json','transcript_review_v84.json','label_positions.json','visual_events.json','QA_V84.json','RESUME_V84.json']:files.append(P/name)
files.extend(sorted(P.glob('encoded_contact_*.jpg')))
files.extend(sorted(P.glob('regression_*.jpg')))
delivery=ROOT.parents[1]/'delivery';delivery.mkdir(exist_ok=True)
target=delivery/'ChenSheng_V84_Media_Timing_Resume.zip'
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in files:z.write(f,'chen_sheng_full/'+f.relative_to(ROOT).as_posix())
 z.write(ROOT/'assets/logo.png','chen_sheng_full/assets/logo.png')
 z.write(ROOT.parents[1]/'inputs/เฉินเซิ่ง.wav','chen_sheng_full/inputs/chen_sheng.wav')
 assert z.testzip() is None
print(json.dumps({'archive':str(target),'bytes':target.stat().st_size,'files':len(files)+2,'source_code_commit':commit}),flush=True)
