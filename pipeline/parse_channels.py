import glob, os, re, sys, html, json
from bs4 import BeautifulSoup
from urllib.parse import unquote

sys.stdout.reconfigure(encoding='utf-8')

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))

def clean_html_content(content_tag):
    if not content_tag:
        return "", ""
    
    # Replace discord emoji imgs with their alt text
    for emoji_img in content_tag.find_all('img', class_='chatlog__emoji'):
        alt = emoji_img.get('alt', '')
        emoji_img.replace_with(alt)
    
    # Extract plain text for search
    plain_text = content_tag.get_text().strip()
    
    # Format HTML cleanly
    # Get inner html of span.chatlog__markdown-preserve if available
    preserve = content_tag.find('span', class_='chatlog__markdown-preserve')
    if preserve:
        raw_html = "".join([str(c) for c in preserve.contents])
    else:
        raw_html = "".join([str(c) for c in content_tag.contents])
    
    return raw_html.strip(), plain_text

def parse_all_channels():
    all_files = glob.glob(os.path.join(DOCS_DIR, '*.html'))
    files = [f for f in all_files if re.search(r'phần-(\d+)', os.path.basename(f))]
    
    # Sort files properly by channel part number
    def get_part_num(fpath):
        m = re.search(r'phần-(\d+)', os.path.basename(fpath))
        return int(m.group(1)) if m else 999
    
    files = sorted(files, key=get_part_num)
    
    all_parts = []
    
    for fpath in files:
        fname = os.path.basename(fpath)
        part_num = get_part_num(fpath)
        print(f"Processing Phần {part_num}: {fname[:50]}...")
        
        with open(fpath, 'r', encoding='utf-8') as fp:
            soup = BeautifulSoup(fp.read(), 'html.parser')
        
        channel_title = f"Phần {part_num} - Bài Viết FB"
        preamble = soup.find('div', class_='preamble__entries-container')
        if preamble:
            chan_name_el = preamble.find_all('div', class_='preamble__entry')
            if len(chan_name_el) > 1:
                channel_title = chan_name_el[1].text.strip()
        
        containers = soup.find_all('div', class_='chatlog__message-container')
        
        items = []
        for c in containers:
            msg_id = c.get('data-message-id', '')
            
            # Timestamp
            ts_el = c.find('span', class_='chatlog__timestamp')
            if not ts_el:
                ts_el = c.find('div', class_='chatlog__short-timestamp')
            timestamp = ts_el.text.strip() if ts_el else ""
            
            # Text content
            content_div = c.find('div', class_='chatlog__content')
            raw_html, plain_text = clean_html_content(content_div)
            
            # Images
            imgs = []
            for img_el in c.find_all('img', class_='chatlog__attachment-media'):
                src = img_el.get('src', '')
                if src:
                    # decode URL encoding e.g. %20 -> space
                    decoded_src = unquote(src)
                    imgs.append(decoded_src)
            
            # Only keep if there is either text or image
            if plain_text or imgs:
                # Determine title/snippet
                title_guess = ""
                if plain_text:
                    lines = [l.strip() for l in plain_text.split('\n') if l.strip()]
                    if lines:
                        first_line = lines[0]
                        # Clean markers like >>>>> or emojis
                        clean_first = re.sub(r'^[>♥❤️\s\-]+', '', first_line).strip()
                        clean_first = re.sub(r'[<♥❤️\s\-]+$', '', clean_first).strip()
                        title_guess = clean_first[:80]
                
                items.append({
                    "id": msg_id,
                    "timestamp": timestamp,
                    "title": title_guess,
                    "contentHtml": raw_html,
                    "contentText": plain_text,
                    "images": imgs
                })
        
        all_parts.append({
            "part": part_num,
            "title": f"Phần {part_num}",
            "channel": channel_title,
            "itemCount": len(items),
            "imageCount": sum(len(x['images']) for x in items),
            "items": items
        })
    
    return all_parts

if __name__ == '__main__':
    parts = parse_all_channels()
    total_items = sum(p['itemCount'] for p in parts)
    total_imgs = sum(p['imageCount'] for p in parts)
    print(f"\nDone parsing! Total Parts: {len(parts)}, Items: {total_items}, Images: {total_imgs}")
    
    output_json = os.path.join(DOCS_DIR, 'docs_data.json')
    with open(output_json, 'w', encoding='utf-8') as fp:
        json.dump(parts, fp, ensure_ascii=False, indent=2)
    print(f"Saved database to {output_json}")
