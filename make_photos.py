#!/usr/bin/env python3
"""
폴더(2022~2026, Wedding)를 스캔해서 photos.js 를 만들고,
화면용으로 줄인 사진을 resized/ 폴더에 만들어 줍니다.

- index.html 과 같은 위치에 두고 실행:  python make_photos.py
- 처음 한 번만:  pip install pillow
- 멘트/날짜/제목/소개글은 다시 실행해도 유지됩니다.
- 이미 줄여 둔 사진은 다시 만들지 않아서 두 번째부터는 빨라요.
"""
import json, os, re, sys

try:
    from PIL import Image, ImageOps
except ImportError:
    print("Pillow 가 필요해요. 터미널에서 아래를 먼저 실행해 주세요:\n  pip install pillow")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDERS = ["2022", "2023", "2024", "2025", "2026", "Wedding"]
IMG = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
KEEP = {".gif"}                      # 움직이는 gif 가 깨지지 않게 원본 그대로 사용
VID = {".mp4", ".mov", ".webm", ".m4v"}
SKIP = {".heic", ".heif"}
OUT = os.path.join(HERE, "photos.js")
CACHE = "resized"
SIZES = {"thumb": (800, 80), "view": (1920, 85)}   # 종류: (최대 가로·세로 px, JPG 품질)


def natural(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def load_old():
    if not os.path.exists(OUT):
        return {}
    txt = open(OUT, encoding="utf-8").read()
    m = re.search(r"window\.ALBUM\s*=\s*(\{.*\})\s*;?\s*$", txt, re.S)
    try:
        return json.loads(m.group(1)) if m else {}
    except Exception:
        print("! 기존 photos.js 를 읽지 못해 새로 만듭니다.")
        return {}


def find_folder(name):
    for d in os.listdir(HERE):
        if d.lower() == name.lower() and os.path.isdir(os.path.join(HERE, d)):
            return d
    return None


stats = {"made": 0, "failed": 0}


def make_resized(src_abs, rel, kind):
    """줄인 사진을 만들고 index.html 기준 상대 경로를 돌려줘요. 실패하면 None."""
    maxpx, quality = SIZES[kind]
    out_rel = f"{CACHE}/{kind}/{rel}.jpg"
    out_abs = os.path.join(HERE, *out_rel.split("/"))
    if os.path.exists(out_abs) and os.path.getmtime(out_abs) >= os.path.getmtime(src_abs):
        return out_rel
    try:
        os.makedirs(os.path.dirname(out_abs), exist_ok=True)
        with Image.open(src_abs) as im:
            im = ImageOps.exif_transpose(im)      # 폰 사진 회전 정보 반영
            im.thumbnail((maxpx, maxpx), Image.LANCZOS)   # 작은 사진은 키우지 않아요
            im.convert("RGB").save(out_abs, "JPEG", quality=quality, optimize=True, progressive=True)
        stats["made"] += 1
        return out_rel
    except Exception as e:
        stats["failed"] += 1
        print(f"! 줄이기 실패 ({rel}): {e}")
        return None


old = load_old()
old_photos = {p["src"]: p for p in old.get("photos", [])}
old_order = {p["src"]: i for i, p in enumerate(old.get("photos", []))}

photos = []
for tab in FOLDERS:
    folder = find_folder(tab)
    if not folder:
        print(f"- '{tab}' 폴더가 없어요 (건너뜀)")
        continue
    found = []
    for fn in os.listdir(os.path.join(HERE, folder)):
        ext = os.path.splitext(fn)[1].lower()
        if fn.startswith("."):
            continue
        if ext in SKIP:
            print(f"! HEIC는 브라우저에서 안 열려요. JPG로 변환해 주세요: {folder}/{fn}")
            continue
        if ext in IMG or ext in KEEP:
            found.append((f"{folder}/{fn}", "image", ext in IMG))
        elif ext in VID:
            found.append((f"{folder}/{fn}", "video", False))
    known = sorted([f for f in found if f[0] in old_order], key=lambda f: old_order[f[0]])
    new = sorted([f for f in found if f[0] not in old_order], key=lambda f: natural(f[0]))
    for src, typ, resizable in known + new:
        prev = old_photos.get(src, {})
        item = {
            "year": tab,
            "src": src,
            "type": typ,
            "caption": prev.get("caption", ""),
            "date": prev.get("date", ""),
        }
        if resizable:
            src_abs = os.path.join(HERE, *src.split("/"))
            item["thumb"] = make_resized(src_abs, src, "thumb") or src
            item["view"] = make_resized(src_abs, src, "view") or src
        photos.append(item)
    print(f"- {tab}: {len(found)}개")

album = {
    "title": old.get("title", "우리가 함께한 시간"),
    "sub": old.get("sub", "2022 – 2026, 두 사람이 함께 걸어온 길"),
    "notes": {t: old.get("notes", {}).get(t, "") for t in FOLDERS},
    "photos": photos,
}

lines = ["window.ALBUM = {",
         f'"title": {json.dumps(album["title"], ensure_ascii=False)},',
         f'"sub": {json.dumps(album["sub"], ensure_ascii=False)},',
         '"notes": ' + json.dumps(album["notes"], ensure_ascii=False, indent=1) + ",",
         '"photos": [']
for i, p in enumerate(photos):
    lines.append(" " + json.dumps(p, ensure_ascii=False) + ("," if i < len(photos) - 1 else ""))
lines += ["]", "};"]
open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"\n완료: 사진 {len(photos)}개 → photos.js (새로 줄인 사진 {stats['made']}개, 실패 {stats['failed']}개)")
