#!/usr/bin/env python3
"""Audio-led repair of Chen Sheng V8. Keeps V8/V82 editions intact.
Run from repository root. Source WAV is inputs/chen_sheng.wav or SOURCE_WAV.
Cities are reference proxies, routes schematic connectors, never surveyed tracks.
"""
import concurrent.futures, hashlib, io, json, math, os, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import render_full as baseline
R=Path(__file__).resolve().parent; O=R/'v83'; A=O/'assets'; T=O/'tiles'
for p in (O,A,T):p.mkdir(exist_ok=True)
W,H,FPS=1080,1920,60
D=402.12
FONT=A/'NotoSansThaiFull.ttf'
PLACES=dict(baseline.PLACES)
# Correct direction: the drafted troops headed FROM Dazexiang TOWARD Yuyang.
# These proxies locate the historical localities, not exact archaeological survey pins.
PLACES['daze']=('ต้าเจ๋อเซียง',117.09069,33.51569) # modern township proxy, not exact revolt site
PLACES['xiachengfu']=('เซี่ยเฉิงฝู่',116.15,33.57) # area proxy NW of modern Guoyang; disputed exact site
PLACES['peixian']=('เพ่ย',116.93,34.73)
PLACES['wuguan']=('ด่านอู่กวน',110.715,33.695)
PLACES['hangu']=('ด่านหานกู่',110.925,34.639) # Qin pass at Wangduo, Lingbao, NOT Han pass at Xin'an
PLACES['xi']=('ซี',109.33,34.47) # locality proxy NE of Lintong, west bank of the Xi stream
PLACES['caoyang']=('เฉาหยาง',111.00,34.68) # locality proxy NE of Lingbao, beyond Qin Hangu eastward
PLACES['aocang']=('อ๋าวชาง',113.52,34.91) # locality proxy near old Xingyang
# CHGIS point features for the named ancient counties, queried at 209 BCE.
geo_names={'qi':'蕲县','zhi':'銍县','zan':'酇县','ku':'苦县','zhe':'柘县','qiao':'谯县','chen':'陈县','xingyang':'荥阳县','xianyang':'咸阳县','julu':'巨鹿县'}
for key,cn in geo_names.items():
 data=json.loads((O/'geography'/f'{cn}.json').read_text())['placenames'][0]
 x,y=map(float,data['xy coordinates'].split(','));PLACES[key]=(PLACES[key][0],x,y)
RED=(238,98,88,255); GOLD=(246,201,106,255); CYAN=(90,228,255,255)
def run(a):subprocess.run([str(x) for x in a],check=True,stdout=subprocess.DEVNULL)
def ff(a):run(['ffmpeg','-hide_banner','-loglevel','error','-y']+a)
def font(n):return ImageFont.truetype(str(FONT),n)
def text(d,xy,s,n=38,fill=GOLD,anchor='mm',stroke=3):
 d.text(xy,s,font=font(n),fill=fill,anchor=anchor,stroke_width=stroke,stroke_fill=(6,16,24,255))
def merc(lon,lat,z):return baseline.merc(lon,lat,z)
FALLBACKS=[]
def fetch_tile(z,x,y):
 p=T/f'{z}-{x}-{y}.jpg'
 if p.exists():return p
 target=T/f'fallback_{z}-{x}-{y}.jpg'
 if target.exists():return target
 for pz in range(z-1,-1,-1):
  f=2**(z-pz);parent=T/f'{pz}-{x//f}-{y//f}.jpg'
  if parent.exists():
   im=Image.open(parent);l=(x%f)*256/f;t=(y%f)*256/f
   im=im.crop((l,t,l+256/f,t+256/f)).resize((256,256),Image.Resampling.LANCZOS)
   im.save(target,quality=94);FALLBACKS.append({'tile':[z,x,y],'cached_parent':pz});return target
 # Offline, georegistered Asia raster from the approved reference package.
 source=A/'asia.jpg';meta=json.loads((A/'asia.json').read_text())
 im=Image.open(source);e=meta['response']['extent'];world=20037508.342789244
 x0=x/(2**z)*world*2-world;x1=(x+1)/(2**z)*world*2-world
 y0=world-y/(2**z)*world*2;y1=world-(y+1)/(2**z)*world*2
 box=((x0-e['xmin'])/(e['xmax']-e['xmin'])*im.width,(e['ymax']-y0)/(e['ymax']-e['ymin'])*im.height,(x1-e['xmin'])/(e['xmax']-e['xmin'])*im.width,(e['ymax']-y1)/(e['ymax']-e['ymin'])*im.height)
 im.crop(box).resize((256,256),Image.Resampling.LANCZOS).save(target,quality=94)
 FALLBACKS.append({'tile':[z,x,y],'cached_parent':'registered-Asia-raster'});return target

def setup():
 src=Path(os.environ.get('SOURCE_WAV',str(R/'inputs/chen_sheng.wav')))
 if not src.exists():raise FileNotFoundError(src)
 mascot=A/'mascot.webm'
 if not mascot.exists():
  with mascot.open('wb') as f:
   for p in sorted((R/'assets').glob('mascot.part*')):f.write(p.read_bytes())
 ref=O/'narration_reference.m4a'
 if not ref.exists():ff(['-i',src,'-vn','-c:a','aac','-b:a','160k',ref])
 return src,ref,mascot

def camera(b):
 keys=b.get('show',[b['dest']]);keys=list(dict.fromkeys(keys+[b['dest']]+([b['origin']] if b.get('origin') else [])))
 coords=[PLACES[k][1:] for k in keys]
 lon=(min(c[0] for c in coords)+max(c[0] for c in coords))/2
 lat=(min(c[1] for c in coords)+max(c[1] for c in coords))/2
 # Reserve a compact, legible map theater between headline and spoken subtitles.
 for z in range(12,4,-1):
  pts=[merc(*c,z) for c in coords]
  if max(p[0] for p in pts)-min(p[0] for p in pts)<760 and max(p[1] for p in pts)-min(p[1] for p in pts)<780:break
 if len(coords)==1:z=min(z,b.get('zoom',8))
 cx,cy=merc(lon,lat,z)
 return cx,cy,z

def point(k,cam):
 cx,cy,z=cam;x,y=merc(*PLACES[k][1:],z)
 return round(540+x-cx),round(850+y-cy)

def tiles_for(cam):
 cx,cy,z=cam;l=cx-540;t=cy-850
 return [(z,x,y) for x in range(math.floor(l/256),math.ceil((l+W)/256)) for y in range(math.floor(t/256),math.ceil((t+H)/256))]

def background(cam):
 import numpy as np
 cx,cy,z=cam;l=cx-540;t=cy-850
 # One georegistered raster underlay and feathered cached imagery layers.
 # Blend in map coordinates so no mismatched tile-resolution rectangles remain.
 source=Image.open(A/'asia.jpg');meta=json.loads((A/'asia.json').read_text());e=meta['response']['extent'];world=20037508.342789244
 def mx(px):return px/(256*2**z)*world*2-world
 def my(py):return world-py/(256*2**z)*world*2
 box=((mx(l)-e['xmin'])/(e['xmax']-e['xmin'])*source.width,(e['ymax']-my(t))/(e['ymax']-e['ymin'])*source.height,(mx(l+W)-e['xmin'])/(e['xmax']-e['xmin'])*source.width,(e['ymax']-my(t+H))/(e['ymax']-e['ymin'])*source.height)
 im=source.crop(box).resize((W,H),Image.Resampling.LANCZOS).convert('RGBA')
 layers=[]
 for p in T.glob('*.jpg'):
  if p.name.startswith('fallback_'):continue
  tz,tx,ty=map(int,p.stem.split('-'));sc=2**(z-tz);rw=256*sc;rx=tx*rw-l;ry=ty*rw-t
  if rx<W and ry<H and rx+rw>0 and ry+rw>0:layers.append((tz,p,rx,ry,rw,sc))
 for tz,p,rx,ry,rw,sc in sorted(layers):
  x0=max(0,math.ceil(rx));y0=max(0,math.ceil(ry));x1=min(W,math.floor(rx+rw));y1=min(H,math.floor(ry+rw))
  if x1<=x0 or y1<=y0:continue
  crop=((x0-rx)/sc,(y0-ry)/sc,(x1-rx)/sc,(y1-ry)/sc)
  tile=Image.open(p).convert('RGBA').crop(crop).resize((x1-x0,y1-y0),Image.Resampling.LANCZOS)
  f=min(60,rw*.2)
  xx=np.arange(x0,x1)+.5;yy=np.arange(y0,y1)+.5
  ax=np.minimum(np.minimum((xx-rx)/f,(rx+rw-xx)/f),1)
  ay=np.minimum(np.minimum((yy-ry)/f,(ry+rw-yy)/f),1)
  alpha=np.minimum(ay[:,None],ax[None,:]);alpha=np.clip(alpha,0,1)
  tile.putalpha(Image.fromarray((alpha*255).astype('uint8')))
  im.alpha_composite(tile,(x0,y0))
 im=im.convert('RGB').filter(ImageFilter.GaussianBlur(.65))
 im=ImageEnhance.Color(im).enhance(.65);im=ImageEnhance.Brightness(im).enhance(.72)
 return im.convert('RGBA')

def sprite(name,width):
 im=Image.open(A/(name+'.png')).convert('RGBA')
 # Sprite-sheet crop already has alpha; retain original transparency and composition.
 im.thumbnail((width,width),Image.Resampling.LANCZOS)
 return im

def flag(im,p,color):
 d=ImageDraw.Draw(im);x,y=p
 d.line((x+40,y-75,x+40,y+10),fill=(250,235,197,255),width=3)
 d.polygon([(x+42,y-74),(x+96,y-61),(x+42,y-43)],fill=color,outline=(250,235,197,255))

def halo(im,p,color):
 # Local city emphasis, explicitly NOT an administrative/political territory polygon.
 l=Image.new('RGBA',im.size);d=ImageDraw.Draw(l);x,y=p
 for r,al,w in [(106,24,26),(86,50,15),(72,160,3)]:
  c=(*color[:3],al);d.ellipse((x-r,y-r,x+r,y+r),outline=c,width=w)
 return Image.alpha_composite(im,l)

def draw_scene(i,b):
 cam=camera(b);im=background(cam);draw=ImageDraw.Draw(im)
 # Short headline; map stays full screen, only a subtle top gradient.
 shade=Image.new('RGBA',(W,H));sd=ImageDraw.Draw(shade)
 for y in range(250):sd.line((0,y,W,y),fill=(3,13,23,round(230*(1-y/250))))
 im=Image.alpha_composite(im,shade);draw=ImageDraw.Draw(im)
 text(draw,(48,57),'กบฏเฉินเซิ่ง',29,fill=(255,245,221,255),anchor='lm',stroke=2)
 text(draw,(48,116),b['title'],48 if len(b['title'])<24 else 41,anchor='lm')
 text(draw,(48,177),b.get('note',''),28,fill=(224,234,237,255),anchor='lm',stroke=2)
 logo=Image.open(R/'assets/logo.png').convert('RGBA');logo.thumbnail((90,90));im.alpha_composite(logo,(941,37))
 p1=point(b['dest'],cam);p0=point(b.get('origin') or b['dest'],cam)
 route=Image.new('RGBA',im.size);rd=ImageDraw.Draw(route)
 if b.get('origin'):
  pts=[(round(p0[0]+(p1[0]-p0[0])*j/100-36*math.sin(math.pi*j/100)),round(p0[1]+(p1[1]-p0[1])*j/100-22*math.sin(math.pi*j/100))) for j in range(101)]
  for w,c in [(28,(34,208,248,45)),(12,(55,221,255,120)),(4,(219,252,255,255))]:rd.line(pts,fill=c,width=w,joint='curve')
  a=math.atan2(p1[1]-p0[1]+22*math.pi,p1[0]-p0[0]+36*math.pi)
  rd.polygon([p1,(p1[0]-24*math.cos(a)+12*math.sin(a),p1[1]-24*math.sin(a)-12*math.cos(a)),(p1[0]-24*math.cos(a)-12*math.sin(a),p1[1]-24*math.sin(a)+12*math.cos(a))],fill=CYAN)
 im=Image.alpha_composite(im,route)
 keys=b.get('show',[b['dest']]);keys=list(dict.fromkeys(keys+([b['origin']] if b.get('origin') else [])+[b['dest']]))
 used=[]
 for k in keys:
  p=point(k,cam)
  if not (60<p[0]<1020 and 270<p[1]<1350):continue
  rebel=k in b.get('controlled',[]);col=RED if rebel else GOLD
  im=halo(im,p,col)
  town=sprite('gate' if k in ['xianyang','hangu','xingyang'] else 'town',120)
  im.alpha_composite(town,(p[0]-town.width//2,p[1]-town.height//2))
  flag(im,p,col)
  # Deconflict adjacent labels vertically, retaining connector to true marker.
  lx,ly=p[0],p[1]-100
  for ox,oy in used:
   if abs(lx-ox)<245 and abs(ly-oy)<65:ly+=185
  used.append((lx,ly))
  d=ImageDraw.Draw(im);bb=d.textbbox((lx,ly),PLACES[k][0],font=font(36),anchor='mm',stroke_width=2)
  d.rounded_rectangle((bb[0]-12,bb[1]-8,bb[2]+12,bb[3]+8),radius=9,fill=(6,18,28,220),outline=(*col[:3],160),width=1)
  text(d,(lx,ly),PLACES[k][0],36,fill=(255,232,176,255),stroke=2)
 d=ImageDraw.Draw(im)
 d.ellipse((46,1645,63,1662),fill=RED);text(d,(78,1655),'กบฏ',27,fill=RED,anchor='lm',stroke=1);d.ellipse((208,1645,225,1662),fill=GOLD);text(d,(240,1655),'ฉิน',27,fill=GOLD,anchor='lm',stroke=1)
 text(d,(46,1701),'จุดเมืองโดยประมาณ · เส้นทางแสดงทิศทาง',24,fill=(225,232,235,255),anchor='lm',stroke=1)
 text(d,(46,1742),'ภาพบุคคลและสิ่งก่อสร้างจำลอง',23,fill=(210,220,224,255),anchor='lm',stroke=1)
 path=O/f'bg_{i:02}.png';im.convert('RGB').save(path)
 # Destination state appears after movement reaches it.
 state=Image.new('RGBA',(W,H));flag(state,p1,GOLD if b.get('side')=='qin' else RED)
 state=halo(state,p1,GOLD if b.get('side')=='qin' else RED);state.save(O/f'state_{i:02}.png')
 return p0,p1

def render_scene(i,b):
 n=round(b['end']*FPS)-round(b['start']*FPS);dur=n/FPS
 p=O/f'seg_{i:02}.mp4'
 if p.exists() and p.stat().st_size>100000 and os.environ.get('FORCE')!='1':
  check=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames','-of','csv=p=0',str(p)],capture_output=True,text=True)
  if check.returncode==0 and check.stdout.strip()==str(n):return p
 target=O/f'seg_{i:02}.building.mp4'
 p0,p1=draw_scene(i,b)
 army=sprite('qin' if b.get('side')=='qin' else 'rebels',230) if b['kind']!='death' else Image.new('RGBA',(230,230))
 army.save(O/f'army_{i:02}.png')
 portrait=sprite(b.get('portrait','chen'),94) if b.get('portrait') or b['kind']=='death' else Image.new('RGBA',(94,94));portrait.save(O/f'portrait_{i:02}.png')
 enemy=sprite('rebels' if b.get('side')=='qin' else 'qin',205) if b['kind'] in ['siege','qin_attack','revolt','battle'] else Image.new('RGBA',(205,205));enemy.save(O/f'enemy_{i:02}.png')
 u=f'min(max((t-0.4)/{max(1,dur*.74):.6f},0),1)'
 # Both the line and actor use the same parametric curve.
 if b.get('origin') and not b.get('planned'):
  x=f'{p0[0]}+({p1[0]-p0[0]})*({u})-36*sin(PI*({u}))'
  y=f'{p0[1]}+({p1[1]-p0[1]})*({u})-22*sin(PI*({u}))'
 else:x=str((p0 if b.get('planned') else p1)[0]-165);y=str((p0 if b.get('planned') else p1)[1]+75)
 filters=[f'[0:v][1:v]overlay=x=\'{x}-w/2\':y=\'{y}-h/2\':eval=frame:shortest=1[b1]']
 if b['kind']=='death':
  filters.append(f'[2:v]fade=t=out:st={dur*.45:.3f}:d={max(.3,dur*.30):.3f}:alpha=1[portrait]')
 else:filters.append('[2:v]format=rgba[portrait]')
 filters.append(f'[b1][portrait]overlay=x=\'{x}-w/2\':y=\'{y}-72\':eval=frame:shortest=1[b2a]')
 if b['kind'] in ['qin_attack','revolt','battle']:
  filters.append(f'[4:v]fade=t=out:st={dur*.65:.3f}:d={max(.3,dur*.16):.3f}:alpha=1[enemy]')
 else:filters.append('[4:v]format=rgba[enemy]')
 filters.append(f'[b2a][enemy]overlay=x={p1[0]+95}:y={p1[1]+35}:shortest=1[b2]')
 # Do not turn a siege into a capture. Actual captures alone change the flag.
 if b.get('capture'):
  filters.append(f"[b2][3:v]overlay=0:0:enable='gte(t,{b.get('capture_at',dur*.79):.3f})':shortest=1[v]")
 else:filters.append('[b2]format=yuv420p[v]')
 args=[]
 for f in [O/f'bg_{i:02}.png',O/f'army_{i:02}.png',O/f'portrait_{i:02}.png',O/f'state_{i:02}.png',O/f'enemy_{i:02}.png']:
  args+=['-loop','1','-framerate',FPS,'-i',f]
 ff(args+['-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map','[v]','-frames:v',n,'-an','-c:v','libx264','-threads','3','-preset','veryfast','-crf','17','-pix_fmt','yuv420p',target])
 q=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames','-of','csv=p=0',str(target)],capture_output=True,text=True)
 assert q.returncode==0 and q.stdout.strip()==str(n),(i,n,q.stdout,q.stderr)
 os.replace(target,p)
 print('scene',i,'done',n,flush=True);return p

def main():
 src,ref,mascot=setup();beats=json.loads((O/'beats.json').read_text())
 assert beats[0]['start']==0 and beats[-1]['end']==D
 assert all(abs(a['end']-b['start'])<.001 for a,b in zip(beats,beats[1:]))
 tiles=set(v for b in beats for v in tiles_for(camera(b)))
 print('prefetch',len(tiles),'tiles',flush=True)
 # No network required: use georegistered source raster plus cached native tiles.
 (O/'map_fallbacks.json').write_text(json.dumps(FALLBACKS,indent=2))
 print('tiles ready; offline lower-detail fallbacks',len(FALLBACKS),flush=True)
 if os.environ.get('PREP_ONLY')=='1':
  for i,b in enumerate(beats):draw_scene(i,b)
  return
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:clips=list(ex.map(lambda p:render_scene(*p),enumerate(beats)))
 if os.environ.get('PARTS_ONLY')=='1':return
 (O/'all.ffconcat').write_text('ffconcat version 1.0\n'+''.join(f"file '{p.name}'\n" for p in clips))
 output=O/'ChenSheng_V83_FULL_60FPS_REVIEW.mp4'
 ff(['-safe','0','-f','concat','-i',O/'all.ffconcat','-i',ref,'-stream_loop','-1','-c:v','libvpx-vp9','-i',mascot,
     '-filter_complex_threads','1','-filter_complex',f"[0:v]ass=filename={O/'captions.ass'}:fontsdir={A}[sub];[2:v]scale=195:-1,format=rgba[mas];[sub][mas]overlay=W-w-28:H-h-25:shortest=0,format=yuv420p[v]",
     '-map','[v]','-map','1:a:0','-c:v','libx264','-threads','6','-preset','veryfast','-crf','16','-c:a','copy','-frames:v',round(D*FPS),'-movflags','+faststart','-progress',O/'mux_progress.txt',output])
 print('OUTPUT',output,flush=True)
if __name__=='__main__':main()
