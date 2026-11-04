import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "assets"
GEN = Path("/workspace/scratch/87e2757ddd0b/generated_images")

ATLASES = [
    (
        GEN / "exec-fdfcc49b-9bf6-4223-88bc-aea356377738.png",
        ["rainstorm", "conscript", "oath", "qin_decree", "forced_labor", "rebel_rise"],
    ),
    (
        GEN / "exec-815895bc-bc4b-4ae1-8e5f-cfad2a96568a.png",
        ["siege", "clash", "qin_wins", "rebels_win", "captured_gate", "coronation"],
    ),
    (
        GEN / "exec-3385bee0-c88a-4256-b189-4490bb82c10c.png",
        ["chariot", "betrayal", "uprising_spread", "xiang_yu", "liu_bang", "qin_fall"],
    ),
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crop_cell(atlas: Image.Image, col: int, row: int) -> Image.Image:
    cell = atlas.crop((col * 512, row * 512, (col + 1) * 512, (row + 1) * 512))
    # Atlas subjects occasionally bleed a few pixels into the neighboring cell.
    # Clear only the shared gutters before trimming so every exported sprite is isolated.
    alpha = cell.getchannel("A")
    alpha.paste(0, (0, 0, 24, 512))
    alpha.paste(0, (488, 0, 512, 512))
    cell.putalpha(alpha)
    alpha = cell.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        raise RuntimeError((col, row, "empty alpha"))
    cell = cell.crop(bbox)
    padded = Image.new("RGBA", (cell.width + 32, cell.height + 32))
    padded.alpha_composite(cell, (16, 16))
    return padded


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"edition": "Chen Sheng V8.4", "generated": [], "reused": []}
    for source, names in ATLASES:
        atlas = Image.open(source).convert("RGBA")
        if atlas.size != (1536, 1024):
            raise RuntimeError((source, atlas.size))
        shutil.copy2(source, OUT / ("atlas_" + source.name))
        for index, name in enumerate(names):
            image = crop_cell(atlas, index % 3, index // 3)
            target = OUT / f"{name}.png"
            image.save(target)
            manifest["generated"].append(
                {
                    "id": name,
                    "file": target.name,
                    "source_atlas": source.name,
                    "cell": index,
                    "sha256": digest(target),
                    "alpha": image.getchannel("A").getextrema(),
                }
            )
    for name in ["rebels.png", "qin.png", "town.png", "gate.png", "chen.png", "zhang.png", "mascot.webm", "NotoSansThaiFull.ttf", "NotoSansThai-OFL.txt"]:
        source = ROOT / "v83" / "assets" / name
        target = OUT / name
        shutil.copy2(source, target)
        manifest["reused"].append({"file": name, "sha256": digest(target)})
    shutil.copy2(ROOT / "assets" / "logo.png", OUT / "logo.png")
    manifest["reused"].append({"file": "logo.png", "sha256": digest(OUT / "logo.png")})
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps({"generated": len(manifest["generated"]), "reused": len(manifest["reused"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
