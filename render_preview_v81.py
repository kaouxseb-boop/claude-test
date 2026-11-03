#!/usr/bin/env python3
"""Map Story V8.1: 5-second SILENT full-map motion proof with generated historical illustration."""
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
TILE_Z=6
TILE_SIZE=256
TILE_X0,TILE_X1=31,43
TILE_Y0,TILE_Y1=14,29
WORLD=256*(2**TILE_Z)
OUT=Path("dist")
OUT.mkdir(parents=True,exist_ok=True)
UA_URL="https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/UKR/ADM0/geoBoundaries-UKR-ADM0.geojson"
NE_URL="https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
FONT_URL="https://raw.githubusercontent.com/google/fonts/main/ofl/sarabun/Sarabun-Bold.ttf"
FLAG_URL="https://commons.wikimedia.org/wiki/Special:Redirect/file/Flag_of_the_Soviet_Union_(1924).svg"
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
    # Hold meaningful map compositions: whole Ukraine -> Moscow order -> village.
    def blend(a,b,p): return a+(b-a)*ease(p)
    if t < 1.30:
        p=ease((t-0.75)/0.55)
        lon,lat,zoom=blend(32.3,33.8,p),blend(50.0,51.1,p),blend(0.93,1.03,p)
    elif t < 2.72:
        lon,lat,zoom=33.8,51.1,1.03
    else:
        p=ease((t-2.72)/1.05)
        lon,lat,zoom=blend(33.8,31.65,p),blend(51.1,49.15,p),blend(1.03,1.50,p)
    return merc(lon,lat),zoom


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

def geo_flag_layer(base,ua_mask,center,zoom,flag,opacity):
    # Flag is geographically fixed as camera moves: no swimming/warping to the visible bbox.
    # This USSR flag is an illustrative period overlay for the Ukrainian SSR in 1932.
    if opacity<=0:return
    nw=screen(merc(21.0,53.1),center,zoom)
    se=screen(merc(41.2,43.25),center,zoom)
    x0,y0=int(nw[0]),int(nw[1]);x1,y1=int(se[0]),int(se[1])
    if x1<=x0 or y1<=y0:return
    flag_canvas=flag.resize((x1-x0,y1-y0),Image.Resampling.BICUBIC).convert("RGB")
    layer=Image.new("RGB",(W,H),(0,0,0))
    layer.paste(flag_canvas,(x0,y0))
    base.paste(layer,(0,0),ua_mask.point(lambda q:int(q*opacity)))
 
def add_farm_asset(base,asset,center,zoom,t,anchor=(30.85,49.05)):
    if t<2.92:return
    p=ease((t-2.92)/0.48)
    x,y=screen(merc(*anchor),center,zoom)
    size=int(490*(0.84+0.16*p))
    im=asset.copy()
    # The generated sprite contains soft edge shadow; fade to transparency at the corners.
    im.thumbnail((size,size),Image.Resampling.LANCZOS)
    ww,hh=im.size
    # Keep the lower point of the illustration near the true map anchor via leader line.
    pos=(int(x-ww/2),int(y-hh*0.76))
    alpha=im.getchannel("A")
    if alpha.getextrema()[0]>=250:
        # Generated art may have opaque vignette; feather the perimeter to avoid a photo rectangle.
        edge=Image.new("L",im.size,0)
        e=ImageDraw.Draw(edge)
        e.ellipse((int(ww*.03),int(hh*.03),int(ww*.97),int(hh*.96)),fill=255)
        edge=edge.filter(ImageFilter.GaussianBlur(42))
        alpha=ImageChops.multiply(alpha,edge)
    alpha=alpha.point(lambda q:int(q*p))
    im.putalpha(alpha)
    base.paste(im,pos,im)
    dr=ImageDraw.Draw(base)
    foot=(pos[0]+ww//2,pos[1]+int(hh*.78))
    dr.line((foot,(int(x),int(y))),fill=(255,226,147),width=3)
    dr.ellipse((x-7,y-7,x+7,y+7),fill=(255,224,132),outline=(10,22,31),width=2)

def mini_caption(base,t,show,words,highlight=None):
    if show<0:return
    p=ease(show)
    y=int(1530+24*(1-p)-10*math.sin(math.pi*min(1,show)*1.2)*p)
    dr=ImageDraw.Draw(base)
    # No giant PowerPoint panel: just a clean 1-line subtitle with stroke.
    text_center(base,words,y,62,(255,233,174) if highlight else (255,255,255),6)

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
        "geography":"Present-day geoBoundaries UKR ADM0 incl Crimea is a reference frame, NOT exact Ukrainian SSR administrative borders in 1932; Natural Earth other shapes",
        "imagery":"Esri World Imagery tile server, geographically projected",
        "paths":"Moscow policy arrow is conceptual order direction; not wheat shipping route or a verified travel path",
        "status":"encoded file/decode QA only; generated farm is interpretive; not a voice-aligned final"},ensure_ascii=False,indent=2),encoding="utf8")

def main():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg tools absent")
    global FONT_PATH
    FONT_PATH=OUT/"Sarabun-Bold.ttf"
    FONT_PATH.write_bytes(fetch(FONT_URL))
    print("Map source: geoBoundaries Ukraine and Natural Earth",flush=True)
    ua_bytes=fetch(UA_URL)
    print('Ukraine geometry bytes:',len(ua_bytes),'signature:',repr(ua_bytes[:12]),flush=True)
    uk_data=json.loads(ua_bytes)
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
        import cairosvg
        flag_svg=fetch(FLAG_URL)
        print('Flag source signature:',repr(flag_svg[:60]),flush=True)
        FLAG=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=flag_svg,output_width=1200,output_height=600))).convert("RGBA")
        print("Loaded historical Soviet flag artwork",flush=True)
    except Exception as error:
        raise RuntimeError("Cannot verify Soviet flag source; refusing to substitute an incorrect emblem") from error
    mosaic=satellite_mosaic()
    filename=OUT/"Holodomor_V81_5sec_SILENT_preview.mp4"
    encoder=subprocess.Popen(["ffmpeg","-y","-hide_banner","-loglevel","error","-f","rawvideo",
        "-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
        "-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(filename)],stdin=subprocess.PIPE)
    moscow=(37.6173,55.7558)
    policy_dest=(32.9,49.83)
    farm_asset=Image.open("assets/v81_ukrainian_farm.png").convert("RGBA")
    print("Generated farm sprite",farm_asset.size,"alpha",farm_asset.getchannel("A").getextrema(),flush=True)
    try:
        for frame in range(FPS*SECONDS):
            t=frame/FPS
            cent,zoom=camera(t)
            im=sat_frame(mosaic,cent,zoom)
            # Keep satellite texture visible, no flat slide background.
            im.paste((3,8,16),(0,0),Image.new("L",(W,H),81))
            ru_mask=drawmask(ru_rings,cent,zoom)
            tinted(im,ru_mask,(86,76,86),46)
            ua_mask=drawmask(ua_rings,cent,zoom)
            # Geography-fixed historical Soviet flag: full Ukrainian silhouette, then fades
            # back to legible terrain as confiscation starts.
            flag_fade=0.63*(1.0-ease((t-1.05)/1.97))
            # Reveal warm transparent thematic shading without altering satellite terrain.
            tinted(im,ua_mask,(37,109,143),int(78*ease((t-1.40)/1.3)))
            geo_flag_layer(im,ua_mask,cent,zoom,FLAG,flag_fade)
            outline(im,ru_rings,cent,zoom,(158,138,150),3,10)
            outline(im,ua_rings,cent,zoom,(115,243,255),5,14)
            # Accurate geographic pins in all camera stages.
            draw_pin(im,moscow,cent,zoom,(255,190,83),10)
            mx,my=screen(merc(*moscow),cent,zoom)
            if -180<mx<W+100 and -150<my<H:
                label(im,"มอสโก",mx-75,my+33,41)
            ux,uy=screen(merc(35.4,48.1),cent,zoom)
            if 100<ux<W-100 and 100<uy<H-130:
                label(im,"ยูเครน",ux,uy,49)
            # Moscow -> Ukrainian SSR represents POLICY ORDERS, not physical grain shipping.
            if 1.24<=t<=3.3:
                q=ease((t-1.24)/1.36)
                draw_route(im,moscow,policy_dest,cent,zoom,q,0)
                if t>1.79 and t<3.13:
                    px,py=screen(merc(35.95,52.43),cent,zoom)
                    if 100<px<W-150 and 250<py<H-200:
                        label(im,"คำสั่งโควตา",px,py-88,35)
            # A single generated period-illustration appears at the local confiscation beat.
            add_farm_asset(im,farm_asset,cent,zoom,t)
            # Bare headline integrated into map, not framed as a presentation slide.
            text_center(im,"โฮโลโดมอร์",82,83,(255,237,180),5)
            text_center(im,"ยูเครน • ค.ศ. 1932–1933",188,38,(236,241,244),3)
            if 1.45<t<2.86:
                mini_caption(im,t,ease((t-1.45)/0.21),"มอสโกสั่งเก็บธัญพืช",True)
            if t>=3.12:
                mini_caption(im,t,ease((t-3.12)/0.22),"ชาวนาถูกยึดเสบียง!",True)
            # Plain small evidence key, not a full-width card.
            dr=ImageDraw.Draw(im)
            dr.text((43,1801),"ฐานแผนที่: พรมแดนปัจจุบัน • ภาพชาวนาเป็นภาพจำลอง",font=font(25),
                    fill=(226,229,225),stroke_width=2,stroke_fill=(9,13,16))
            dr.text((43,1852),"ลูกศรคือทิศทางคำสั่ง ไม่ใช่เส้นทางขนข้าว",font=font(25),
                    fill=(216,223,225),stroke_width=2,stroke_fill=(9,13,16))
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
