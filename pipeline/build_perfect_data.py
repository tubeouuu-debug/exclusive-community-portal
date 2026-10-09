import json, sys, re, os, html

sys.stdout.reconfigure(encoding='utf-8')

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(DOCS_DIR, 'docs_data.json'), 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

def clean_boilerplate_markers(text):
    """Strips Discord-specific copy-paste headers from beginning of text"""
    if not text:
        return ""
    lines = text.split('\n')
    cleaned_lines = []
    
    for l in lines:
        stripped = l.strip()
        # Check if line is purely a marker or repetitive disclaimer
        if re.match(r'^[>♥❤️\s\-*#]*bài viết\s*\d+\s*:?[<♥❤️\s\-*#]*$', stripped, re.IGNORECASE):
            continue
        if re.match(r'^[>♥❤️\s\-*#]*(nội dung\s+)?(dành cho|cho người|thành viên).*?(đăng ký)[<♥❤️\s\-*#]*$', stripped, re.IGNORECASE):
            continue
        if stripped == '\\':
            continue
        # Also clean leading marker from line if attached
        l_clean = re.sub(r'^[>♥❤️\s\-*#]*bài viết\s*\d+\s*<?<?<?<?<?\s*[:\s\-*]*', '', l, flags=re.IGNORECASE)
        l_clean = re.sub(r'^[>♥❤️\s\-*#]*(nội dung\s+)?(dành cho|cho người|thành viên).*?(đăng ký)[<♥❤️\s\-*#:]*', '', l_clean, flags=re.IGNORECASE)
        cleaned_lines.append(l_clean)
        
    result = '\n'.join(cleaned_lines).strip()
    return result

def extract_real_title(text):
    """
    Extracts an explicit title ONLY if author deliberately wrote one.
    Otherwise returns None (preventing chopped headings).
    """
    if not text:
        return None
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return None
        
    line0 = lines[0]
    # Check if line0 has >>>>>bài viết X<<<<< [Title]
    m_bv = re.search(r'>>>>>\s*bài viết\s*\d+\s*<?<?<?<?<?\s*[:\s\-*]*(.*)', line0, re.IGNORECASE)
    if m_bv:
        cand = m_bv.group(1).strip()
        cand = re.sub(r'^[>♥❤️\s\-*#]+', '', cand).strip()
        cand = re.sub(r'[<♥❤️\s\-*#]+$', '', cand).strip()
        if len(cand) > 3:
            return cand

    # Check candidates in first 4 non-empty lines
    for l in lines[:4]:
        cleaned = re.sub(r'^[>♥❤️\s\-*#]+', '', l).strip()
        cleaned = re.sub(r'[<♥❤️\s\-*#]+$', '', cleaned).strip()
        if any(k in cleaned.lower() for k in [
            'nội dung dành cho', 'nội dung cho người', 'dành cho người', 'thành viên đăng ký',
            'bài viết 1', 'bài viết 2', 'bài viết 3'
        ]):
            continue
        
        letters = re.findall(r'[a-zA-ZÀ-ỹ]', cleaned)
        if not letters:
            continue
            
        upper_count = sum(1 for c in letters if c.isupper())
        is_mostly_caps = upper_count / len(letters) >= 0.70 and len(cleaned) <= 60
        
        # If mostly caps (e.g. VÌ SAO XEKO KHÔNG THỂ NGHÈO? or CHỒNG NGOAN VẪN ĐI TÌM SUGAR BABY)
        if is_mostly_caps and len(letters) >= 6:
            return cleaned
            
        # Standalone heading must NOT end with ? ! . : ,
        if 4 < len(cleaned) <= 45 and not cleaned.endswith(('.', ':', ',', '?', '!')):
            return cleaned

    return None

def get_word_safe_preview(text, max_len=75):
    """Clean preview for search and list navigation, never chops words mid-way"""
    if not text:
        return "Bài viết"
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for l in lines:
        cleaned = re.sub(r'^[>♥❤️\s\-*#]+', '', l).strip()
        cleaned = re.sub(r'[<♥❤️\s\-*#]+$', '', cleaned).strip()
        if any(k in cleaned.lower() for k in ['nội dung dành cho', 'nội dung cho người', 'dành cho người', 'bài viết 1:', 'bài viết 2:']):
            continue
        if len(cleaned) < 5:
            continue
        if len(cleaned) <= max_len:
            return cleaned
        cut = cleaned[:max_len]
        last_sp = cut.rfind(' ')
        if last_sp > 25:
            cut = cut[:last_sp]
        return cut + '...'
    return "Bài viết"

def format_text_to_html(text):
    if not text:
        return ""
    paragraphs = re.split(r'\n{2,}', text.strip())
    html_parts = []
    
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        lines = p.split('\n')
        is_list = all(re.match(r'^[•\-\*]\s+', l.strip()) or not l.strip() for l in lines if l.strip())
        
        if is_list and len(lines) > 1:
            items_html = []
            for l in lines:
                l_clean = re.sub(r'^[•\-\*]\s+', '', l.strip())
                if l_clean:
                    items_html.append(f"<li>{html.escape(l_clean)}</li>")
            html_parts.append(f"<ul>{''.join(items_html)}</ul>")
        elif p.startswith('>'):
            quote_text = re.sub(r'^>\s*', '', p, flags=re.MULTILINE)
            html_parts.append(f"<blockquote>{html.escape(quote_text).replace(chr(10), '<br>')}</blockquote>")
        else:
            escaped_p = html.escape(p).replace('\n', '<br>')
            html_parts.append(f"<p>{escaped_p}</p>")
            
    return "".join(html_parts)

def smart_group_channel(raw_items, part_num):
    articles = []
    current = {
        "timestamp": "",
        "texts": [],
        "images": []
    }

    n = len(raw_items)
    for i, item in enumerate(raw_items):
        txt = item['contentText'].strip()
        imgs = item['images']
        ts = item['timestamp']
        
        curr_chars = sum(len(t) for t in current['texts'])
        
        should_split = False
        
        # Condition 1: Explicit marker starts a new post
        is_bv_marker = bool(re.search(r'>>>>>\s*bài viết\s*\d+', txt, re.IGNORECASE))
        is_member_marker = bool(re.search(r'(nội dung\s+)?(dành cho|cho người|thành viên).*?(đăng ký)', txt, re.IGNORECASE))
        is_custom_marker = bool(re.search(r'^\s*(bài viết sưu tầm|câu chuyện sưu tầm|\{?câu chuyện sưu tầm|trích rep cmt)', txt, re.IGNORECASE))
        
        if (is_bv_marker or is_member_marker or is_custom_marker) and curr_chars > 60:
            should_split = True
        # Condition 2: A new item with an IMAGE arrives, AND current already has completed text!
        elif len(imgs) > 0 and curr_chars > 100:
            # Look ahead: is this image followed by text in this item or in next items?
            has_upcoming_text = bool(txt)
            if not has_upcoming_text:
                for k in range(i + 1, min(i + 4, n)):
                    next_txt = raw_items[k]['contentText'].strip()
                    if len(next_txt) > 30:
                        has_upcoming_text = True
                        break
                    # If next item is another image without text, it belongs to the same cluster
                    if len(raw_items[k]['images']) > 0 and not next_txt:
                        continue
            if has_upcoming_text:
                should_split = True


        if should_split and (current['texts'] or current['images']):
            articles.append(current)
            current = {
                "timestamp": ts,
                "texts": [],
                "images": []
            }

        if not current['timestamp'] and ts:
            current['timestamp'] = ts

        if imgs:
            current['images'].extend(imgs)

        if txt and txt != '\\':
            current['texts'].append(txt)

    if current['texts'] or current['images']:
        articles.append(current)

    # Post-process
    formatted_articles = []
    for idx, art in enumerate(articles):
        full_raw_text = "\n\n".join(art['texts'])
        
        real_title = extract_real_title(full_raw_text)
        preview = get_word_safe_preview(full_raw_text)
        
        cleaned_body_text = clean_boilerplate_markers(full_raw_text)
        formatted_html = format_text_to_html(cleaned_body_text)
        
        formatted_articles.append({
            "id": f"p{part_num}-art{idx+1}",
            "index": idx + 1,
            "timestamp": art['timestamp'],
            "hasExplicitTitle": bool(real_title),
            "title": real_title if real_title else "",
            "preview": preview,
            "contentHtml": formatted_html,
            "contentText": cleaned_body_text,
            "images": art['images']
        })

    return formatted_articles

def build_perfect_data():
    grouped_parts = []
    for part in raw_data:
        part_num = part['part']
        articles = smart_group_channel(part['items'], part_num)
        grouped_parts.append({
            "part": part_num,
            "title": f"Phần {part_num}",
            "channel": part['channel'],
            "articleCount": len(articles),
            "imageCount": sum(len(a['images']) for a in articles),
            "articles": articles
        })
    return grouped_parts

if __name__ == '__main__':
    grouped_data = build_perfect_data()
    total_arts = sum(p['articleCount'] for p in grouped_data)
    total_imgs = sum(p['imageCount'] for p in grouped_data)
    print(f"Total Parts: {len(grouped_data)}, Articles: {total_arts}, Images: {total_imgs}")
    
    # Save to data.js
    data_js_path = os.path.join(DOCS_DIR, 'data.js')
    with open(data_js_path, 'w', encoding='utf-8') as f:
        f.write('window.DOCS_DATA = ' + json.dumps(grouped_data, ensure_ascii=False) + ';')
    print(f"Updated {data_js_path} successfully!")
