#!/usr/bin/env python3
"""Five-second V8 real-map technical test: schematic India -> Kra crossing."""
import concurrent.futures
import hashlib
import io
import json
import math
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, SECONDS = 1080, 1920, 30, 5
Z, TILE, WORLD = 7, 256, 256 * (2 ** 7)
# Keep a full 3x map canvas so camera zooms do not enlarge a 1080p raster.
UPSCALE = 3
BW, BH = W * UPSCALE, H * UPSCALE
OUT = Path("kra/output")
OUT.mkdir(parents=True, exist_ok=True)
TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
GEO_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/sarabun/Sarabun-Bold.ttf"
BBOX = (77.0, -16.0, 106.0, 36.0)  # lon_min, lat_min, lon_max, lat_max
CHENNAI = (80.28, 13.08)  # modern geographic anchors, NOT ancient-port claims
RANONG = (98.59, 9.96)
CHUMPHON = (99.17, 10.49)
# Diagrammatic open-water route, not evidence for a literal historical itinerary.
SEA = [CHENNAI, (84.0, 11.8), (89.2, 10.4), (94.0, 9.3), RANONG]
LAND = [RANONG, (98.83, 10.12), CHUMPHON]
SITE_X, SITE_Y = (98.86, 10.22)

def fetch(url):
    last = None
    for n in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "History-Map-V8-GitHub-5s/1.0"})
            with urllib.request.urlopen(req, timeout=55) as response:
                data = response.read()
            if len(data) < 100:
                raise RuntimeError("Unexpectedly short download")
            return data
        except Exception as exc:
            last = exc
            time.sleep(1.4 * (n + 1))
    raise RuntimeError(f"Download failed: {url} / {last}")

def merc(lon, lat):
    latitude = math.radians(max(-85, min(85, lat)))
    return (WORLD * (lon + 180) / 360,
            WORLD * (1 - math.asinh(math.tan(latitude)) / math.pi) / 2)

def camera_setup():
    lo, bottom, hi, top = BBOX
    xa, ya = merc(lo, top)
    xb, yb = merc(hi, bottom)
    midpoint = ((xa + xb) / 2, (ya + yb) / 2)
    scale = max(W / (xb - xa), H / (yb - ya))
    return midpoint, scale

MID, BASE_SCALE = camera_setup()

def base_xy(lon, lat):
    x, y = merc(lon, lat)
    return ((x - MID[0]) * BASE_SCALE + W / 2,
            (y - MID[1]) * BASE_SCALE + H / 2)

def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)

def camera(t):
    alpha = ease((t - 3.05) / 1.16)
    focus = base_xy(* (SITE_X, SITE_Y))
    return ((W / 2 + (focus[0] - W / 2) * alpha,
             H / 2 + (focus[1] - H / 2) * alpha),
            1.0 + 1.42 * alpha)

def to_screen(point, cam_center, zoom):
    x, y = base_xy(*point)
    return ((x - cam_center[0]) * zoom + W / 2,
            (y - cam_center[1]) * zoom + H / 2)

def mosaic():
    # Real, geographically registered satellite imagery — never hand-drawn polygons.
    left, top = merc(BBOX[0], BBOX[3])
    right, bottom = merc(BBOX[2], BBOX[1])
    x0 = max(0, math.floor(left / TILE) - 1)
    x1 = min(2 ** Z, math.ceil(right / TILE) + 1)
    y0 = max(0, math.floor(top / TILE) - 1)
    y1 = min(2 ** Z, math.ceil(bottom / TILE) + 1)
    jobs = [(x, y) for y in range(y0, y1) for x in range(x0, x1)]
    print("Downloading satellite tiles:", len(jobs), flush=True)
    sheet = Image.new("RGB", ((x1 - x0) * TILE, (y1 - y0) * TILE))
    def one(pair):
        x, y = pair
        image = Image.open(io.BytesIO(fetch(TILE_URL.format(z=Z, y=y, x=x)))).convert("RGB")
        if image.size != (TILE, TILE):
            raise RuntimeError("Invalid tile " + str(pair))
        return (x, y, image)
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        for x, y, image in pool.map(one, jobs):
            sheet.paste(image, ((x - x0) * TILE, (y - y0) * TILE))
    centre_source = (MID[0] - x0 * TILE, MID[1] - y0 * TILE)
    high_scale = BASE_SCALE * UPSCALE
    affine = (1 / high_scale, 0, centre_source[0] - BW / 2 / high_scale,
              0, 1 / high_scale, centre_source[1] - BH / 2 / high_scale)
    # Base is 3240x5760: zooming into the Kra peninsula preserves source detail.
    return sheet.transform((BW, BH), Image.Transform.AFFINE, affine, resample=Image.Resampling.BICUBIC)

def polygons(geometry):
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    if geometry["type"] == "MultiPolygon":
        return [ring for poly in geometry["coordinates"] for ring in poly]
    return []

def borders():
    geo = json.loads(fetch(GEO_URL))
    outline = Image.new("L", (BW, BH), 0)
    tint = Image.new("L", (BW, BH), 0)
    d1 = ImageDraw.Draw(outline)
    d2 = ImageDraw.Draw(tint)
    wanted = {"India", "Myanmar", "Thailand", "Malaysia", "Bangladesh",
              "Sri Lanka", "Indonesia", "Cambodia", "Laos", "Vietnam"}
    n = 0
    for feature in geo.get("features", []):
        props = feature.get("properties", {})
        name = props.get("ADMIN", props.get("NAME", ""))
        if name not in wanted:
            continue
        for ring in polygons(feature.get("geometry") or {}):
            if len(ring) < 3:
                continue
            coords = [(x * UPSCALE, y * UPSCALE) for x, y in
                      (base_xy(lon, lat) for lon, lat in ring)]
            if max(v[0] for v in coords) < -30 * UPSCALE or min(v[0] for v in coords) > BW + 30 * UPSCALE:
                continue
            if max(v[1] for v in coords) < -30 * UPSCALE or min(v[1] for v in coords) > BH + 30 * UPSCALE:
                continue
            d2.polygon(coords, fill=58)
            d1.line(coords + [coords[0]], fill=240, width=2 * UPSCALE, joint="curve")
            n += 1
    if n < 3:
        raise RuntimeError("Natural Earth polygons not parsed correctly")
    return outline, tint, n

def backdrop(real_map, borders_mask, country_tint):
    """Three independent cyan/white Jedi-glow layers over REAL satellite terrain."""
    img = real_map.convert("RGB")
    territory = Image.new("RGB", (BW, BH), (37, 133, 119))
    img.paste(territory, (0, 0), country_tint.point(lambda x: int(x * 0.60)))
    # Far-field bloom, concentrated neon and hairline white-cyan core.
    far = borders_mask.filter(ImageFilter.GaussianBlur(12 * UPSCALE))
    near = borders_mask.filter(ImageFilter.GaussianBlur(3 * UPSCALE))
    far_color = Image.new("RGB", (BW, BH), (10, 225, 251))
    near_color = Image.new("RGB", (BW, BH), (33, 249, 255))
    core_color = Image.new("RGB", (BW, BH), (224, 255, 239))
    img.paste(far_color, (0, 0), far.point(lambda x: int(x * 0.92)))
    img.paste(near_color, (0, 0), near.point(lambda x: int(x * 0.89)))
    img.paste(core_color, (0, 0), borders_mask)
    return img

def catmull(points, steps=26):
    result = []
    for i in range(len(points) - 1):
        p0 = points[max(0, i - 1)]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[min(len(points) - 1, i + 2)]
        for k in range(steps):
            t = k / steps
            def c(j):
                return 0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t
                        + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                        + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t * t * t)
            result.append((c(0), c(1)))
    result.append(points[-1])
    return result

SEA_PTS = catmull(SEA)
LAND_PTS = catmull(LAND)

def route(img, path, percentage, center, zoom, rgb):
    if percentage <= 0:
        return
    count = max(1, int((len(path) - 1) * min(1, percentage)))
    coords = [to_screen(p, center, zoom) for p in path[:count + 1]]
    gray = Image.new("L", (W, H), 0)
    ImageDraw.Draw(gray).line(coords, fill=255, width=7, joint="curve")
    far = gray.filter(ImageFilter.GaussianBlur(19))
    near = gray.filter(ImageFilter.GaussianBlur(5))
    img.paste(rgb, (0, 0), far.point(lambda x: int(x * 0.96)))
    img.paste(rgb, (0, 0), near.point(lambda x: int(x * 0.94)))
    crisp = Image.new("L", (W, H), 0)
    ImageDraw.Draw(crisp).line(coords, fill=255, width=5, joint="curve")
    img.paste((241, 255, 254) if rgb[2] > rgb[0] else (255, 235, 151), (0, 0), crisp)
    if len(coords) >= 4:
        x, y = coords[-1]
        px, py = coords[-4]
        angle = math.atan2(y - py, x - px)
        tri = [(x + 16 * math.cos(angle), y + 16 * math.sin(angle)),
               (x + 13 * math.cos(angle + 2.5), y + 13 * math.sin(angle + 2.5)),
               (x + 13 * math.cos(angle - 2.5), y + 13 * math.sin(angle - 2.5))]
        ImageDraw.Draw(img).polygon(tri, fill=(255, 255, 239))

def point(img, ll, center, zoom, rgb, size=9):
    x, y = to_screen(ll, center, zoom)
    if x < -20 or x > W + 20 or y < -20 or y > H + 20:
        return
    d = ImageDraw.Draw(img)
    d.ellipse((x - size * 2.7, y - size * 2.7, x + size * 2.7, y + size * 2.7),
              fill=(*rgb,)) 
    d.ellipse((x - size, y - size, x + size, y + size), fill=(246, 255, 254),
              outline=rgb, width=4)

def text(draw, text, x, y, size, font_file, fill=(255,255,255), anchor="mm", stroke=4):
    f = ImageFont.truetype(str(font_file), size, layout_engine=ImageFont.Layout.RAQM)
    draw.text((int(x), int(y)), text, font=f, fill=fill, anchor=anchor,
              stroke_width=stroke, stroke_fill=(4, 14, 23))

def frame(base, font_file, t):
    center, zoom = camera(t)
    crop = ((center[0] - W / (2 * zoom)) * UPSCALE,
            (center[1] - H / (2 * zoom)) * UPSCALE,
            (center[0] + W / (2 * zoom)) * UPSCALE,
            (center[1] + H / (2 * zoom)) * UPSCALE)
    img = base.crop(crop).resize((W, H), Image.Resampling.LANCZOS).convert("RGB")
    sea_p = ease((t - 0.47) / 2.67)
    land_p = ease((t - 3.54) / 1.02)
    route(img, SEA_PTS, sea_p, center, zoom, (38, 226, 251))
    route(img, LAND_PTS, land_p, center, zoom, (255, 185, 64))
    point(img, CHENNAI, center, zoom, (34, 223, 243))
    point(img, RANONG, center, zoom, (34, 223, 243))
    if land_p > 0:
        point(img, CHUMPHON, center, zoom, (255, 198, 83))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((23, 30, W - 23, 229), radius=25, fill=(4, 21, 35),
                        outline=(50, 179, 195), width=3)
    text(d, "HISTORY MAP · V8", 57, 68, 27, font_file, fill=(99, 231, 239), anchor="lm", stroke=2)
    text(d, "ทางลัดการค้าโบราณ", 54, 123, 61, font_file, anchor="lm", stroke=3)
    text(d, "อินเดีย → คาบสมุทร → อ่าวไทย", 55, 185, 40, font_file,
         fill=(255, 218, 126), anchor="lm", stroke=3)
    if zoom < 1.25:
        for label, coord in [("อินเดีย", (82.8,19.0)), ("อ่าวเบงกอล", (89.3,17.0)),
                             ("พม่า", (95.1,21.5)), ("ไทย", (101.2,18.0))]:
            x,y = to_screen(coord,center,zoom)
            if 250 < y < 1460 and 50 < x < 1030:
                text(d,label,x,y,40,font_file,anchor="mm")
    else:
        for label,coord,shift in [("ฝั่งอันดามัน",RANONG,(-92,-85)),
                                  ("ฝั่งอ่าวไทย",CHUMPHON,(90,-75))]:
            x,y=to_screen(coord,center,zoom)
            if 120<x<W-120 and 275<y<H-300:
                text(d,label,x+shift[0],y+shift[1],31,font_file,
                     fill=(255,221,144),anchor="mm",stroke=3)
    d.rounded_rectangle((28, H - 313, W - 28, H - 145), radius=29,
                        fill=(4, 17, 31), outline=(32, 145, 162),width=2)
    caption = "ข้ามอ่าวเบงกอล สู่ชายฝั่งอันดามัน" if t < 3.38 else "ขนสินค้าข้ามคาบสมุทร สู่อ่าวไทย!"
    text(d,caption,W//2,H-224,46,font_file,anchor="mm")
    text(d,"แผนที่ภูมิประเทศจริง · แนวเดินทางสันนิษฐาน",W//2,H-88,27,
         font_file,fill=(172,211,219),anchor="mm",stroke=2)
    d.rectangle((0,H-7,int(W*(t/SECONDS)),H),fill=(55,226,246))
    return img

def verify(mp4):
    subprocess.check_call(["ffmpeg","-v","error","-i",str(mp4),"-f","null","-"])
    obj=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames",
        "-show_streams","-show_format","-of","json",str(mp4)]))
    video=next(s for s in obj["streams"] if s["codec_type"]=="video")
    assert (video["width"],video["height"])==(W,H)
    assert int(video["nb_read_frames"])==FPS*SECONDS
    assert abs(float(obj["format"]["duration"])-SECONDS)<0.06
    assert not any(s["codec_type"]=="audio" for s in obj["streams"])
    report={"result":"file/decode QA PASS","seconds":SECONDS,"frames":FPS*SECONDS,
        "resolution":[W,H],"audio":"NONE (silent technical preview)",
        "geography":"Esri World Imagery tiles z7 + Natural Earth GeoJSON",
        "sharpness":"3x source canvas; LANCZOS final sampling; H.264 CRF16",
        "jedi_border":"three layers: 12x/3x radius cyan blooms + sharp pale core",
        "routes":"illustrative interpretation, not ancient GPS",
        "branding":"original licensed logo/mascot not supplied in this repository",
        "human_viewing":"not yet independently confirmed",
        "video_sha256":hashlib.sha256(mp4.read_bytes()).hexdigest()}
    (OUT/"qa.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)

def main():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe required")
    font_file=OUT/"Sarabun-Bold.ttf"
    font_file.write_bytes(fetch(FONT_URL))
    background=mosaic()
    boundary,tint,n=borders()
    print("Natural Earth outline polygons:",n,flush=True)
    base=backdrop(background,boundary,tint)
    mp4=OUT/"V8_India_Kra_5sec_SILENT.mp4"
    cmd=["ffmpeg","-y","-hide_banner","-loglevel","error",
         "-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}",
         "-framerate",str(FPS),"-i","pipe:0",
         "-an","-c:v","libx264","-pix_fmt","yuv420p",
         "-preset","medium","-crf","16","-movflags","+faststart",str(mp4)]
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    sample=[]
    try:
        for index in range(SECONDS*FPS):
            image=frame(base,font_file,index/FPS)
            process.stdin.write(image.tobytes())
            if index in (15,75,135):
                sample.append(image.resize((270,480)))
            if index%30==0:
                print("encoded frames supplied:",index,flush=True)
    finally:
        process.stdin.close()
    if process.wait()!=0:
        raise RuntimeError("FFmpeg encoding failed")
    sheet=Image.new("RGB",(810,480),(0,0,0))
    for i,img in enumerate(sample):
        sheet.paste(img,(i*270,0))
    sheet.save(OUT/"contact_sheet.jpg",quality=92)
    verify(mp4)

if __name__=="__main__":
    main()
