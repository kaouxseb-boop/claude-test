#!/usr/bin/env python3
"""V8 Chen Sheng uprising: 5s synchronized opening preview with true satellite terrain."""
import concurrent.futures, hashlib, io, json, math, shutil, subprocess, time, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W,H,FPS,SECONDS,UP=1080,1920,30,5,3
BW,BH=W*UP,H*UP
Z,TILE,WORLD=7,256,256*2**7
OUT=Path("chen_sheng/output")
OUT.mkdir(parents=True,exist_ok=True)
TILE_URL="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
GEO_URL="https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
FONT_URL="https://raw.githubusercontent.com/google/fonts/main/ofl/sarabun/Sarabun-Bold.ttf"
BBOX=(98.8,19.5,126.3,44.0)
DAZE=(117.22,33.78)  # approximation: Dazexiang/Suzhou Anhui region, NOT ancient surveyed location
XIANYANG=(108.72,34.34)
CHEN=(114.90,33.74)
COUNTRY_COLORS={"China":(255,203,95),"Mongolia":(64,232,252),"India":(100,245,196),
    "Myanmar":(160,112,246),"Vietnam":(78,225,166),"North Korea":(122,202,252),
    "South Korea":(80,212,255),"Nepal":(252,102,177),"Bhutan":(133,244,166),
    "Laos":(200,140,242),"Pakistan":(109,220,233)}
ASSETS=Path("chen_sheng/assets")

def fetch(url):
    last=None
    for n in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"HistoryMapV8-ChenSheng/1.0"})
            with urllib.request.urlopen(req,timeout=55) as fh:
                data=fh.read()
            if len(data)<100: raise RuntimeError("empty response")
            return data
        except Exception as err:
            last=err
            time.sleep(1.4*(n+1))
    raise RuntimeError(f"Download failed {url}: {last}")

def merc(lon,lat):
    lat=math.radians(max(-85,min(85,lat)))
    return WORLD*(lon+180)/360,WORLD*(1-math.asinh(math.tan(lat))/math.pi)/2

def setup():
    lo,b,hi,t=BBOX
    a,c=merc(lo,t);d,e=merc(hi,b)
    return ((a+d)/2,(c+e)/2),max(W/(d-a),H/(e-c))
MID,SCALE=setup()

def xy(ll):
    x,y=merc(*ll)
    return (x-MID[0])*SCALE+W/2,(y-MID[1])*SCALE+H/2

def ease(v):
    v=max(0,min(1,v))
    return v*v*(3-2*v)

def camera(t):
    f=ease((t-1.2)/3.8)
    point=xy((113.3,34.1))
    focus=(W/2+(point[0]-W/2)*f*0.48,H/2+(point[1]-H/2)*f*0.48)
    return focus,1+0.28*f

def pos(ll,c,z):
    x,y=xy(ll)
    return (x-c[0])*z+W/2,(y-c[1])*z+H/2

def mosaic():
    left,top=merc(BBOX[0],BBOX[3])
    right,bottom=merc(BBOX[2],BBOX[1])
    x0=max(0,math.floor(left/TILE)-1)
    x1=min(2**Z,math.ceil(right/TILE)+1)
    y0=max(0,math.floor(top/TILE)-1)
    y1=min(2**Z,math.ceil(bottom/TILE)+1)
    jobs=[(x,y) for y in range(y0,y1) for x in range(x0,x1)]
    print("Real satellite tiles:",len(jobs),flush=True)
    sheet=Image.new("RGB",((x1-x0)*TILE,(y1-y0)*TILE))
    def one(p):
        x,y=p
        im=Image.open(io.BytesIO(fetch(TILE_URL.format(z=Z,x=x,y=y)))).convert("RGB")
        if im.size!=(TILE,TILE):raise RuntimeError("tile geometry incorrect")
        return x,y,im
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        for x,y,im in pool.map(one,jobs):
            sheet.paste(im,((x-x0)*TILE,(y-y0)*TILE))
    sx,sy=MID[0]-x0*TILE,MID[1]-y0*TILE
    q=SCALE*UP
    affine=(1/q,0,sx-BW/(2*q),0,1/q,sy-BH/(2*q))
    return sheet.transform((BW,BH),Image.Transform.AFFINE,affine,
                           resample=Image.Resampling.BICUBIC)

def rings(geometry):
    if geometry.get("type")=="Polygon":return geometry["coordinates"]
    if geometry.get("type")=="MultiPolygon":
        return [ring for polygon in geometry["coordinates"] for ring in polygon]
    return []

def borders(base):
    feature_data=json.loads(fetch(GEO_URL))
    seen={}
    for feature in feature_data.get("features",[]):
        country=feature.get("properties",{}).get("ADMIN") or feature.get("properties",{}).get("NAME")
        if country not in COUNTRY_COLORS:continue
        polys=rings(feature.get("geometry",{}))
        if not polys:continue
        mask=Image.new("L",(BW,BH),0)
        fill=Image.new("L",(BW,BH),0)
        md=ImageDraw.Draw(mask); fd=ImageDraw.Draw(fill)
        n=0
        for ring in polys:
            if len(ring)<3:continue
            p=[(v*UP,w*UP) for v,w in (xy(ll) for ll in ring)]
            if max(x for x,y in p)<-100 or min(x for x,y in p)>BW+100:continue
            if max(y for x,y in p)<-100 or min(y for x,y in p)>BH+100:continue
            fd.polygon(p,fill=42 if country=="China" else 13)
            md.line(p+[p[0]],fill=210,width=2*UP,joint="curve")
            n+=1
        if not n:continue
        seen[country]=n
        color=COUNTRY_COLORS[country]
        base.paste(color,(0,0),fill)
        far=mask.filter(ImageFilter.GaussianBlur(12*UP))
        base.paste(color,(0,0),far.point(lambda a:min(120,int(a*0.45))))
        near=mask.filter(ImageFilter.GaussianBlur(3*UP))
        base.paste(color,(0,0),near.point(lambda a:min(220,int(a*0.9))))
        core=tuple(min(255,int(v*0.35+255*0.65)) for v in color)
        base.paste(core,(0,0),mask)
        del mask,fill,far,near
    if "China" not in seen:raise RuntimeError("Modern China boundary missing from Natural Earth")
    print("Modern reference-country glow layers:",seen,flush=True)
    return base,seen

def font(path,size):
    return ImageFont.truetype(str(path),size,layout_engine=ImageFont.Layout.RAQM)

def txt(draw,string,x,y,size,path,color=(255,255,255),anchor="mm",stroke=4):
    draw.text((round(x),round(y)),string,font=font(path,size),fill=color,anchor=anchor,
              stroke_width=stroke,stroke_fill=(6,14,24))

def halo(img,loc,c,z,rgb,phase):
    x,y=pos(loc,c,z)
    if not (-80<x<W+80 and -80<y<H+80):return
    mask=Image.new("L",(W,H),0)
    d=ImageDraw.Draw(mask)
    radius=36+33*phase
    d.ellipse((x-radius,y-radius,x+radius,y+radius),outline=225,width=5)
    wide=mask.filter(ImageFilter.GaussianBlur(18))
    img.paste(rgb,(0,0),wide.point(lambda a:min(190,int(a*.82))))
    img.paste(rgb,(0,0),mask)
    ImageDraw.Draw(img).ellipse((x-8,y-8,x+8,y+8),fill=(255,255,255),outline=rgb,width=3)

def frame(base,icon,path,t):
    c,z=camera(t)
    crop=((c[0]-W/(2*z))*UP,(c[1]-H/(2*z))*UP,
          (c[0]+W/(2*z))*UP,(c[1]+H/(2*z))*UP)
    img=base.crop(crop).resize((W,H),Image.Resampling.LANCZOS).convert("RGBA")
    # No misleading capital-to-rebel route: these are merely two historical reference locations.
    halo(img,XIANYANG,c,z,(255,205,93),.25)
    if t>1.2:halo(img,DAZE,c,z,(255,83,95),ease((t-1.2)/3.1))
    d=ImageDraw.Draw(img)
    # Non-generic dark title block sized for mobile.
    d.rounded_rectangle((22,25,W-22,248),radius=27,fill=(5,18,31),
                        outline=(255,190,79),width=3)
    txt(d,"HISTORY MAP  /  V8",54,62,25,path,(245,200,101),"lm",2)
    txt(d,"กบฏเฉินเซิ่ง",55,131,77,path,(255,247,224),"lm",3)
    txt(d,"จุดชนวนล้มราชวงศ์ฉิน",56,207,37,path,(255,213,116),"lm",3)
    # Coordinates are approximate pins using present-day geography.
    for ll,label,col,dx,dy in [
        (XIANYANG,"เสียนหยาง · เมืองหลวงฉิน",(255,213,109),-10,-47),
        (DAZE,"ต้าเจ๋อเซียง · จุดเริ่มกบฏ",(255,116,130),-150,44)]:
        x,y=pos(ll,c,z)
        if 60<x<W-60 and 300<y<H-450:
            txt(d,label,x+dx,y+dy,30,path,col,"mm",3)
    if t>1.85:
        # AI image-generated PNG with transparent alpha; never a programmatic clip-art substitute.
        p=ease((t-1.85)/0.58)
        iw=390
        ih=round(icon.height*(iw/icon.width))
        scaled=icon.resize((iw,ih),Image.Resampling.LANCZOS)
        a=scaled.getchannel("A").point(lambda v:int(v*p*0.96))
        scaled.putalpha(a)
        px,py=650,860+int((1-p)*55)
        shadow=Image.new("RGBA",(iw,ih),(0,0,0,0))
        shadow.putalpha(a.filter(ImageFilter.GaussianBlur(23)).point(lambda v:int(v*.58)))
        img=img.convert("RGBA")
        img.alpha_composite(shadow,(px+9,py+14))
        img.alpha_composite(scaled,(px,py))
    # Bottom lower third: editorial text, not claimed as word-aligned subtitles.
    d=ImageDraw.Draw(img)
    d.rounded_rectangle((25,H-322,W-25,H-147),radius=27,
                        fill=(4,14,25,237),outline=(70,165,180,230),width=3)
    txt(d,"ใครจะคิดว่า…",W/2,H-268,58,path,(255,255,255),"mm",4)
    txt(d,"จักรวรรดิฉินจะเริ่มสั่นคลอน",W/2,H-197,43,path,(255,213,109),"mm",4)
    txt(d,"แผนที่ฐานปัจจุบัน · หมุดโบราณเป็นตำแหน่งโดยประมาณ",W/2,H-90,24,path,
        (211,230,232),"mm",2)
    d.rectangle((0,H-7,int(W*t/SECONDS),H),fill=(62,233,247))
    return img.convert("RGB")

def qa(mp4):
    subprocess.check_call(["ffmpeg","-v","error","-i",str(mp4),"-f","null","-"])
    result=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames",
        "-show_streams","-show_format","-of","json",str(mp4)]))
    v=next(s for s in result["streams"] if s["codec_type"]=="video")
    a=next(s for s in result["streams"] if s["codec_type"]=="audio")
    assert (v["width"],v["height"])==(W,H)
    assert int(v["nb_read_frames"])==SECONDS*FPS
    assert abs(float(result["format"]["duration"])-SECONDS)<.18
    assert a["sample_rate"]=="24000"
    report={"status":"PASS encoded MP4 + audio video streams and decode",
      "result":"technical 5-second preview (NOT full 402.12-second narration)",
      "duration_video_sec":float(v["duration"]),"duration_audio_sec":float(a["duration"]),
      "frames":int(v["nb_read_frames"]),"resolution":[W,H],"fps":FPS,
      "map":"Esri World Imagery z7 + Natural Earth modern reference geography",
      "geohistory":"ancient Qin state boundary not asserted; modern country borders for geographic orientation only",
      "reference_pins":"Xianyang city point / Dazexiang approximate modern-region proxy",
      "jedi":"individually colored modern-country borders; three glow layers with sharp core",
      "sharpness":"3240x5760 source, LANCZOS downsample, H.264 CRF16",
      "audio":"first 5s excerpt from user-supplied Chen Sheng original WAV encoded AAC",
      "branding":"original channel logo/mascot unavailable; technical preview only",
      "subtitles":"intro editorial lower third; no claim of speech-level ASR alignment",
      "AI_icon":"generated historical 2D Chen Sheng PNG with transparency",
      "mp4_sha256":hashlib.sha256(mp4.read_bytes()).hexdigest()}
    (OUT/"qa.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)

def main():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):raise RuntimeError("FFmpeg required")
    fontfile=OUT/"Sarabun-Bold.ttf"
    fontfile.write_bytes(fetch(FONT_URL))
    icon=Image.open(ASSETS/"chen-sheng-2d.png").convert("RGBA")
    audio=ASSETS/"opening-5s.aac"
    assert audio.is_file() and audio.stat().st_size>20000
    m=mosaic()
    bg,seen=borders(m)
    filename=OUT/"V8_ChenSheng_5sec_PREVIEW.mp4"
    command=["ffmpeg","-y","-hide_banner","-loglevel","error",
       "-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}",
       "-framerate",str(FPS),"-i","pipe:0",
       "-i",str(audio),"-map","0:v:0","-map","1:a:0",
       "-c:v","libx264","-pix_fmt","yuv420p","-preset","medium","-crf","16",
       "-c:a","aac","-b:a","96k","-t",str(SECONDS),
       "-movflags","+faststart",str(filename)]
    proc=subprocess.Popen(command,stdin=subprocess.PIPE)
    shots=[]
    try:
        for i in range(FPS*SECONDS):
            im=frame(bg,icon,fontfile,i/FPS)
            proc.stdin.write(im.tobytes())
            if i in (15,75,135):shots.append(im.resize((270,480)))
            if i%30==0:print("frames written",i,flush=True)
    finally:
        proc.stdin.close()
    if proc.wait()!=0:raise RuntimeError("FFmpeg failed")
    contact=Image.new("RGB",(810,480))
    for i,shot in enumerate(shots):contact.paste(shot,(i*270,0))
    contact.save(OUT/"contact_sheet.jpg",quality=94)
    qa(filename)

if __name__=="__main__":
    main()
