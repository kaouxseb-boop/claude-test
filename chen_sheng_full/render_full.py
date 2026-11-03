#!/usr/bin/env python3
"""Chen Sheng full-length V8 map production, 60 fps, real terrain."""
import io, os, math, json, hashlib, subprocess, urllib.request, concurrent.futures
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT=Path("chen_sheng_full"); AS=ROOT/"assets"; OUT=ROOT/"output"; OUT.mkdir(parents=True,exist_ok=True)
W,H,UP,FPS=1080,1920,3,60
AUDIO=OUT/"narration.aac"; MASCOT=OUT/"mascot.webm"
IMG="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
NE="https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
FONT="https://raw.githubusercontent.com/google/fonts/main/ofl/sarabun/Sarabun-Bold.ttf"
# Historical locations are approximate reference coordinates, not surveyed Han-era GPS.
PLACES={
 "daze":("ต้าเจ๋อเซียง",117.22,33.78),"yuyang":("อวี๋หยาง",116.95,40.35),
 "qi":("เมืองฉี",117.10,33.64),"zhi":("จื้อ",116.75,33.63),
 "zan":("จ้าน",116.25,33.75),"ku":("ขู่",115.50,33.86),
 "zhe":("เจ้อ",115.31,34.07),"qiao":("เฉียว",115.77,33.88),
 "chen":("เมืองเฉิน",114.90,33.74),"xingyang":("สิงหยาง",113.39,34.79),
 "hangu":("ด่านหานกู่",110.80,34.60),"xi":("ซี",109.18,34.30),
 "xianyang":("เสียนหยาง",108.72,34.34),"lishan":("หลีซาน",109.27,34.36),
 "caoyang":("เฉาหยาง",110.25,34.63),"mianchi":("เหมี่ยนฉือ",111.76,34.76),
 "aocang":("อ๋าวชาง",113.46,34.84),"xiachengfu":("เซี่ยเฉิงฝู่",116.7,33.3),
 "julu":("จวี้ลู่",115.04,37.22)
}
# Each scene is a geographic beat; durations are editorial estimates pending final speech alignment.
SCENES=[
("จักรวรรดิฉิน","xianyang",None,12),("เฉินเซิ่ง ชาวนาสามัญชน","daze",None,12),
("จุดจบที่คาดไม่ถึง","xiachengfu",None,13),("เมื่อกว่า 2,200 ปีก่อน","xianyang",None,11),
("ทหารเกณฑ์ราว 900 คน","daze","yuyang",14),("ฝนทำให้ล่าช้า","daze",None,12),
("เฉินเซิ่งและอู๋กว่าง","daze",None,13),("ลุกฮือที่ต้าเจ๋อเซียง","daze",None,15),
("ชัยชนะแรก เมืองฉี","qi","daze",12),("ยึดเมืองจื้อ","zhi","qi",9),
("กองทัพขยายไปจ้าน","zan","zhi",9),("เมืองขู่และเจ้อ","zhe","ku",11),
("กองกำลังถึงเฉียว","qiao","zhe",9),("รุกขึ้นเมืองเฉิน","chen","qiao",15),
("ตั้งรัฐจางฉู่","chen",None,14),("อู๋กว่างตีสิงหยาง","xingyang","chen",16),
("หลี่โหยวป้องกันเมือง","xingyang",None,13),("โจวเหวินบุกตะวันตก","hangu","chen",13),
("รุกถึงเขตซี","xi","hangu",12),("ใกล้เมืองหลวงฉิน","xianyang","xi",12),
("จางหานระดมนักโทษ","lishan",None,13),("กองทัพฉินโต้กลับ","xi","lishan",12),
("โจวเหวินถอยเฉาหยาง","caoyang","xi",10),("แตกพ่ายที่เหมี่ยนฉือ","mianchi","caoyang",14),
("เถียนจางสังหารอู๋กว่าง","xingyang",None,14),("ศึกคลังเสบียงอ๋าวชาง","aocang","xingyang",12),
("จางหานตีสิงหยาง","xingyang","aocang",10),("กองทัพฉินมุ่งเมืองเฉิน","chen","xingyang",14),
("เฉินเซิ่งหนีออกจากเมือง","chen",None,13),("ถูกคนขับรถม้าสังหาร","xiachengfu","chen",17),
("ลวี่เฉินกลับยึดเมืองเฉิน","chen","xiachengfu",12),("ไฟกบฏยังไม่ดับ","chen",None,11),
("เซี่ยงอวี่ชนะที่จวี้ลู่","julu",None,13),("หลิวปังเข้าสู่เสียนหยาง","xianyang","julu",14),
("จักรวรรดิฉินล่มสลาย","xianyang",None,13),("ชื่อของเฉินเซิ่งในประวัติศาสตร์","daze",None,13)]
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":"ChenSheng-V8-Full/1.0"})
 for i in range(4):
  try:
   with urllib.request.urlopen(req,timeout=60) as f:return f.read()
  except Exception:
   if i==3:raise
def concat_parts(prefix,suffix):
 names=sorted(AS.glob(prefix+".part*"))
 assert names, prefix
 with open(OUT/suffix,"wb") as dest:
  for name in names:
   with open(name,"rb") as src:
    while True:
     b=src.read(1024*1024)
     if not b:break
     dest.write(b)
def merc(lon,lat,z):
 world=256*2**z; lat=math.radians(max(-85,min(85,lat)))
 return world*(lon+180)/360,world*(1-math.asinh(math.tan(lat))/math.pi)/2
def basemap(lon,lat,z=8):
 # Source map registered by Web Mercator. No hand-drawn coastline.
 cx,cy=merc(lon,lat,z); scale=2.3
 tw,th=math.ceil(W*UP/scale),math.ceil(H*UP/scale)
 l=cx-tw/2;t=cy-th/2
 x0=math.floor(l/256);y0=math.floor(t/256)
 x1=math.ceil((l+tw)/256);y1=math.ceil((t+th)/256)
 sheet=Image.new("RGB",((x1-x0)*256,(y1-y0)*256))
 jobs=[(x,y) for y in range(y0,y1) for x in range(x0,x1)]
 def tile(pos):
  x,y=pos
  if not 0<=x<2**z or not 0<=y<2**z:return x,y,None
  im=Image.open(io.BytesIO(fetch(IMG.format(z=z,x=x,y=y)))).convert("RGB")
  assert im.size==(256,256)
  return x,y,im
 with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
  for x,y,im in ex.map(tile,jobs):
   if im:sheet.paste(im,((x-x0)*256,(y-y0)*256))
 crop=sheet.crop((round(l-x0*256),round(t-y0*256),round(l-x0*256+tw),round(t-y0*256+th)))
 return crop.resize((W*UP,H*UP),Image.Resampling.LANCZOS), (cx,cy,z,scale)
def geo_xy(lon,lat,proj):
 cx,cy,z,scale=proj;x,y=merc(lon,lat,z)
 return ((x-cx)*scale+W/2)*UP,((y-cy)*scale+H/2)*UP
def text(d,string,x,y,size,font,fill,anchor="mm",stroke=3):
 d.text((int(x),int(y)),string,font=ImageFont.truetype(str(font),size),fill=fill,anchor=anchor,stroke_width=stroke,stroke_fill=(3,12,25))
def scene_frame(idx,scene,font,logo):
 title,dest,origin,_=scene;label,lon,lat=PLACES[dest]
 image,proj=basemap(lon,lat); image=image.convert("RGBA")
 overlay=Image.new("RGBA",image.size,(0,0,0,0));d=ImageDraw.Draw(overlay)
 # Reference modern-country coastlines from Natural Earth, no invented Qin borders.
 countries=json.loads((OUT/"countries.geojson").read_text())
 mask=Image.new("L",image.size,0);md=ImageDraw.Draw(mask)
 for feat in countries["features"]:
  if (feat.get("properties",{}).get("ADMIN") or feat.get("properties",{}).get("NAME"))!="China":continue
  geom=feat["geometry"];polys=[geom["coordinates"]] if geom["type"]=="Polygon" else geom["coordinates"]
  for polygon in polys:
   for ring in polygon:
    pts=[geo_xy(a,b,proj) for a,b in ring]
    if len(pts)>2:md.line(pts+[pts[0]],fill=230,width=UP*2)
 for radius,alpha in [(36,54),(10,115)]:
  blurred=mask.filter(ImageFilter.GaussianBlur(radius))
  overlay.paste((255,190,85,alpha),(0,0),blurred.point(lambda k:int(k*alpha/255)))
 overlay.paste((255,235,170,255),(0,0),mask)
 d=ImageDraw.Draw(overlay)
 def pin(key,color):
  nm,a,b=PLACES[key];x,y=geo_xy(a,b,proj)
  r=13*UP
  d.ellipse((x-r,y-r,x+r,y+r),fill=color,outline=(255,255,255,255),width=4*UP)
  text(d,nm,x,y-55*UP,30*UP,font,(255,214,117),stroke=4*UP)
  return x,y
 if origin and origin in PLACES:
  a,b,c=PLACES[origin];x1,y1=geo_xy(b,c,proj)
  x2,y2=geo_xy(lon,lat,proj)
  # Geographic route is schematic straight connector, not exact military road.
  for width,color in [(25,(20,215,248,50)),(11,(20,215,248,135)),(4,(210,251,255,255))]:
   d.line([(x1,y1),(x2,y2)],fill=color,width=width*UP)
  pin(origin,(47,213,241,255))
 pin(dest,(255,109,97,255))
 image=Image.alpha_composite(image,overlay).convert("RGB")
 image=image.resize((W,H),Image.Resampling.LANCZOS)
 d=ImageDraw.Draw(image)
 d.rounded_rectangle((28,38,1052,192),radius=24,fill=(5,18,31),outline=(242,194,95),width=3)
 text(d,title,540,120,54,font,(255,235,173),stroke=3)
 d.rounded_rectangle((30,290,385,344),radius=15,fill=(6,21,36),outline=(255,208,121),width=2)
 text(d,"ตำแหน่งประวัติศาสตร์โดยประมาณ",207,317,23,font,(255,235,201),stroke=1)
 image.paste(logo,(W-logo.width-32,24),logo)
 return image
def main():
 concat_parts("audio","narration.aac");concat_parts("mascot","mascot.webm")
 font=OUT/"Sarabun-Bold.ttf";font.write_bytes(fetch(FONT))
 (OUT/"countries.geojson").write_bytes(fetch(NE))
 logo=Image.open(AS/"logo.png").convert("RGBA");logo.thumbnail((105,105))
 # The original PCM WAV has exactly 402.120s; ADTS ffprobe bitrate estimates can overstate duration.
 duration=402.12
 total=sum(s[3] for s in SCENES);scene_durations=[duration*s[3]/total for s in SCENES]
 manifest=[];concat=[]
 for i,s in enumerate(SCENES):
  target=OUT/f"scene_{i:03d}.jpg"
  if not target.exists():
   image=scene_frame(i,s,font,logo);image.save(target,quality=95,subsampling=0)
  manifest.append({"scene":i,"label":s[0],"location":s[1],"origin":s[2],"duration":scene_durations[i]})
  concat.append(f"file '{target.name}'");concat.append(f"duration {scene_durations[i]:.6f}")
 concat.append(f"file 'scene_{len(SCENES)-1:03d}.jpg'")
 (OUT/"slideshow.ffconcat").write_text("ffconcat version 1.0\n"+"\n".join(concat)+"\n")
 (OUT/"storyboard.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 # VP9 mascot alpha is decoded through libvpx-vp9 for overlay.
 output=OUT/"ChenSheng_Full_V8_60FPS.mp4"
 cmd=["ffmpeg","-y","-loglevel","error","-safe","0","-f","concat","-i",str(OUT/"slideshow.ffconcat"),
      "-i",str(AUDIO),"-stream_loop","-1","-c:v","libvpx-vp9","-i",str(MASCOT),
      "-filter_complex","[0:v]fps=60,format=rgba[bg];[2:v]scale=165:-1,format=rgba[mas];[bg][mas]overlay=W-w-16:H-h-14:shortest=0,format=yuv420p[v]",
      "-map","[v]","-map","1:a:0","-c:v","libx264","-preset","veryfast","-crf","16","-c:a","aac","-b:a","96k",
      "-t",str(duration),"-movflags","+faststart",str(output)]
 subprocess.check_call(cmd)
 check=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames","-show_streams","-show_format","-of","json",str(output)]))
 v=next(s for s in check["streams"] if s["codec_type"]=="video")
 a=next(s for s in check["streams"] if s["codec_type"]=="audio")
 assert (v["width"],v["height"])==(1080,1920)
 assert abs(float(check["format"]["duration"])-duration)<.3
 assert abs(int(v["nb_read_frames"])-round(duration*60))<=2
 subprocess.check_call(["ffmpeg","-v","error","-i",str(output),"-f","null","-"])
 subprocess.check_call(["ffmpeg","-y","-loglevel","error","-ss","00:03:00","-i",str(output),"-frames:v","1",str(OUT/"middle.jpg")])
 report={"status":"PASS technical video/decode","duration_sec":duration,"fps":60,"frames":v["nb_read_frames"],"video_codec":v["codec_name"],"mascot":"original animated keyed mascot", "logo":"original channel logo","map":"Esri World Imagery z8 + Natural Earth modern boundaries","scene_count":len(SCENES),"editorial_issues":["Scene durations estimated from narrative weights, NOT aligned transcript","Full voiced Thai subtitles not yet available: narration is preserved, visual scene headings only","All historic pins approximate modern geographical proxies","Human visual review pending"],"sha256":hashlib.sha256(output.read_bytes()).hexdigest()}
 (OUT/"qa.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps(report,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
