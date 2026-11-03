#!/usr/bin/env python3
"""Chen Sheng V8.2: moving map actors, speech-derived pop captions, 60 fps.

Separate release: the original V8 and its audit are never overwritten.
Historical locations are approximate, and map tiles use modern geography.
"""
from __future__ import annotations
import io, json, math, os, hashlib, re, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import render_full as old

ROOT = Path("chen_sheng_full")
OUT = ROOT / "v82"
AS = ROOT / "assets"
OUT.mkdir(parents=True, exist_ok=True)
W, H, FPS = 1080, 1920, 60
DURATION = 402.12
FONT_URL = old.FONT
TILE_URL = old.IMG
TILE_DIR = OUT / "tiles"
TILE_DIR.mkdir(exist_ok=True)
SCENES = old.SCENES
PLACES = old.PLACES
REBEL = {"daze", "qi", "zhi", "zan", "ku", "zhe", "qiao", "chen"}

def cmd(args):
    subprocess.check_call([str(x) for x in args])

def prepare():
    old.concat_parts("audio", "narration.aac")
    old.concat_parts("mascot", "mascot.webm")
    font = OUT / "Sarabun-Bold.ttf"
    if not font.exists():
        font.write_bytes(old.fetch(FONT_URL))
    return font

def cached_tile(z, x, y):
    if not (0 <= x < 2**z and 0 <= y < 2**z):
        return Image.new("RGB", (256,256), (13,28,36))
    p = TILE_DIR / f"{z}-{x}-{y}.jpg"
    if not p.exists():
        p.write_bytes(old.fetch(TILE_URL.format(z=z, x=x, y=y)))
    return Image.open(p).convert("RGB")

def merc(lon, lat, z):
    return old.merc(lon,lat,z)

def camera(dest, origin):
    lon, lat = PLACES[dest][1:]
    if origin:
        lon0,lat0=PLACES[origin][1:]
        lon,lat=(lon+lon0)/2,(lat+lat0)/2
    for z in range(8,4,-1):
        xd,yd=merc(*PLACES[dest][1:],z)
        if origin:
            xo,yo=merc(*PLACES[origin][1:],z)
            if abs(xd-xo)>W*.61 or abs(yd-yo)>H*.47:
                continue
        return lon,lat,z
    return lon,lat,5

def point(key, cam):
    lon,lat,z=cam
    cx,cy=merc(lon,lat,z)
    x,y=merc(*PLACES[key][1:],z)
    return (int(W/2+x-cx),int(H/2+y-cy))

def draw_label(d, xy, label, font, active=False):
    x,y=xy
    if not (-130<x<W+130 and -80<y<H+80):
        return
    col=(226,79,65,255) if active else (236,191,94,255)
    # 2D fortress with three crenellations; controlled-city color is event state.
    d.rectangle((x-21,y-13,x+21,y+16),fill=col,outline=(255,245,211),width=2)
    for dx in [-17,0,17]:
        d.rectangle((x+dx-6,y-25,x+dx+6,y-13),fill=col,outline=(255,245,211),width=1)
    d.rectangle((x-5,y+1,x+5,y+16),fill=(22,28,38))
    # text with compact stroke, no opaque rectangular plaque
    d.text((x,y-38),label,font=font,anchor="mb",fill=(255,245,213),
           stroke_width=3,stroke_fill=(6,16,27))

def scene_image(i, font_file):
    title,dest,origin,_=SCENES[i]
    cam=camera(dest,origin)
    lon,lat,z=cam
    cx,cy=merc(lon,lat,z)
    left,top=cx-W/2,cy-H/2
    x0,y0=math.floor(left/256),math.floor(top/256)
    x1,y1=math.ceil((left+W)/256),math.ceil((top+H)/256)
    atlas=Image.new("RGB",((x1-x0+1)*256,(y1-y0+1)*256),(15,30,39))
    for x in range(x0,x1+1):
        for y in range(y0,y1+1):
            atlas.paste(cached_tile(z,x,y),((x-x0)*256,(y-y0)*256))
    bg=atlas.crop((round(left-x0*256),round(top-y0*256),
                   round(left-x0*256)+W,round(top-y0*256)+H)).convert("RGBA")
    dark=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(dark)
    d.rectangle((0,0,W,224),fill=(3,17,30,195))
    d.rectangle((0,1770,W,H),fill=(3,17,30,115))
    d.line([(35,190),(1045,190)],fill=(242,193,90,190),width=3)
    bg=Image.alpha_composite(bg,dark)
    overlay=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(overlay)
    if origin:
        sx,sy=point(origin,cam)
        ex,ey=point(dest,cam)
        # Mildly bowed three-layer luminous directional route; not a false border.
        curve=[]
        for t in range(81):
            u=t/80
            x=sx+(ex-sx)*u-36*math.sin(math.pi*u)
            y=sy+(ey-sy)*u-22*math.sin(math.pi*u)
            curve.append((round(x),round(y)))
        for width,color in [(24,(20,217,250,45)),(10,(20,217,250,140)),(3,(222,252,255,255))]:
            d.line(curve,fill=color,width=width,joint="curve")
        # Directional arrowhead at destination.
        a=math.atan2(ey-sy,ex-sx)
        q=(ex-24*math.cos(a),ey-24*math.sin(a))
        tri=[(ex,ey),(q[0]+13*math.sin(a),q[1]-13*math.cos(a)),
             (q[0]-13*math.sin(a),q[1]+13*math.cos(a))]
        d.polygon(tri,fill=(223,249,255,255))
    labels={dest}
    if origin:labels.add(origin)
    # Nearby captured/campaign nodes, max two additional, to preserve readability.
    nearby=sorted([(math.dist(point(k,cam),point(dest,cam)),k)
                   for k in PLACES if k not in labels and 100<point(k,cam)[1]<1600])
    labels.update(k for _,k in nearby[:2])
    fcity=ImageFont.truetype(str(font_file),29)
    for key in labels:
        captured=key in REBEL and (i>=next((j for j,s in enumerate(SCENES) if s[1]==key),999))
        draw_label(d,point(key,cam),PLACES[key][0],fcity,captured)
    bg=Image.alpha_composite(bg,overlay)
    d=ImageDraw.Draw(bg)
    ft=ImageFont.truetype(str(font_file),49 if len(title)<22 else 41)
    d.text((W//2,94),title,font=ft,anchor="mm",fill=(255,232,168),
           stroke_width=3,stroke_fill=(3,13,25))
    fm=ImageFont.truetype(str(font_file),23)
    d.text((42,154),f"แผนที่อ้างอิงภูมิศาสตร์ปัจจุบัน · จุดเมืองโดยประมาณ",font=fm,
           fill=(225,237,246))
    logo=Image.open(AS/"logo.png").convert("RGBA")
    logo.thumbnail((105,105))
    bg.alpha_composite(logo,(W-logo.width-35,244))
    return bg.convert("RGB"),point(origin or dest,cam),point(dest,cam)

def troop_sprite(path, color, font_file):
    im=Image.new("RGBA",(152,107),(0,0,0,0))
    d=ImageDraw.Draw(im)
    dark=(16,30,41,255)
    # Three small overhead military units, distinguishable at phone size.
    for x,y in [(33,57),(76,57),(119,57)]:
        d.ellipse((x-14,y-14,x+14,y+14),fill=color,outline=(255,239,207),width=3)
        d.polygon([(x,y-21),(x-11,y-5),(x+11,y-5)],fill=(39,54,63),outline=(255,239,207))
        d.line((x,y+14,x,y+24),fill=(255,238,202),width=3)
    d.line((76,34,76,5),fill=(255,239,207),width=4)
    d.polygon([(78,5),(128,12),(78,25)],fill=color,outline=(255,240,212))
    im.save(path)

def ass_time(sec):
    h=int(sec//3600);m=int(sec%3600//60);s=sec%60
    return f"{h}:{m:02}:{s:05.2f}"

def ass_escape(t):
    return t.replace("\\","").replace("{","").replace("}","").replace("\n"," ")

def captions(asr):
    data=json.loads(Path(asr).read_text(encoding="utf-8"))
    words=data.get("words",[])
    if not words:
        words=[{"start":s["start"],"end":s["end"],"text":s["text"]}
               for s in data.get("segments",[])]
    # Spoken-word timeline from ASR. Preserve real pauses; split into short pop units.
    units=[];chunk=[];start=0;end=0
    for w in words:
        t=str(w.get("text","")).strip()
        if not t:continue
        a=float(w["start"]);b=float(w["end"])
        if chunk and (b-start>2.4 or len("".join(chunk))+len(t)>28 or a-end>0.6):
            units.append((start,end," ".join(chunk)))
            chunk=[]
        if not chunk:start=a
        end=b;chunk.append(t)
    if chunk:units.append((start,end," ".join(chunk)))
    # ASS karaoke-style short pop; white with heavy black outline, gold emphasis.
    hdr=("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
         "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
         "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour,"
         "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY,"
         "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR,"
         "MarginV, Encoding\n"
         "Style: Pop,Sarabun,51,&H00FFFFFF,&H0000CCFF,&H00000000,&H00000000,"
         "-1,0,0,0,100,100,0,0,1,5,1,2,74,74,360,1\n\n"
         "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR,"
         "MarginV, Effect, Text\n")
    lines=[hdr]
    for a,b,t in units:
        if b<=a:continue
        t=ass_escape(t)
        # Initial scale settles in 0.16 sec; no black panel behind subtitles.
        effect=r"{\fscx113\fscy113\t(0,160,\fscx100\fscy100)}"
        for key in ("เฉินเซิ่ง","จิ๋นซีฮ่องเต้","จักรวรรดิฉิน","อู๋กว่าง","จางหาน"):
            t=t.replace(key, r"{\c&H007DEBFF&}"+key+r"{\c&H00FFFFFF&}")
        lines.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Pop,,0,0,0,,{effect}{t}\n")
    p=OUT/"captions.ass";p.write_text("".join(lines),encoding="utf-8")
    return len(units)

def render_scene(i,duration,font_file):
    bg,p0,p1=scene_image(i,font_file)
    bg_path=OUT/f"bg_{i:02}.jpg";bg.save(bg_path,quality=94,subsampling=0)
    title,dest,origin,_=SCENES[i]
    enemy= i in {20,21,22,23,26,27,28}
    sprite=OUT/("army_qin.png" if enemy else "army_rebel.png")
    if origin:
        # Distribute movement across ~80% of segment, then settle at destination.
        xexpr=f"{p0[0]-76}+({p1[0]-p0[0]})*min(t/{max(1,duration*.8):.3f},1)"
        yexpr=f"{p0[1]-52}+({p1[1]-p0[1]})*min(t/{max(1,duration*.8):.3f},1)"
    else:
        xexpr=f"{p1[0]-76}+7*sin(t*2)"
        yexpr=f"{p1[1]-52}+6*cos(t*2)"
    segment=OUT/f"seg_{i:02}.mp4"
    if segment.exists() and segment.stat().st_size>100000:
        return segment
    filterstr=f"[0:v][1:v]overlay=x='{xexpr}':y='{yexpr}':eval=frame:shortest=1,format=yuv420p[v]"
    cmd(["ffmpeg","-y","-loglevel","error","-loop","1","-framerate",FPS,
         "-i",bg_path,"-loop","1","-framerate",FPS,"-i",sprite,
         "-filter_complex",filterstr,"-map","[v]","-t",f"{duration:.3f}",
         "-r",FPS,"-an","-c:v","libx264","-preset","veryfast",
         "-crf","17","-pix_fmt","yuv420p",segment])
    return segment

def probe(path):
    return json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames",
        "-show_streams","-show_format","-of","json",str(path)]))

def main():
    font_file=prepare()
    troop_sprite(OUT/"army_rebel.png",(211,59,58,255),font_file)
    troop_sprite(OUT/"army_qin.png",(223,173,72,255),font_file)
    timing=Path(os.environ.get("TIMING_JSON","chen_sheng_full/timing/asr_segments.json"))
    if not timing.exists():
        raise FileNotFoundError("Real narration ASR timestamps required: "+str(timing))
    cap_count=captions(timing)
    mode=os.environ.get("MODE","preview")
    if mode=="preview":
        indices=[15] # show moving Wu Guang attack toward Xingyang
        durations=[12.0]
        total=12.0
    else:
        indices=list(range(len(SCENES)))
        scale=DURATION/sum(s[3] for s in SCENES)
        durations=[s[3]*scale for s in SCENES]
        total=DURATION
    clips=[render_scene(i,d,font_file) for i,d in zip(indices,durations)]
    concat=OUT/f"{mode}.ffconcat"
    concat.write_text("ffconcat version 1.0\n"+
                      "".join(f"file '{p.name}'\n" for p in clips),encoding="utf-8")
    video=OUT/(f"ChenSheng_V82_{'12s_PREVIEW' if mode=='preview' else 'FULL_60FPS'}.mp4")
    # Retain the original animated keyed mascot; subtitles are above it.
    ass=(OUT/"captions.ass").as_posix()
    args=["ffmpeg","-y","-loglevel","error","-safe","0","-f","concat",
          "-i",concat,"-i",old.AUDIO,"-stream_loop","-1","-c:v","libvpx-vp9",
          "-i",old.MASCOT,"-filter_complex",
          f"[0:v]ass=filename={ass}:fontsdir={OUT.as_posix()}[sub];"
          "[2:v]scale=180:-1,format=rgba[mas];"
          "[sub][mas]overlay=W-w-20:H-h-18:shortest=0,format=yuv420p[v]",
          "-map","[v]","-map","1:a:0","-c:v","libx264","-preset","veryfast",
          "-crf","16","-c:a","aac","-b:a","128k","-r",FPS,"-t",str(total),
          "-movflags","+faststart",video]
    if mode=="preview":
        # Preview audio is not the selected scene; use original opening narration
        # and flag timing as non-representative, to test motion/typography only.
        pass
    cmd(args)
    q=probe(video)
    v=next(s for s in q["streams"] if s["codec_type"]=="video")
    a=next(s for s in q["streams"] if s["codec_type"]=="audio")
    assert (v["width"],v["height"])==(W,H)
    assert abs(float(v["avg_frame_rate"].split("/")[0])/float(v["avg_frame_rate"].split("/")[1])-FPS)<.01
    assert abs(float(q["format"]["duration"])-total)<.4
    cmd(["ffmpeg","-v","error","-i",video,"-f","null","-"])
    thumbs=[]
    for t in ([2,6,10] if mode=="preview" else [2,60,180,300,398]):
        p=OUT/f"{mode}_t{t:03}.jpg"
        cmd(["ffmpeg","-y","-v","error","-ss",str(t),"-i",video,"-frames:v","1",p])
        thumbs.append(str(p))
    qa={"status":"TECHNICAL_PASS_EDITORIAL_REVIEW_REQUIRED",
        "mode":mode,"duration":total,"fps":FPS,"resolution":"1080x1920",
        "video":str(video),"sha256":hashlib.sha256(video.read_bytes()).hexdigest(),
        "asr_pop_caption_units":cap_count,"spoken_caption_status":"ASR DRAFT — requires verification against locked Thai script",
        "motion":"60fps moving 2D troop sprites over real Web Mercator imagery",
        "historic_geography":"Approximate place proxies on modern basemap, not Qin borders",
        "limitations":["Visual events use editorial timing estimates rather than final forced alignment",
                       "Prototype shows Xingyang movement with opening audio for motion QA"],
        "frames":thumbs}
    (OUT/f"qa_{mode}.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(qa,ensure_ascii=False),flush=True)
if __name__=="__main__":
    main()
