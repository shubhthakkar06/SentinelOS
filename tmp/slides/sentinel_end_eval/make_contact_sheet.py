from pathlib import Path
from PIL import Image, ImageDraw

files = sorted(Path("tmp/slides/sentinel_end_eval/preview").glob("slide-*.png"))
thumb_w, thumb_h = 320, 180
rows = 5
cols = 3
label_h = 34
canvas = Image.new("RGB", (thumb_w * cols, (thumb_h + label_h) * rows), (8, 17, 24))
draw = ImageDraw.Draw(canvas)

for idx, file_path in enumerate(files):
    image = Image.open(file_path).convert("RGB")
    image.thumbnail((thumb_w, thumb_h))
    x = (idx % cols) * thumb_w
    y = (idx // cols) * (thumb_h + label_h)
    canvas.paste(image, (x, y))
    draw.text((x + 8, y + thumb_h + 8), file_path.name, fill=(220, 240, 245))

canvas.save("tmp/slides/sentinel_end_eval/contact_sheet.png")
