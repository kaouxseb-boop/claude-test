import json,re,difflib,hashlib
from pathlib import Path
from PIL import ImageFont
from pythainlp.tokenize import word_tokenize
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
F=ImageFont.truetype(str(P/'assets/NotoSansThaiFull.ttf'),60)
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
 tokens=word_tokenize(t,engine='newmm',keep_whitespace=True)
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
  if chunk and a>start+.10 and (b-start>2.05 or F.getlength(tentative)>850):
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
 if readable and u['end']-u['start']<.45 and u['start']-readable[-1]['end']<.65 and u['end']-readable[-1]['start']<3.0:
  readable[-1]['text']+=u['text'];readable[-1]['end']=max(readable[-1]['end'],u['end'])
 else:readable.append(u)
units=readable
for i,u in enumerate(units):
 if i+1<len(units):u['end']=min(u['end'],units[i+1]['start'])
 if u['end']<=u['start']:u['end']=min(u['start']+.04,units[i+1]['start']) if i+1<len(units) else u['start']+.04

def lines(t,size=60):
 f=ImageFont.truetype(str(P/'assets/NotoSansThaiFull.ttf'),size);ws=word_tokenize(t,engine='newmm',keep_whitespace=True);ls=['']
 for w in ws:
  if f.getlength(ls[-1]+w)>890 and ls[-1]:ls.append(w)
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
Style: Pop,Noto Sans Thai,60,&H00FFFFFF,&H0000CCFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5,1,2,70,70,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
ass=[hdr];srt=[];bounds=[]
keys=['เฉินเซิ่ง','อู๋กว่าง','จิ๋นซีฮ่องเต้','ราชวงศ์ฉิน','จางหาน','โจวเหวิน','เถียนจาง','ลวี่เฉิน','จวงเจี่ย','900 คน']
for i,u in enumerate(units,1):
 size=60;ls=lines(u['text'],size)
 while len(ls)>2 and size>46:size-=2;ls=lines(u['text'],size)
 if len(ls)>2:raise ValueError(('Subtitle exceeds two lines',u))
 display='\\N'.join(ls)
 for key in keys:display=display.replace(key,r'{\c&H007DEBFF&}'+key+r'{\c&H00FFFFFF&}')
 effect=r'{\an2\pos(540,1480)\fs'+str(size)+r'\fscx110\fscy110\t(0,140,\fscx100\fscy100)}'
 ass.append(f"Dialogue: 0,{ts(u['start'],True)},{ts(u['end'],True)},Pop,,0,0,0,,{effect}{display}\n")
 srt.extend([str(i),ts(u['start'])+' --> '+ts(u['end']),'\n'.join(ls),''])
 bounds.append(dict(index=i,lines=len(ls),fontsize=size,width=max(ImageFont.truetype(str(P/'assets/NotoSansThaiFull.ttf'),size).getlength(v) for v in ls),duration=u['end']-u['start']))
# Put map labels in the final ASS layer so moving troops cannot cover city names.
import sys
sys.path.insert(0,str(P.parent))
import render_v83 as maprender
city_style='Style: City,Noto Sans Thai,36,&H00B0E8FF,&H00B0E8FF,&H20120E08,&H20120E08,-1,0,0,0,100,100,0,0,3,9,0,5,0,0,0,1\n'
ass[0]=ass[0].replace('\n[Events]','\n'+city_style+'\n[Events]')
for b in json.loads((P/'beats.json').read_text()):
 cam=maprender.camera(b);keys=list(dict.fromkeys(b.get('show',[b['dest']])+([b['origin']] if b.get('origin') else [])+[b['dest']]))
 used=[]
 for k in keys:
  x,y=maprender.point(k,cam)
  if not (60<x<1020 and 270<y<1350):continue
  ly=y-100
  for ox,oy in used:
   if abs(x-ox)<245 and abs(ly-oy)<65:ly+=185
  used.append((x,ly));label=maprender.PLACES[k][0]
  ass.append(f"Dialogue: 1,{ts(b['start'],True)},{ts(b['end'],True)},City,,0,0,0,,{{\\an5\\pos({x},{ly})}}{label}\n")
(P/'captions.ass').write_text(''.join(ass));(P/'ChenSheng_V83_Thai.srt').write_text('\n'.join(srt))
(P/'caption_units.json').write_text(json.dumps(units,ensure_ascii=False,indent=2))
(P/'transcript_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2))
qa={'units':len(units),'last_cue_end':units[-1]['end'],'bounds':bounds,'timing_method':'ASR word/character anchors with unchanged replacement-error spans; no proportional text-rate timestamps. Human alignment and exact locked-script comparison pending.','full_audio_modified':False,'unreviewed_phrases':['282.1 sec: หลังได้อำนาจ','109.12 sec: southwest direction of Zan','127 sec: narration says north toward Chen; mapped movement is west with a slight south component'],'status':'REVIEW — manual orthography and ASR anchors, not forced-alignment certified'}
(P/'caption_qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
print(json.dumps({'units':len(units),'min_duration':min(v['duration'] for v in bounds),'max_duration':max(v['duration'] for v in bounds),'max_lines':max(v['lines'] for v in bounds),'minimum_font':min(v['fontsize'] for v in bounds)},ensure_ascii=False))
