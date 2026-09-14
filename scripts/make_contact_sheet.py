from pathlib import Path
from PIL import Image, ImageDraw


source_dir = Path(r"C:\dev\hpo-ptbr-lab\tmp\aula04_20260911\pdf_pages")
output_dir = source_dir.parent / "contact_sheets"
output_dir.mkdir(parents=True, exist_ok=True)
files = sorted(source_dir.glob("page-*.png"))

thumb_w = 330
thumb_h = 430
cols = 4
rows = 2
per_sheet = cols * rows

for sheet_index in range(0, len(files), per_sheet):
    batch = files[sheet_index : sheet_index + per_sheet]
    canvas = Image.new("RGB", (cols * thumb_w, rows * thumb_h), "white")
    draw = ImageDraw.Draw(canvas)
    for idx, path in enumerate(batch):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb_w - 12, thumb_h - 28))
        x = (idx % cols) * thumb_w + (thumb_w - image.width) // 2
        y = (idx // cols) * thumb_h + 22
        canvas.paste(image, (x, y))
        draw.text(((idx % cols) * thumb_w + 6, (idx // cols) * thumb_h + 4), path.stem, fill="black")
    out = output_dir / f"sheet-{sheet_index // per_sheet + 1}.png"
    canvas.save(out)
    print(out)
