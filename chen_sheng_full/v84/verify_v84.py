"""Check the encoded deliverable; extract actual event frames for visual review."""
import concurrent.futures
import hashlib
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

P=Path(__file__).resolve().parent; OLD=P.parent/'v83'; F=P/'ChenSheng_V84_FULL_60FPS_REVIEW.mp4'
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(p)]))
def audiohash(p):return subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0','-f','hash','-hash','sha256','-']).decode().strip()
q=probe(F);v=next(s for s in q['streams'] if s['codec_type']=='video')
assert (v['width'],v['height'],v['avg_frame_rate'],v['nb_read_frames'])==(1080,1920,'60/1','24127'),v
result=subprocess.run(['ffmpeg','-v','error','-i',str(F),'-f','null','-'],capture_output=True,text=True)
assert result.returncode==0 and not result.stderr.strip(),result.stderr
expected=audiohash(OLD/'narration_reference.m4a');actual=audiohash(F)
if expected!=actual:
 repaired=F.with_name('audio_restored_v84.mp4')
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(F),'-i',str(OLD/'narration_reference.m4a'),'-map','0:v:0','-map','1:a:0','-c','copy','-movflags','+faststart',str(repaired)],check=True)
 assert audiohash(repaired)==expected
 repaired.replace(F);actual=expected;q=probe(F)
assert abs(float(q['format']['duration'])-402.12)<.05
events=json.loads((P/'visual_events.json').read_text());beats=json.loads((OLD/'beats.json').read_text())
# At least one encoded frame per event and every scene. Frame time falls after entry motion.
times=sorted(set(round(e['time']+.4,3) for e in events)|set(round(b['start']+.7,3) for b in beats))
shots=P/'encoded_frames';shots.mkdir(exist_ok=True)
def extract(item):
 i,t=item;path=shots/f'event_{i:03}.jpg';subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(F),'-frames:v','1',str(path)],check=True)
 return path
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:paths=list(ex.map(extract,enumerate(times)))
for n,start in enumerate(range(0,len(paths),12),1):
 canvas=Image.new('RGB',(1440,1980),(5,12,20));d=ImageDraw.Draw(canvas)
 for j,path in enumerate(paths[start:start+12]):
  im=Image.open(path).resize((360,640),Image.Resampling.LANCZOS);x=(j%4)*360;y=(j//4)*660
  canvas.paste(im,(x,y+20));d.text((x+6,y+3),f'{start+j:03} | {times[start+j]:.2f}s',fill='white')
 canvas.save(P/f'encoded_contact_{n:02}.jpg',quality=92)
caption=json.loads((P/'caption_qa_v84.json').read_text())
report={
 'edition':'V8.4 REVIEW','technical_file_pass':True,'resolution':[1080,1920],'fps':'60/1','video_frames':24127,
 'duration':q['format']['duration'],'bytes':F.stat().st_size,'sha256':hashlib.sha256(F.read_bytes()).hexdigest(),
 'complete_encoded_reference_preserved':expected==actual,'audio_reference_pcm_hash':expected,'mp4_decoded_audio_hash':actual,
 'source_integrity':json.loads((OLD/'source_integrity.json').read_text()),'decode_errors':result.stderr,
 'scene_count':len(beats),'visual_event_count':len(events),'caption_units':caption['units'],'minimum_caption_font':min(x['fontsize'] for x in caption['bounds']),
 'max_caption_lines':max(x['lines'] for x in caption['bounds']),'caption_pop':'130% -> 96% -> 106% -> 100% in 250ms','subtitle_y':1460,
 'city_colors':'distinct local city colors; plain red/gold flags and army badges identify sides; colors change at narrated captures',
 'borders':'glowing schematic local influence cells around referenced historical places, not surveyed ancient administrative borders',
 'event_times':'manually anchored to repaired source transcript phrases; 107 event entries rather than proportional scene subdivisions',
 'encoded_frame_samples':len(paths),'encoded_frame_times':times,
 'visual_review':'frames extracted; evaluation must be recorded separately after viewing',
 'continuous_playback_and_direct_listening':'not performed in this runtime',
 'user_final_approval':False,
 'known_limits':[
  'Original narration retains two direction claims inconsistent with mapped reference points (Zan relative to Yongcheng; Qiao to Chen).',
  'Exact locked script was not retrieved. Corrected ASR-derived subtitle text and timing still require direct listening for final approval.',
  'City influence cells are illustrative, not documented ancient jurisdiction polygons; disputed death site is a locality proxy.',
  'Some close-up cached satellite backgrounds have limited spatial detail. Event and portrait art are historical reconstructions.'
 ]}
(P/'QA_V84.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:report[k] for k in ['edition','technical_file_pass','duration','bytes','complete_encoded_reference_preserved','scene_count','visual_event_count','caption_units','encoded_frame_samples','sha256']},ensure_ascii=False),flush=True)
