#!/usr/bin/env python3
"""Map Story V8: honest 5-second SILENT motion proof, public geography only."""
import concurrent.futures
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W,H,FPS,SECONDS = 1080,1920,30,5
TILE_Z=5
TILE_SIZE=256
TILE_X0,TILE_X1=14,22
TILE_Y0,TILE_Y1=5,15
WORLD=256*(2**TILE_Z)
OUT=Path("dist")
OUT.mkdir(parents=True,exist_ok=True)
UA_URL="https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/gbOpen/UKR/ADM0/geoBoundaries-UKR-ADM0.geojson"
NE_URL="https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
FONT_URL="https://raw.githubusercontent.com/google/fonts/main/ofl/sarabun/Sarabun-Bold.ttf"
FLAG_URL="https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Flag_of_the_Soviet_Union.svg/640px-Flag_of_the_Soviet_Union.svg.png"
TILE_URL="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

def fetch(url, retries=4):
    last=None
    for attempt in range(retries):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"MapStoryV8VisualPreview/0.1 (public educational visualization)"})
            with urllib.request.urlopen(req,timeout=45) as resp:
                data=resp.read()
            if len(data)<100:
                raise RuntimeError("download too small "+url)
            return data
        except Exception as e:
            last=e
            time.sleep((attempt+1)*1.1)
    raise RuntimeError("Fetch failed "+url+" : "+str(last))

def merc(lon,lat):
    lat=max(-85.0,min(85.0,lat))
    r=math.radians(lat)
    return ((lon+180)/360*WORLD,(1-math.asinh(math.tan(r))/math.pi)/2*WORLD)

def polygons_from_geo(geom):
    if geom["type"]=="Polygon":
        polys=[geom["coordinates"]]
    elif geom["type"]=="MultiPolygon":
        polys=geom["coordinates"]
    else:
        return []
    return [poly[0] for poly in polys if poly and len(poly[0])>=3]

def point_in_ring(lon,lat,ring):
    inside=False
    j=len(ring)-1
    for i in range(len(ring)):
        xi,yi=ring[i];xj,yj=ring[j]
        if ((yi>lat)!=(yj>lat)) and (lon<(xj-xi)*(lat-yi)/(yj-yi+1e-20)+xi):
            inside=not inside
        j=i
    return inside

def is_inside(geom,lon,lat):
    return any(point_in_ring(lon,lat,ring) for ring in polygons_from_geo(geom))

def perp_distance(p,a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    if dx*dx+dy*dy<1e-15:return math.dist(p,a)
    return abs(dy*p[0]-dx*p[1]+b[0]*a[1]-b[1]*a[0])/math.hypot(dx,dy)

def simplify(points,tol=0.28):
    if len(points)<5:return points
    # Iterative RDP, with endpoints guaranteed.
    keep={0,len(points)-1}
    stack=[(0,len(points)-1)]
    while stack:
        a,b=stack.pop()
        m=-1;mi=-1
        for i in range(a+1,b):
            d=perp_distance(points[i],points[a],points[b])
            if d>m:m=d;mi=i
        if m>tol:
            keep.add(mi);stack.extend([(a,mi),(mi,b)])
    return [points[i] for i in sorted(keep)]

def prep_geom(geom):
    rings=[]
    for ring in polygons_from_geo(geom):
        pts=[merc(lon,lat) for lon,lat in ring]
        rings.append(simplify(pts))
    return rings

def camera(t):
    # Geography-first: broad position -> mid-scale policy movement, then hold.
    p=min(1.0,max(0,t/1.55))
    p=p*p*(3-2*p)
    center_lon=32.4+0.55*p
    center_lat=50.8+0.20*p
    zoom=1.30+0.33*p
    return merc(center_lon,center_lat),zoom

def screen(pt,center,zoom):
    return ((pt[0]-center[0])*zoom+W/2,(pt[1]-center[1])*zoom+H/2)

def screen_ring(ring,center,zoom):
    return [screen(p,center,zoom) for p in ring]

def ease(x):
    x=max(0.0,min(1.0,x))
    return x*x*(3-2*x)

def drawmask(rings,center,zoom):
    mask=Image.new("L",(W,H),0)
    d=ImageDraw.Draw(mask)
    for r in rings:
        if len(r)>2:
            d.polygon(screen_ring(r,center,zoom),fill=255)
    return mask

def outline(base,rings,center,zoom,color,width=4,glow=10):
    edge=Image.new("L",(W,H),0)
    d=ImageDraw.Draw(edge)
    for r in rings:
        if len(r)>2:
            points=screen_ring(r,center,zoom)
            # Skip remote polygons wholly outside the working frame.
            if max(p[0] for p in points)<-40 or min(p[0] for p in points)>W+40 or max(p[1] for p in points)<-40 or min(p[1] for p in points)>H+40:
                continue
            d.line(points+[points[0]],fill=255,width=width,joint="curve")
    bloom=edge.filter(ImageFilter.GaussianBlur(glow))
    tint=Image.new("RGB",(W,H),color)
    base.paste(tint,(0,0),bloom.point(lambda x:int(x*0.54)))
    base.paste(tint,(0,0),edge)
    return base

def font(size):
    try:return ImageFont.truetype(str(FONT_PATH),size,layout_engine=ImageFont.Layout.RAQM)
    except Exception:return ImageFont.truetype(str(FONT_PATH),size)

def label(base,text,x,y,fsize=49,fg=(255,217,95),center=True):
    d=ImageDraw.Draw(base)
    f=font(fsize)
    bb=d.textbbox((0,0),text,font=f,stroke_width=3)
    tw=bb[2]-bb[0];th=bb[3]-bb[1]
    if center:x-=tw/2
    pad_x,pad_y=20,12
    rect=(int(x-pad_x),int(y-pad_y),int(x+tw+pad_x),int(y+th+pad_y+14))
    d.rounded_rectangle(rect,radius=18,fill=(8,13,22),outline=(214,174,77),width=2)
    d.text((int(x),int(y-bb[1])),text,font=f,fill=fg,stroke_width=2,stroke_fill=(2,4,8))
    return rect

def text_center(base,text,y,size,color=(255,255,255),stroke=5):
    d=ImageDraw.Draw(base)
    f=font(size)
    bb=d.textbbox((0,0),text,font=f,stroke_width=stroke)
    x=(W-(bb[2]-bb[0]))/2
    d.text((int(x),int(y-bb[1])),text,font=f,fill=color,stroke_width=stroke,stroke_fill=(2,6,14))

def satellite_mosaic():
    jobs=[(x,y) for y in range(TILE_Y0,TILE_Y1) for x in range(TILE_X0,TILE_X1)]
    background=Image.new("RGB",((TILE_X1-TILE_X0)*256,(TILE_Y1-TILE_Y0)*256),(18,26,33))
    def tile(job):
        x,y=job
        raw=fetch(TILE_URL.format(z=TILE_Z,y=y,x=x))
        image=Image.open(io.BytesIO(raw)).convert("RGB")
        if image.size!=(256,256):raise RuntimeError("tile dimensions invalid "+str(job))
        return x,y,image
    print("Downloading",len(jobs),"genuine satellite tiles",flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for x,y,im in pool.map(tile,jobs):
            background.paste(im,((x-TILE_X0)*256,(y-TILE_Y0)*256))
    return background

def sat_frame(mosaic,center,zoom):
    c_x=center[0]-TILE_X0*256;c_y=center[1]-TILE_Y0*256
    crop_w=W/zoom;crop_h=H/zoom
    left=c_x-crop_w/2;top=c_y-crop_h/2
    box=(int(left),int(top),int(left+crop_w),int(top+crop_h))
    if box[0]<0 or box[1]<0 or box[2]>mosaic.width or box[3]>mosaic.height:
        raise RuntimeError("Satellite source out of bounds "+str(box))
    return mosaic.crop(box).resize((W,H),Image.Resampling.BICUBIC)

def tinted(base,mask,color,opacity):
    overlay=Image.new("RGB",(W,H),color)
    active=mask.point(lambda x:int(x*opacity/255))
    base.paste(overlay,(0,0),active)

def draw_pin(base,pt,center,zoom,rgb=(254,221,113),radius=10):
    x,y=screen(merc(*pt),center,zoom)
    if x<-20 or x>W+20 or y<-20 or y>H+20:return
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(layer)
    d.ellipse((x-radius*3,y-radius*3,x+radius*3,y+radius*3),fill=(*rgb,60))
    d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=(*rgb,255),outline=(255,255,255,255),width=2)
    base.paste(layer,(0,0),layer)

def quadratic(a,b,c,t):
    q=1-t
    return (q*q*a[0]+2*q*t*b[0]+t*t*c[0],q*q*a[1]+2*q*t*b[1]+t*t*c[1])

def path_for(origin,target,center,zoom,curve):
    a=screen(merc(*origin),center,zoom)
    c=screen(merc(*target),center,zoom)
    dx=c[0]-a[0];dy=c[1]-a[1]
    control=((a[0]+c[0])/2-curve*dy,(a[1]+c[1])/2+curve*dx)
    return [quadratic(a,control,c,i/100) for i in range(101)]

def draw_route(base,origin,target,center,zoom,frac,index):
    pts=path_for(origin,target,center,zoom,0.15+0.04*index)
    count=max(1,min(100,int(100*frac)))
    visible=pts[:count+1]
    top=Image.new("L",(W,H),0)
    d=ImageDraw.Draw(top)
    d.line(visible,fill=255,width=7,joint="curve")
    bloom=top.filter(ImageFilter.GaussianBlur(15))
    base.paste((239,193,62),(0,0),bloom.point(lambda x:int(x*0.64)))
    base.paste((255,219,111),(0,0),top)
    if count>2:
        x,y=visible[-1];px,py=visible[-4]
        angle=math.atan2(y-py,x-px)
        sz=22
        arrow=[(x+sz*math.cos(angle),y+sz*math.sin(angle)),
               (x+sz*math.cos(angle+2.5),y+sz*math.sin(angle+2.5)),
               (x+sz*math.cos(angle-2.5),y+sz*math.sin(angle-2.5))]
        ImageDraw.Draw(base).polygon(arrow,fill=(255,238,149))

def grab_movie_samples(filename):
    for stamp,name in [(0.3,"start"),(2.5,"middle"),(4.6,"end")]:
        subprocess.check_call(["ffmpeg","-y","-hide_banner","-loglevel","error","-ss",str(stamp),"-i",str(filename),
                               "-frames:v","1",str(OUT/(name+".jpg"))])
    subprocess.check_call(["ffmpeg","-v","error","-i",str(filename),"-f","null","-"])
    info=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(filename)]))
    stream=next(s for s in info["streams"] if s["codec_type"]=="video")
    frames=int(stream.get("nb_frames","0") or 0)
    duration=float(info["format"]["duration"])
    assert stream["width"]==W and stream["height"]==H,(stream["width"],stream["height"])
    assert frames==FPS*SECONDS,frames
    assert abs(duration-SECONDS)<0.10,duration
    assert not any(s["codec_type"]=="audio" for s in info["streams"]),"unexpected audio"
    (OUT/"qa.json").write_text(json.dumps({
        "frames":frames,"seconds":duration,"width":W,"height":H,
        "audio":"intentionally silent visual test, not source-voice aligned",
        "geography":"geoBoundaries UKR ADM0 incl Crimea; Natural Earth other shapes",
        "imagery":"Esri World Imagery tile server, geographically projected",
        "paths":"illustrative/schematic, not verified grain shipping routes",
        "status":"file/decode QA passed; no human watch-through asserted"},ensure_ascii=False,indent=2),encoding="utf8")

def main():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg tools absent")
    global FONT_PATH
    FONT_PATH=OUT/"Sarabun-Bold.ttf"
    FONT_PATH.write_bytes(fetch(FONT_URL))
    print("Map source: geoBoundaries Ukraine and Natural Earth",flush=True)
    uk_data=json.loads(fetch(UA_URL))
    if uk_data.get("type")=="FeatureCollection":
        ua_geom=uk_data["features"][0]["geometry"]
    elif uk_data.get("type")=="Feature":
        ua_geom=uk_data["geometry"]
    else:ua_geom=uk_data
    if not is_inside(ua_geom,34.10,44.95):
        raise RuntimeError("CRIMEA CHECK FAILED: current Ukraine polygon excludes Crimea")
    country_data=json.loads(fetch(NE_URL))
    rus_feature=next(f for f in country_data["features"] if f.get("properties",{}).get("ADMIN")=="Russia")
    ua_rings=prep_geom(ua_geom)
    ru_rings=prep_geom(rus_feature["geometry"])
    # Small public example graphics; no user logo, mascot, voice, or private assets.
    try:
        FLAG=Image.open(io.BytesIO(fetch(FLAG_URL))).convert("RGBA")
        print("Loaded historical Soviet flag artwork",flush=True)
    except Exception as error:
        raise RuntimeError("Cannot verify Soviet flag source; refusing to substitute an incorrect emblem") from error
    mosaic=satellite_mosaic()
    filename=OUT/"Holodomor_V8_5sec_SILENT_preview.mp4"
    encoder=subprocess.Popen(["ffmpeg","-y","-hide_banner","-loglevel","error","-f","rawvideo",
        "-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
        "-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(filename)],stdin=subprocess.PIPE)
    farms=[(30.52,50.45),(33.45,49.6),(35.05,48.47)]
    moscow=(37.6173,55.7558)
    try:
        for frame in range(FPS*SECONDS):
            t=frame/FPS
            cent,zoom=camera(t)
            im=sat_frame(mosaic,cent,zoom)
            # Maintain real natural terrain under thematic overlays.
            im.paste((3,8,16),(0,0),Image.new("L",(W,H),92))
            ru_mask=drawmask(ru_rings,cent,zoom)
            tinted(im,ru_mask,(120,30,35),65)
            ua_mask=drawmask(ua_rings,cent,zoom)
            # Fill the entire Ukraine geographic silhouette with historical Soviet flag.
            # The flag is only an illustrative USSR-era overlay, NOT a claim of sovereignty.
            bb=ua_mask.getbbox()
            if bb:
                x0,y0,x1,y1=bb
                w,h=max(1,x1-x0),max(1,y1-y0)
                flag=FLAG.resize((w,h),Image.Resampling.BICUBIC).convert("RGB")
                flag_layer=Image.new("RGB",(W,H),(0,0,0))
                flag_layer.paste(flag,(x0,y0))
                mask=ua_mask.point(lambda v:int(v*0.70))
                im.paste(flag_layer,(0,0),mask)
            outline(im,ru_rings,cent,zoom,(194,75,65),3,9)
            outline(im,ua_rings,cent,zoom,(103,235,255),6,17)
            # Place pins and route symbols at shared coordinate anchors.
            draw_pin(im,moscow,cent,zoom,(255,189,88),9)
            for j,pt in enumerate(farms):
                fade=1-ease((t-3.8)/0.8)
                if fade>0:
                    x,y=screen(merc(*pt),cent,zoom)
                    r=9+5*math.sin(t*3+j)
                    dr=ImageDraw.Draw(im)
                    dr.ellipse((x-r,y-r,x+r,y+r),fill=(int(245*fade),int(201*fade),int(85*fade)),outline=(255,246,182),width=2)
            if t>=2.04:
                for j,pt in enumerate(farms):
                    head=ease((t-2.04-j*0.18)/2.3)
                    if head>0:
                        draw_route(im,pt,moscow,cent,zoom,head,j)
            x,y=screen(merc(31.4,48.8),cent,zoom)
            label(im,"ยูเครน",x,y,49)
            x,y=screen(merc(*moscow),cent,zoom)
            label(im,"มอสโก",x+75,y-50,45,center=False)
            # Editorial text and subtitles stay in dedicated, legible safe areas.
            dr=ImageDraw.Draw(im)
            dr.rounded_rectangle((62,86,1018,286),radius=30,fill=(8,15,24),outline=(228,188,84),width=3)
            text_center(im,"โฮโลโดมอร์",105,100,(255,238,196),6)
            text_center(im,"ยูเครน ค.ศ. 1932–1933",223,39,(237,245,253),3)
            if t>=2.4:
                p=ease((t-2.4)/0.22)
                dr.rounded_rectangle((57,1441,1023,1643),radius=34,fill=(4,9,17),outline=(255,219,115),width=3)
                text_center(im,"อาหารที่ปลูกเอง...",1483,70,(255,255,255),5)
                if t>=4.08:
                    text_center(im,"กลับถูกยึด!",1552,72,(255,213,75),5)
            text_center(im,"ข้อมูลขอบเขต: geoBoundaries / Natural Earth • ภาพพื้น: Esri World Imagery",1736,24,(205,215,226),1)
            dr.rounded_rectangle((42,1782,1038,1873),radius=12,fill=(2,7,14))
            text_center(im,"เส้นทางแสดงอำนาจรัฐโดยสังเขป • ไม่ใช่เส้นทางขนส่งยืนยัน",1803,27,(212,222,230),1)
            # Bottom brand is text-only because public repo must not contain private mascot.
            text_center(im,"เรื่องเล่าข้ามเวลา by AI  •  5s MOTION TEST",1871,26,(176,199,221),1)
            encoder.stdin.write(im.convert("RGB").tobytes())
            if frame%30==0:
                print("rendered",frame,"/",FPS*SECONDS,flush=True)
    finally:
        if encoder.stdin:encoder.stdin.close()
    if encoder.wait()!=0:raise RuntimeError("ffmpeg encoding failed")
    grab_movie_samples(filename)
    print("DONE",filename,filename.stat().st_size,"bytes",flush=True)

if __name__=="__main__":
    main()
