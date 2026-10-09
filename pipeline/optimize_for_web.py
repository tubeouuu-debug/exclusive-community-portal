import os, sys, shutil, time, json
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
DEST_DIR = os.path.abspath(os.path.join(SRC_DIR, '..', 'DocsDiscord_Web'))

os.makedirs(DEST_DIR, exist_ok=True)

print("Đang tối ưu hóa hình ảnh sang WebP siêu nhẹ...")
t0 = time.time()
converted_count = 0
total_orig_size = 0
total_new_size = 0

# Find all image directories
for item in os.listdir(SRC_DIR):
    item_src = os.path.join(SRC_DIR, item)
    if os.path.isdir(item_src) and item_src.endswith('.html_Files'):
        item_dest = os.path.join(DEST_DIR, item)
        os.makedirs(item_dest, exist_ok=True)
        
        for fname in os.listdir(item_src):
            if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                f_src = os.path.join(item_src, fname)
                base_name = os.path.splitext(fname)[0]
                f_dest = os.path.join(item_dest, base_name + '.webp')
                
                sz_o = os.path.getsize(f_src)
                total_orig_size += sz_o
                
                try:
                    im = Image.open(f_src)
                    w, h = im.size
                    # Limit max width to 1400px (standard crisp retina display for reading)
                    if w > 1400:
                        im = im.resize((1400, int(h * 1400 / w)), Image.Resampling.LANCZOS)
                    if im.mode in ('RGBA', 'P'):
                        im = im.convert('RGB')
                    
                    im.save(f_dest, 'WEBP', quality=82, method=4)
                    sz_n = os.path.getsize(f_dest)
                    total_new_size += sz_n
                    converted_count += 1
                except Exception as e:
                    # Fallback copy if error
                    shutil.copy2(f_src, os.path.join(item_dest, fname))
                    total_new_size += sz_o

print(f"Đã nén xong {converted_count} ảnh trong {time.time() - t0:.1f} giây!")
print(f"Dung lượng ban đầu: {total_orig_size / (1024*1024):.2f} MB")
print(f"Dung lượng sau khi nén: {total_new_size / (1024*1024):.2f} MB")
print(f"Giảm: {(1 - total_new_size / total_orig_size) * 100:.1f}%!")

# Copy and update data.js
data_js_src = os.path.join(SRC_DIR, 'data.js')
data_js_dest = os.path.join(DEST_DIR, 'data.js')
with open(data_js_src, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace .png, .jpg, .jpeg extensions in image paths with .webp
import re
content_webp = re.sub(r'\.(png|jpg|jpeg)\b', '.webp', content, flags=re.IGNORECASE)
with open(data_js_dest, 'w', encoding='utf-8') as f:
    f.write(content_webp)

# Copy and update index.html
index_src = os.path.join(SRC_DIR, 'index.html')
index_dest = os.path.join(DEST_DIR, 'index.html')
with open(index_src, 'r', encoding='utf-8') as f:
    idx_content = f.read()

# Avatar path replacement in index.html
idx_content_webp = re.sub(r'\.(png|jpg|jpeg)\b', '.webp', idx_content, flags=re.IGNORECASE)
with open(index_dest, 'w', encoding='utf-8') as f:
    f.write(idx_content_webp)

# Copy functions directory if exists
func_src = os.path.join(SRC_DIR, 'functions')
func_dest = os.path.join(DEST_DIR, 'functions')
if os.path.exists(func_src):
    shutil.copytree(func_src, func_dest, dirs_exist_ok=True)

# Summary of DEST_DIR
dest_files = []
dest_size = 0
for r, _, fs in os.walk(DEST_DIR):
    for f in fs:
        dest_files.append(f)
        dest_size += os.path.getsize(os.path.join(r, f))

print("\n--- KẾT QUẢ THƯ MỤC WEB MỚI ---")
print(f"Đường dẫn: {DEST_DIR}")
print(f"Tổng số file: {len(dest_files)} files (so với 617 files trước đó)")
print(f"Tổng dung lượng: {dest_size / (1024*1024):.2f} MB (so với 431 MB trước đó)")
