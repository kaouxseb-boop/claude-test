"""V8.4: audio-anchored map actions, generated sprites and short pop captions.
Colored cells illustrate local influence around reference places, not surveyed borders.
Run PREP_ONLY=1 first, then v83/build_captions_v84.py, then this file.
"""
import concurrent.futures
import hashlib
import json
import math
import os
import subprocess
import uuid
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage
import render_v83 as old

ROOT=Path(__file__).resolve().parent; V83=ROOT/'v83'; OUT=ROOT/'v84'; A=OUT/'assets'
W,H,FPS,D=1080,1920,60,402.12
RED=(255,87,105); GOLD=(255,204,102); CYAN=(84,228,255)
FONT=A/'NotoSansThaiFull.ttf'
BEATS=json.loads((V83/'beats.json').read_text())
VERSION='visual-rebuild-5'

# Exact source-time actions from the repaired source transcript, not scene fractions.
# Each tuple is (source time, generated illustration, short visual explanation).
EVENTS=[
 (0.3,'qin_fall','จักรวรรดิเริ่มสั่นคลอน'),(3.6,'conscript','ทหารเกณฑ์ไม่กี่ร้อยคน'),
 (6.3,'conscript','ชาวนาธรรมดา'),(10.6,'chen','เฉินเซิ่ง'),
 (13.3,'chen','จุดจบที่คาดไม่ถึง'),(17.25,'betrayal','คนขับรถม้าของตัวเอง'),(20.1,'chariot','เปิดแผนที่ตามรอย'),
 (23.4,'qin_decree','กว่า 2,200 ปีก่อน'),(27.9,'qin_decree','ฉินเอ้อร์ซื่อขึ้นครองราชย์'),
 (31.6,'conscript','เริ่มที่ต้าเจ๋อเซียง'),(34.6,'forced_labor','ทหารเกณฑ์ประมาณ 900 คน'),(38.1,'conscript','อวี๋หยาง = จุดหมายที่วางไว้'),
 (41.5,'rainstorm','ฝนหนัก • น้ำท่วม'),(45.0,'qin_decree','กำหนดเดินทางใกล้พ้น'),(49.0,'qin_decree','ตามบันทึกสื่อจี้: เสี่ยงโทษตาย'),
 (54.6,'oath','เฉินเซิ่ง • อู๋กว่าง'),(59.2,'conscript','เดินทางต่อก็เสี่ยงตาย'),(64.0,'rebel_rise','ลุกขึ้นสู้ยังมีโอกาส'),(67.6,'oath','ตัดสินใจก่อกบฏ'),
 (69.5,'clash','ยั่วยุนายทหารฉิน'),(72.3,'clash','แย่งอาวุธเข้าต่อสู้'),(75.1,'rebels_win','เฉินเซิ่งเข้าช่วย'),(79.6,'rebel_rise','ปลุกระดมทหารเกณฑ์'),(83.9,'rebels','จากทหารเกณฑ์เป็นกองทัพกบฏ'),
 (88.3,'siege','เป้าหมายแรก: เมืองฉี'),(93.2,'captured_gate','ยึดเมืองฉีสำเร็จ'),(96.4,'rebel_rise','ชัยชนะจุดกระแสลุกฮือ'),(100.8,'rebel_rise','ผู้คนเข้าร่วมเพิ่มขึ้น'),
 (105.2,'captured_gate','เมืองจื้อ'),(109.2,'captured_gate','เมืองจ้าน'),(113.1,'captured_gate','เมืองขู่ • เมืองเจ้อ'),(119.2,'captured_gate','เมืองเฉียว'),(123.3,'rebel_rise','ธงต่อต้านเริ่มแพร่กระจาย'),
 (127.2,'rebels','กองทัพเคลื่อนสู่เมืองเฉิน'),(130.0,'rebel_rise','กำลังพลหลายหมื่นคน'),(133.7,'qin','ทหารฉินยังตั้งรับ'),(136.1,'clash','ปะทะที่ประตูเมือง'),(139.3,'rebels_win','แนวป้องกันต้านไม่ไหว'),(142.7,'captured_gate','เมืองเฉินถูกยึด'),
 (146.2,'coronation','สถาปนารัฐจางฉู่'),(150.6,'chen','จากชาวนาสู่ผู้ครองเมือง'),(154.0,'rebels','มีกองทัพใต้บัญชา'),(157.0,'chen','เป้าหมายต่อไป'),(159.8,'qin_fall','โค่นราชวงศ์ฉิน'),
 (162.5,'rebels','อู๋กว่างเคลื่อนทัพตะวันตก'),(166.0,'siege','เป้าหมาย: สิงหยาง'),(171.7,'qin','หลี่โหยวตั้งรับ'),(176.8,'siege','ป้องกันเมืองอย่างแข็งขัน'),(181.0,'siege','กบฏล้อมแต่ตีไม่แตก'),(185.9,'siege','การล้อมยืดเยื้อ'),
 (190.5,'chen','เปิดแนวรบอีกด้าน'),(194.0,'rebels','โจวเหวินรับตราแม่ทัพ'),(198.0,'gate','ผ่านด่านหานกู่'),(202.0,'rebel_rise','รับทหารเพิ่มระหว่างทาง'),(205.8,'rebels','รุกถึงบริเวณซี'),(209.4,'gate','เสียนหยางอยู่ไม่ไกล'),
 (214.7,'qin_decree','ราชสำนักหาทางโต้กลับ'),(218.8,'zhang','แม่ทัพจางหาน'),(222.0,'forced_labor','ระดมนักโทษและแรงงาน'),(225.5,'forced_labor','แรงงานก่อสร้างสุสาน'),(229.0,'qin','กองทัพใหม่ของฉิน'),
 (233.8,'clash','จางหานโจมตีโจวเหวิน'),(236.2,'qin_wins','ฝ่ายกบฏพ่ายแพ้'),(238.0,'qin_wins','ถอยไปทางตะวันออก'),(242.4,'qin_wins','ถอยต่อถึงเหมี่ยนฉือ'),(247.6,'clash','ฉินไล่โจมตีซ้ำ'),(251.0,'qin_wins','กองทัพโจวเหวินแตกพ่าย'),(254.0,'qin_wins','โจวเหวินสิ้นชีวิต'),
 (258.6,'siege','สิงหยางยังถูกล้อม'),(265.0,'oath','เถียนจางมองเห็นอันตราย'),(269.0,'qin','เสี่ยงถูกโจมตีสองด้าน'),(274.0,'qin_decree','ปลอมคำสั่งเฉินเซิ่ง'),(278.0,'betrayal','สังหารอู๋กว่างชิงบัญชาการ'),(283.0,'oath','สหายตายด้วยฝ่ายเดียวกัน'),
 (288.1,'rebels','เถียนจางยกทหารออกจากสิงหยาง'),(291.0,'clash','ปะทะจางหานที่อ๋าวชาง'),(294.0,'qin_wins','ฉินตีแตกอย่างเด็ดขาด'),(298.4,'qin_wins','เถียนจางเสียชีวิต'),(300.2,'siege','ฉินเข้าตีสิงหยาง'),
 (304.0,'qin','จางหานมุ่งเมืองเฉิน'),(308.0,'siege','โจมตีแนวป้องกัน'),(312.0,'clash','แม่ทัพกบฏพ่ายแพ้'),(316.0,'qin_wins','เฉินเซิ่งต้านไม่ไหว'),
 (318.5,'chariot','ถอนกำลังออกจากเมือง'),(322.5,'chariot','ศูนย์กลางอำนาจถูกทิ้ง'),(327.0,'chariot','หนีเอาชีวิตรอด'),(331.0,'chariot','ผ่านบริเวณเซี่ยเฉิงฝู่'),
 (333.1,'chariot','ผู้ติดตามใกล้ตัว'),(337.5,'betrayal','จวงเจี่ย คนขับรถม้า'),(339.6,'betrayal','สังหารเจ้านายแล้วจำนนฉิน'),(344.0,'chen','ไม่ได้ตายในศึกใหญ่'),(348.6,'betrayal','จุดจบจากคนใกล้ตัว'),
 (353.2,'rebel_rise','ไฟกบฏยังไม่ดับ'),(356.6,'rebels_win','ลวี่เฉินรวบรวมกำลัง'),(359.0,'captured_gate','ยึดเมืองเฉินคืน'),(363.1,'rebel_rise','การต่อต้านยังลุกลาม'),(367.0,'rebels','ประมาณสองปีต่อมา'),
 (368.1,'xiang_yu','เซี่ยงอวี่'),(370.4,'rebels_win','ชนะกองทัพฉินที่จวี้ลู่'),(372.6,'liu_bang','หลิวปัง'),(375.0,'captured_gate','เข้าสู่เสียนหยาง • ฉินยอมจำนน'),
 (378.6,'qin_fall','จักรวรรดิฉินสิ้นสุด'),(384.0,'chen','เฉินเซิ่งไม่ได้เห็นวันนั้น'),(388.2,'rebel_rise','การตัดสินใจเปลี่ยนแผ่นดิน'),(392.1,'rainstorm','จากทหารเกณฑ์ที่ติดฝน'),(396.0,'chen','ชื่อที่ถูกจารึกในประวัติศาสตร์'),(399.0,'qin_fall','ผู้จุดชนวนการล่มสลายของฉิน'),
]
CAPTURE={8:83.84,9:93.14,10:107.0,11:111.0,12:116.4,13:121.0,14:142.68,21:236.2,26:302.1,27:317.4,31:359.0,34:375.2}
RED_SHADES=[(255,85,112),(242,119,74),(229,83,170),(255,147,96),(203,96,224),(248,99,95)]
GOLD_SHADES=[(255,202,90),(83,194,220),(143,163,234),(106,202,161),(213,185,117)]

def font(n):return ImageFont.truetype(str(FONT),n)
def run(a):subprocess.run([str(x) for x in a],check=True)
def nframes(p):
 q=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames','-of','csv=p=0',str(p)],capture_output=True,text=True,check=True)
 return int(q.stdout.strip())
def sprite(name,width):
 im=Image.open(A/(name+'.png')).convert('RGBA');im.thumbnail((width,width),Image.Resampling.LANCZOS);return im
def save_png(im,path):
 temporary=path.with_name(path.stem+'.'+uuid.uuid4().hex+'.building.png');im.save(temporary,format='PNG')
 with Image.open(temporary) as verify:verify.load()
 os.replace(temporary,path)
def tx(d,xy,s,n=36,fill=(255,241,205),anchor='mm'):
 d.text(xy,s,font=font(n),fill=fill,anchor=anchor,stroke_width=2,stroke_fill=(3,10,17))
def visible_keys(b):return list(dict.fromkeys(b.get('show',[b['dest']])+([b['origin']] if b.get('origin') else [])+[b['dest']]))
def controlled(b,after):
 s=set(b.get('controlled',[]))
 if b['kind']=='qin_attack' and b['dest']=='xi':s.add('xi')
 if after and b.get('capture'):
  if b.get('side')=='qin':s.discard(b['dest'])
  else:s.add(b['dest'])
  if b['dest']=='zhe':s.add('ku')
 return s
def city_color(k,s):
 i=sorted(old.PLACES).index(k);return RED_SHADES[i%len(RED_SHADES)] if k in s else GOLD_SHADES[i%len(GOLD_SHADES)]
def influence(im,keys,cam,s):
 # Smooth, disjoint illustrative city cells with irregular outer edges.
 # The areas are illustrative; the historical evidence supplies the center points only.
 yy,xx=np.mgrid[0:H:4,0:W:4]; distances=[];valid=[]
 for k in keys:
  x,y=old.point(k,cam)
  if -250<x<W+250 and 180<y<1500:
   distances.append(np.hypot(xx-x,yy-y));valid.append(k)
 if not valid:return
 stack=np.stack(distances);nearest=np.argmin(stack,axis=0);mind=stack.min(axis=0)
 radius=225 if len(valid)>1 else 310
 noise=14*np.sin(xx/77+yy/119)+9*np.sin(xx/39-yy/97)
 allowed=(mind<radius+noise)&(yy>235)&(yy<1360)
 layer=Image.new('RGBA',(W,H));edges=Image.new('RGBA',(W,H))
 for i,k in enumerate(valid):
  mask=(nearest==i)&allowed
  full=Image.fromarray((mask*255).astype('uint8')).resize((W,H),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1))
  c=city_color(k,s);wash=Image.new('RGBA',(W,H),(*c,0));wash.putalpha(full.point(lambda a:int(a*.20)));layer.alpha_composite(wash)
  outer=full.filter(ImageFilter.MaxFilter(7));inner=full.filter(ImageFilter.MinFilter(7))
  edge=np.array(outer,dtype=np.int16)-np.array(inner,dtype=np.int16)
  e=Image.new('RGBA',(W,H),(*c,0));e.putalpha(Image.fromarray(np.clip(edge,0,255).astype('uint8')));edges.alpha_composite(e)
 im.alpha_composite(layer);im.alpha_composite(edges.filter(ImageFilter.GaussianBlur(11)));im.alpha_composite(edges.filter(ImageFilter.GaussianBlur(4)));im.alpha_composite(edges)
def city_positions(b):
 cam=old.camera(b);used=[];res=[]
 for k in visible_keys(b):
  x,y=old.point(k,cam)
  if not (30<x<1050 and 260<y<1330):continue
  lx=min(900,max(180,x));ly=y-112
  for ox,oy in used:
   if abs(lx-ox)<270 and abs(ly-oy)<65:ly+=200
  used.append((lx,ly));res.append({'key':k,'x':lx,'y':ly,'text':old.PLACES[k][0]})
 return res
def build_base(i,b,after=False):
 cam=old.camera(b);im=old.background(cam);s=controlled(b,after);keys=visible_keys(b)
 influence(im,keys,cam,s)
 d=ImageDraw.Draw(im)
 # Soft contrast above the action, preserving the terrain over the entire frame.
 sh=Image.new('RGBA',(W,H));sd=ImageDraw.Draw(sh)
 for y in range(260):sd.line((0,y,W,y),fill=(3,12,23,round(215*(1-y/260))))
 im.alpha_composite(sh);d=ImageDraw.Draw(im)
 tx(d,(45,55),'กบฏเฉินเซิ่ง',30,anchor='lm');tx(d,(45,115),b['title'],47 if len(b['title'])<27 else 40,anchor='lm')
 logo=Image.open(A/'logo.png').convert('RGBA');logo.thumbnail((90,90));im.alpha_composite(logo,(940,35))
 if b.get('origin'):
  p0=old.point(b['origin'],cam);p1=old.point(b['dest'],cam)
  pts=[(p0[0]+(p1[0]-p0[0])*j/100-36*math.sin(math.pi*j/100),p0[1]+(p1[1]-p0[1])*j/100-22*math.sin(math.pi*j/100)) for j in range(101)]
  route=Image.new('RGBA',(W,H));rd=ImageDraw.Draw(route)
  for width,alpha in [(25,35),(11,95),(4,245)]:
   if b.get('planned'):
    for j in range(0,98,7):rd.line(pts[j:j+4],fill=(*CYAN,alpha),width=width)
   else:rd.line(pts,fill=(*CYAN,alpha),width=width,joint='curve')
  a=math.atan2(p1[1]-p0[1],p1[0]-p0[0]);rd.polygon([p1,(p1[0]-25*math.cos(a)+12*math.sin(a),p1[1]-25*math.sin(a)-12*math.cos(a)),(p1[0]-25*math.cos(a)-12*math.sin(a),p1[1]-25*math.sin(a)+12*math.cos(a))],fill=(*CYAN,255));im.alpha_composite(route)
 for k in keys:
  x,y=old.point(k,cam)
  if not(-100<x<W+100 and 230<y<1400):continue
  c=city_color(k,s);disc=Image.new('RGBA',(W,H));dd=ImageDraw.Draw(disc)
  dd.ellipse((x-74,y-74,x+74,y+74),fill=(*c,45),outline=(*c,220),width=3);im.alpha_composite(disc)
  sp=sprite('gate' if k in ['xianyang','hangu','xingyang'] else 'town',135);im.alpha_composite(sp,(x-sp.width//2,y-sp.height//2))
  d=ImageDraw.Draw(im);d.line((x+40,y-78,x+40,y+12),fill=(255,239,206),width=3);d.polygon([(x+42,y-78),(x+104,y-62),(x+42,y-43)],fill=RED if k in s else GOLD)
 d=ImageDraw.Draw(im);d.ellipse((45,1608,61,1624),fill=RED);tx(d,(78,1617),'กบฏ',29,RED,anchor='lm');d.ellipse((205,1608,221,1624),fill=GOLD);tx(d,(239,1617),'ฉิน',29,GOLD,anchor='lm')
 tx(d,(45,1670),'สีพื้นที่แยกเมือง • ธงบอกฝ่าย',24,(210,223,229),anchor='lm');tx(d,(45,1710),'เขตอิทธิพลโดยประมาณ • ภาพจำลอง',24,(210,223,229),anchor='lm')
 target=OUT/f'base_{i:02}_{"after" if after else "before"}.png';save_png(im.convert('RGB'),target);return target
def prepare():
 meta=[]
 for i,b in enumerate(BEATS):
  build_base(i,b)
  if b.get('capture'):build_base(i,b,True)
  meta.append({'start':b['start'],'end':b['end'],'labels':city_positions(b)})
 (OUT/'label_positions.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
 (OUT/'visual_events.json').write_text(json.dumps([{'time':t,'asset':a,'explanation':label} for t,a,label in EVENTS],ensure_ascii=False,indent=2))
 print('prepared',len(BEATS),'scenes;',len(EVENTS),'audio-anchored visual events',flush=True)
def event_plate(name,label,index):
 im=Image.new('RGBA',(520,440));sp=sprite(name,360);x=(520-sp.width)//2;y=10
 # Only one main illustration at a time. Caption bar remains inside its own area.
 im.alpha_composite(sp,(x,y));d=ImageDraw.Draw(im);n=30
 while d.textlength(label,font=font(n))>490 and n>24:n-=1
 w=d.textlength(label,font=font(n));ty=min(385,sp.height+28)
 d.rounded_rectangle((max(5,(520-w)//2-15),ty-8,min(515,(520+w)//2+15),ty+n+15),radius=10,fill=(5,16,26,235),outline=(234,193,105,210),width=2)
 tx(d,(260,ty+n/2+3),label,n)
 p=OUT/f'event_{index:03}.png';save_png(im,p);return p
def badge(name,side):
 p=OUT/f'badge_{name}_{side}.png'
 if p.exists() and os.environ.get('REMAKE_BADGES')!='1':return p
 c=RED if side=='rebel' else GOLD;sp=sprite(name,205);im=Image.new('RGBA',(240,260));d=ImageDraw.Draw(im)
 d.ellipse((20,23,220,220),fill=(3,12,20,95),outline=(*c,230),width=5);im.alpha_composite(sp,((240-sp.width)//2,34));d=ImageDraw.Draw(im);d.rounded_rectangle((36,220,204,255),radius=9,fill=(*c,240));d.text((120,237),'กบฏ' if side=='rebel' else 'ฉิน',font=font(25),fill=(12,15,20),anchor='mm');save_png(im,p);return p
def impact_plate():
 p=OUT/'impact.png'
 if p.exists():return p
 im=Image.new('RGBA',(340,340));d=ImageDraw.Draw(im)
 for j in range(16):
  a=j*math.pi/8;r0=25;r1=92+(j%3)*25
  d.line((170+r0*math.cos(a),170+r0*math.sin(a),170+r1*math.cos(a),170+r1*math.sin(a)),fill=(255,215,104,220),width=5)
 d.ellipse((120,120,220,220),outline=(255,241,180,255),width=7);save_png(im,p);return p
def scene(i,b):
 nf=round(b['end']*FPS)-round(b['start']*FPS);dur=nf/FPS;target=OUT/f'seg_{i:02}.mp4';stamp=OUT/f'seg_{i:02}.version'
 if target.exists() and stamp.exists() and stamp.read_text()==VERSION and os.environ.get('FORCE')!='1' and nframes(target)==nf:return target
 args=['-f','image2','-loop','1','-framerate',FPS,'-t',f'{dur:.6f}','-probesize','32','-analyzeduration','0','-c:v','png','-i',OUT/f'base_{i:02}_before.png'];f=[];cur='0:v';stream=1
 def add(path):
  nonlocal stream
  n=stream;stream+=1;args.extend(['-f','image2','-loop','1','-framerate',FPS,'-t',f'{dur:.6f}','-probesize','32','-analyzeduration','0','-c:v','png','-i',path]);return n
 def over(n,x,y,enable=None,pre=''):
  nonlocal cur
  src=f'{n}:v'
  if pre:f.append(f'[{src}]{pre}[pre{n}]');src=f'pre{n}'
  out=f'v{n}';en=f":enable='{enable}'" if enable else ''
  f.append(f"[{cur}][{src}]overlay=x='{x}':y='{y}'{en}:shortest=1[{out}]");cur=out
 if b.get('capture'):
  n=add(OUT/f'base_{i:02}_after.png');ct=max(.1,CAPTURE.get(i,b['end']-.7)-b['start']);over(n,'0','0',pre=f'format=rgba,fade=t=in:st={ct:.3f}:d=0.3:alpha=1')
 cam=old.camera(b);p0=old.point(b.get('origin') or b['dest'],cam);p1=old.point(b['dest'],cam)
 kind=b['kind'];side='qin' if b.get('side')=='qin' else 'rebel';moving=bool(b.get('origin')) and not b.get('planned')
 # Frontline arrival is tied to the narrated confrontation/capture or before its outcome.
 arrival={9:93.14,14:136.06,21:234.5,25:291.0,26:300.5,27:308.0,34:375.0}.get(i,b['start']+max(.8,dur*.72))-b['start']
 u=f'min(max((t-0.15)/{max(.6,arrival):.4f},0),1)'
 x=f'{p0[0]}+({p1[0]-p0[0]})*({u})-36*sin(PI*({u}))';y=f'{p0[1]}+({p1[1]-p0[1]})*({u})-22*sin(PI*({u}))'
 if not moving:x=str(p1[0]-120);y=str(p1[1]+160)
 if b.get('planned'):x=str(p0[0]-90);y=str(p0[1]+150)
 # Portrait/weather/court beats use their event illustrations without redundant army stacks.
 army_kinds={'capture','move','retreat','siege','battle','qin_attack','revolt','plan'}
 if kind in army_kinds:
  n=add(badge('chariot' if i==28 else ('qin' if side=='qin' else 'rebels'),side))
  if i==25:
   dt='max(t-6.0,0)';over(n,f'({x})-120-min(({dt})*190,800)',f'({y})-90+min(({dt})*90,400)',pre='format=rgba,fade=t=out:st=6.6:d=0.8:alpha=1')
  else:over(n,x+'-120',y+'-90')
 if kind in {'siege','battle','qin_attack','revolt'} or (kind=='capture' and i in {9,14,31,34}):
  winner='qin' if i in {21,25,26,27} else 'rebel';enemy_side='rebel' if side=='qin' else 'qin';n=add(badge('qin' if enemy_side=='qin' else 'rebels',enemy_side))
  defeat={8:76.86,9:93.14,14:142.0,21:236.2,26:302.0,27:315.0,31:359.0,33:370.4,34:375.0}.get(i,b['end']+3)-b['start']
  retreat=f'max(t-{defeat:.3f},0)';ex=f'{p1[0]+100}+min(({retreat})*200,700)';ey=f'{p1[1]+90}+min(({retreat})*95,400)'
  over(n,ex+'-120',ey+'-90',pre=f'format=rgba,fade=t=out:st={max(.1,defeat+.4):.3f}:d=0.65:alpha=1')
  hit=max(.3,min(arrival,dur-.6));n=add(impact_plate());over(n,str(p1[0]-170),str(p1[1]-130),enable=f'between(t,{hit:.3f},{min(dur,hit+.42):.3f})',pre='format=rgba')
 # Each illustration is timed from an actual source phrase, capped at 4.2 seconds.
 es=[(j,e) for j,e in enumerate(EVENTS) if b['start']<=e[0]<b['end']]
 # Fit the event in an unoccupied screen zone; preserve map labels and city pins.
 obstacles=[(v['x']-170,v['y']-36,v['x']+170,v['y']+36) for v in city_positions(b)]
 obstacles.append((p1[0]-125,p1[1]-100,p1[0]+125,p1[1]+150))
 def overlap(box,other):return max(0,min(box[2],other[2])-max(box[0],other[0]))*max(0,min(box[3],other[3])-max(box[1],other[1]))
 candidates=[(20,220),(540,220),(20,890),(540,890)]
 px,py=min(candidates,key=lambda p:sum(overlap((p[0]+60,p[1],p[0]+460,p[1]+435),o) for o in obstacles)+(600 if p[1]>500 else 0))
 for z,(j,(time,name,label)) in enumerate(es):
  start=max(0,time-b['start']);nxt=es[z+1][1][0]-b['start'] if z+1<len(es) else dur
  end=min(dur,nxt-.04,start+4.2);end=max(start+.22,end)
  n=add(event_plate(name,label,j));en=f'between(t,{start:.3f},{end:.3f})';dt=f'max(t-{start:.3f},0)'
  xx=f'{px}+if(lt(t,{start+.22:.3f}),({-1 if px<500 else 1})*420*(1-({dt})/.22),0)';yy=f'{py}-14*exp(-8*({dt}))*sin(26*({dt}))'
  over(n,xx,yy,en,pre=f'format=rgba,fade=t=in:st={start:.3f}:d=0.12:alpha=1,fade=t=out:st={max(start,end-.16):.3f}:d=0.16:alpha=1')
 # Rain is an event-local effect and does not move the map camera.
 if i==6:
  f.append(f'[{cur}]drawgrid=w=120:h=170:t=1:c=0x7FCBE2@0.06[vweather]');cur='vweather'
 building=target.with_name(target.stem+'.'+uuid.uuid4().hex+'.building.mp4')
 run(['ffmpeg','-hide_banner','-loglevel','error','-y']+args+['-filter_complex_threads','1','-filter_complex',';'.join(f),'-map',f'[{cur}]','-frames:v',nf,'-an','-c:v','libx264','-threads','3','-preset','veryfast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',building])
 assert nframes(building)==nf;os.replace(building,target);stamp.write_text(VERSION);print('scene',i,'done',nf,flush=True);return target
def assemble():
 concat=OUT/'concat_v84.txt';concat.write_text(''.join(f"file '{(OUT/f'seg_{i:02}.mp4').as_posix()}'\n" for i in range(len(BEATS))))
 output=OUT/'ChenSheng_V84_FULL_60FPS_REVIEW.mp4'
 run(['ffmpeg','-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',concat,'-i',V83/'narration_reference.m4a','-stream_loop','-1','-c:v','libvpx-vp9','-i',A/'mascot.webm','-filter_complex_threads','1','-filter_complex',f"[0:v]ass=filename={OUT/'captions_v84.ass'}:fontsdir={A}[sub];[2:v]scale=195:-1,format=rgba[mas];[sub][mas]overlay=W-w-28:H-h-25:shortest=0,format=yuv420p[v]",'-map','[v]','-map','1:a:0','-c:v','libx264','-threads','6','-preset','veryfast','-crf','17','-c:a','copy','-frames:v',round(D*FPS),'-movflags','+faststart','-progress',OUT/'mux_progress.txt',output]);print('OUTPUT',output,flush=True)
def main():
 OUT.mkdir(exist_ok=True)
 if os.environ.get('PREP_ONLY')=='1':prepare();return
 if os.environ.get('ONLY') is not None:
  i=int(os.environ['ONLY']);scene(i,BEATS[i]);return
 for i,b in enumerate(BEATS):
  for attempt in range(3):
   try:scene(i,b);break
   except (subprocess.CalledProcessError,AssertionError) as error:
    print('incomplete segment',i,'attempt',attempt+1,'will rebuild',flush=True)
    if attempt==2:raise
 if os.environ.get('PARTS_ONLY')!='1':assemble()
if __name__=='__main__':main()
