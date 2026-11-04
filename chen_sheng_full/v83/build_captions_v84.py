import json,re,difflib,hashlib
from pathlib import Path
from PIL import ImageFont
from pythainlp.tokenize import word_tokenize
from pythainlp.corpus.common import thai_words
from pythainlp.util import Trie
NAMES=['เฉินเซิ่ง','อู๋กว่าง','จิ๋นซีฮ่องเต้','ฉินเอ้อร์ซื่อ','ราชวงศ์ฉิน','จางหาน','โจวเหวิน','เถียนจาง','ลวี่เฉิน','จวงเจี่ย','เซี่ยงอวี่','หลิวปัง','หลี่โหยว','ต้าเจ๋อเซียง','เซี่ยเฉิงฝู่','อ๋าวชาง','สิงหยาง','เสียนหยาง','อวี๋หยาง','จวี้ลู่','เหมี่ยนฉือ','เฉาหยาง','ด่านหานกู่','จางฉู่','ซูโจว','ปั๋วโจว','หวยหยาง']
DICT=Trie(set(thai_words())|set(NAMES))
def tokenize(t,keep_whitespace=False):return word_tokenize(t,engine='newmm',custom_dict=DICT,keep_whitespace=keep_whitespace)
P=Path(__file__).resolve().parent
raw=json.loads((P/'asr_turbo.json').read_text());segments=raw['segments'];words=raw['words']
# Remove one overlapping ASR repeat. These are recognition outputs, not an edit to audio.
segments=[s for s in segments if abs(s['start']-177.64)>.03]
for fix in json.loads((P/'asr_repairs.json').read_text()):
 old=[s for s in segments if s['start']>=fix['start']-.005 and s['end']<=fix['end']+.005]
 intervals=[(s['start'],s['end']) for s in old]
 segments=[s for s in segments if s not in old]
 words=[w for w in words if not any(a-.005<=w['start'] and w['end']<=b+.005 for a,b in intervals)]
 segments.extend(fix['segments']);words.extend(fix['words'])
segments.sort(key=lambda s:s['start']);words.sort(key=lambda w:(w['start'],w['end']))
fixes={}
for line in (P/'corrections.tsv').read_text().splitlines():
 if not line.strip():continue
 a,s=line.split('\t',1);fixes[round(float(a),2)]=s
OUT=P.parent/'v84';OUT.mkdir(parents=True,exist_ok=True)
F=ImageFont.truetype(str(P/'assets/NotoSansThaiFull.ttf'),74)
def clean(s):return ''.join(c for c in s if not c.isspace())
all_units=[];review=[]
for s in segments:
 t=fixes.get(round(s['start'],2))
 if t is None:raise ValueError(('Uncorrected ASR segment',s))
 ws=[w for w in words if w['start']>=s['start']-.011 and w['end']<=s['end']+.011]
 chars=[];times=[]
 for w in ws:
  for c in w['text']:
   if not c.isspace():chars.append(c);times.append((w['start'],w['end']))
 orig=''.join(chars);new=clean(t)
 if not orig:raise ValueError(('No real ASR anchors',s))
 mapping=[None]*len(new)
 for tag,a,b,c,d in difflib.SequenceMatcher(None,orig,new,autojunk=False).get_opcodes():
  if tag=='equal':
   for k in range(d-c):mapping[c+k]=times[a+k]
  elif d>c:
   # Orthographic replacement inherits the unchanged span of its ASR source error.
   # No proportional word-duration or character-rate timing is generated.
   aa=times[min(a,len(times)-1)][0]
   bb=times[min(max(a,b-1),len(times)-1)][1]
   if b==a and a>0:aa,bb=times[a-1]
   for k in range(c,d):mapping[k]=(aa,max(aa,bb))
 tokens=tokenize(t,keep_whitespace=True)
 pos=0;timed=[]
 for token in tokens:
  n=len(clean(token))
  if n:
   entries=mapping[pos:pos+n];pos+=n
   a=min(e[0] for e in entries if e);b=max(e[1] for e in entries if e)
   timed.append([a,b,token])
  elif timed:timed[-1][2]+=token
 chunk=[];start=end=0
 for a,b,token in timed:
  tentative=''.join(v[2] for v in chunk)+token
  if chunk and a>start+.08 and (b-start>1.65 or F.getlength(tentative)>690):
   all_units.append(dict(start=start,end=end,text=''.join(v[2] for v in chunk).strip()))
   chunk=[]
  if not chunk:start=a
  end=max(end,b);chunk.append([a,b,token])
 if chunk:all_units.append(dict(start=start,end=end,text=''.join(v[2] for v in chunk).strip()))
 review.append({'start':s['start'],'end':s['end'],'asr':s['text'],'display':t})
# Preserve text while coalescing any edit spans that share an ASR time anchor.
units=[]
for u in all_units:
 if units and (u['start']<=units[-1]['start']+.06 or (u['end']-u['start']<.12 and u['start']<units[-1]['end']+.15)):
  units[-1]['text']+=u['text'];units[-1]['end']=max(units[-1]['end'],u['end'])
 else:units.append(u)
# Merge fragments too brief to read, retaining the same outer ASR boundaries.
readable=[]
for u in units:
 if readable and u['end']-u['start']<.38 and u['start']-readable[-1]['end']<.55 and u['end']-readable[-1]['start']<2.25:
  readable[-1]['text']+=u['text'];readable[-1]['end']=max(readable[-1]['end'],u['end'])
 else:readable.append(u)
units=readable
for i,u in enumerate(units):
 if i+1<len(units):u['end']=min(u['end'],units[i+1]['start'])
 if u['end']<=u['start']:u['end']=min(u['start']+.04,units[i+1]['start']) if i+1<len(units) else u['start']+.04

def lines(t,size=74):
 f=ImageFont.truetype(str(P/'assets/NotoSansThaiFull.ttf'),size);ws=tokenize(t,keep_whitespace=True);ls=['']
 for w in ws:
  if f.getlength(ls[-1]+w)>760 and ls[-1]:ls.append(w)
  else:ls[-1]+=w
 return [x.strip() for x in ls]
def ts(t,ass=False):
 ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);sec,ms=divmod(ms,1000)
 return f'{h}:{m:02}:{sec:02}.{ms//10:02}' if ass else f'{h:02}:{m:02}:{sec:02},{ms:03}'
hdr='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,Noto Sans Thai,74,&H00FFFFFF,&H0000CCFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,6,2,2,55,55,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
ass=[hdr];srt=[];bounds=[]
gold_keys=['เฉินเซิ่ง','อู๋กว่าง','จิ๋นซีฮ่องเต้','จางหาน','โจวเหวิน','เถียนจาง','ลวี่เฉิน','จวงเจี่ย','เซี่ยงอวี่','หลิวปัง']
red_keys=['กบฏ','ลุกขึ้นสู้','โจมตี','รบ','พ่ายแพ้','สังหาร','แตกพ่าย','โต้กลับ','ยึดเมือง']
cyan_keys=['ราชวงศ์ฉิน','900 คน','หลายหมื่นคน','ต้าเจ๋อเซียง','สิงหยาง','อ๋าวชาง','เสียนหยาง','เมืองเฉิน']
for i,u in enumerate(units,1):
 size=74;ls=lines(u['text'],size)
 while len(ls)>2 and size>66:size-=2;ls=lines(u['text'],size)
 if len(ls)>2:raise ValueError(('Subtitle exceeds two lines',u))
 display='\\N'.join(ls)
 for key in sorted(gold_keys,key=len,reverse=True):display=display.replace(key,r'{\c&H007DEBFF&}'+key+r'{\c&H00FFFFFF&}')
 for key in sorted(red_keys,key=len,reverse=True):display=display.replace(key,r'{\c&H006B6BFF&}'+key+r'{\c&H00FFFFFF&}')
 for key in sorted(cyan_keys,key=len,reverse=True):display=display.replace(key,r'{\c&H00FFD37A&}'+key+r'{\c&H00FFFFFF&}')
 if r'{\c&' not in display:
  stop={'และ','หรือ','แต่','เพราะ','ที่','ของ','เป็น','ได้','ให้','จาก','ไป','มา','ก็','จะ','ว่า','เมื่อ','แล้ว','ไม่','อยู่','อย่าง','จึง'}
  candidates=[v.strip() for v in tokenize(u['text']) if v.strip() not in stop and len(v.strip())>=2]
  if candidates:
   key=max(candidates,key=len);display=display.replace(key,r'{\c&H007DEBFF&}'+key+r'{\c&H00FFFFFF&}',1)
 effect=r'{\an2\pos(540,1460)\fs'+str(size)+r'\fscx130\fscy130\t(0,90,\fscx96\fscy96)\t(90,170,\fscx106\fscy106)\t(170,250,\fscx100\fscy100)}'
 ass.append(f"Dialogue: 0,{ts(u['start'],True)},{ts(u['end'],True)},Pop,,0,0,0,,{effect}{display}\n")
 srt.extend([str(i),ts(u['start'])+' --> '+ts(u['end']),'\n'.join(ls),''])
 bounds.append(dict(index=i,lines=len(ls),fontsize=size,width=max(ImageFont.truetype(str(P/'assets/NotoSansThaiFull.ttf'),size).getlength(v) for v in ls),duration=u['end']-u['start']))
# Put map labels in the final ASS layer so moving troops cannot cover city names.
import sys
sys.path.insert(0,str(P.parent))
import render_v84 as maprender
city_style='Style: City,Noto Sans Thai,42,&H00B0E8FF,&H00B0E8FF,&H20120E08,&H20120E08,-1,0,0,0,100,100,0,0,1,2,0,5,0,0,0,1\n'
ass[0]=ass[0].replace('\n[Events]','\n'+city_style+'\n[Events]')
for b in json.loads((OUT/'label_positions.json').read_text()):
 for v in b['labels']:
  x,ly,label=v['x'],v['y'],v['text']
  from PIL import Image,ImageDraw
  label_bounds=ImageDraw.Draw(Image.new('RGB',(1,1))).textbbox((x,ly),label,font=maprender.font(42),anchor='mm',stroke_width=2)
  bx0,by0,bx1,by1=label_bounds[0]-17,label_bounds[1]-13,label_bounds[2]+17,label_bounds[3]+13
  bw,bh=bx1-bx0,by1-by0
  plate=f'm 0 0 l {bw} 0 {bw} {bh} 0 {bh}'
  ass.append(f"Dialogue: 1,{ts(b['start'],True)},{ts(b['end'],True)},City,,0,0,0,,{{\\an7\\pos({bx0},{by0})\\p1\\bord0\\shad0\\1c&H120E08&}}{plate}\n")
  ass.append(f"Dialogue: 2,{ts(b['start'],True)},{ts(b['end'],True)},City,,0,0,0,,{{\\an5\\pos({x},{ly})}}{label}\n")
(OUT/'captions_v84.ass').write_text(''.join(ass));(OUT/'ChenSheng_V84_Thai.srt').write_text('\n'.join(srt))
(OUT/'caption_units_v84.json').write_text(json.dumps(units,ensure_ascii=False,indent=2))
(OUT/'transcript_review_v84.json').write_text(json.dumps(review,ensure_ascii=False,indent=2))
qa={'units':len(units),'last_cue_end':units[-1]['end'],'bounds':bounds,'timing_method':'ASR word/character anchors with unchanged replacement-error spans; no proportional text-rate timestamps. Human alignment and exact locked-script comparison pending.','full_audio_modified':False,'unreviewed_phrases':['282.1 sec: หลังได้อำนาจ','109.12 sec: southwest direction of Zan','127 sec: narration says north toward Chen; mapped movement is west with a slight south component'],'status':'REVIEW — manual orthography and ASR anchors, not forced-alignment certified'}
(OUT/'caption_qa_v84.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
print(json.dumps({'units':len(units),'min_duration':min(v['duration'] for v in bounds),'max_duration':max(v['duration'] for v in bounds),'max_lines':max(v['lines'] for v in bounds),'minimum_font':min(v['fontsize'] for v in bounds)},ensure_ascii=False))
