"""
Flashback Daily - Fully Functional Backend
Fetches real events from Wikipedia's On This Day API
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import re
from datetime import datetime
import ssl

# Disable SSL verification for simplicity (Wikipedia uses HTTPS)
ssl_context = ssl.create_unverified_context()

def fetch_json(url):
    """Fetch JSON from a URL."""
    headers = {'User-Agent': 'FlashbackDaily/1.0 (Educational Project)'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_on_this_day_events(month, day):
    """Fetch events from Wikipedia On This Day API."""
    url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{month}/{day}"
    data = fetch_json(url)
    if data and 'events' in data:
        return data['events']
    return []

def get_article_image(title):
    """Get the main image for a Wikipedia article."""
    encoded_title = urllib.parse.quote(title.replace(' ', '_'))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
    data = fetch_json(url)
    if data:
        # Try to get thumbnail or original image
        if 'thumbnail' in data:
            return data['thumbnail'].get('source')
        if 'originalimage' in data:
            return data['originalimage'].get('source')
    return None

def get_article_images(title, limit=5):
    """Get multiple images related to an article from Commons."""
    encoded_title = urllib.parse.quote(title)

    # First get the main article image
    images = []
    main_image = get_article_image(title)
    if main_image:
        images.append(main_image)

    # Try to get images from the article's media list
    encoded = urllib.parse.quote(title.replace(' ', '_'))
    url = f"https://en.wikipedia.org/api/rest_v1/page/media-list/{encoded}"
    data = fetch_json(url)

    if data and 'items' in data:
        for item in data['items']:
            if len(images) >= limit:
                break
            if 'srcset' in item:
                # Get the largest image
                srcset = item['srcset']
                if srcset:
                    src = srcset[-1].get('src', '')
                    if src and src.startswith('//'):
                        src = 'https:' + src
                    if src and src not in images:
                        images.append(src)
            elif 'src' in item:
                src = item['src']
                if src.startswith('//'):
                    src = 'https:' + src
                if src not in images:
                    images.append(src)

    # Pad with placeholder if needed
    while len(images) < limit:
        images.append(None)

    return images[:limit]

def get_pageviews(title, days=30):
    """Get pageview count for ranking (simplified)."""
    try:
        encoded = urllib.parse.quote(title.replace(' ', '_'))
        end = datetime.now()
        start = datetime(end.year, end.month, 1)
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{encoded}/daily/{start.strftime('%Y%m%d')}/{end.strftime('%Y%m%d')}"
        data = fetch_json(url)
        if data and 'items' in data:
            return sum(item.get('views', 0) for item in data['items'])
    except:
        pass
    return 0

def rank_events(events):
    """Rank events by significance (simplified - uses article length as proxy)."""
    ranked = []
    for event in events[:20]:  # Limit to top 20 for speed
        pages = event.get('pages', [])
        if not pages:
            continue

        page = pages[0]
        title = page.get('title', '')
        extract = page.get('extract', '')

        # Simple ranking: longer extracts = more significant
        score = len(extract) if extract else 0

        ranked.append({
            'event': event,
            'page': page,
            'score': score
        })

    ranked.sort(key=lambda x: x['score'], reverse=True)
    return ranked

def generate_summary(text, extract):
    """Generate a clean 2-sentence summary."""
    # Combine and clean text
    full_text = f"{text} {extract or ''}"

    # Remove citations and clean up
    full_text = re.sub(r'\[\d+\]', '', full_text)
    full_text = re.sub(r'\s+', ' ', full_text).strip()

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', full_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if len(sentences) >= 2:
        return f"{sentences[0]} {sentences[1]}"
    elif len(sentences) == 1:
        return sentences[0]
    else:
        return text[:200] + "..."

def create_flashback(date_str):
    """Create a complete flashback for a date."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        month = dt.month
        day = dt.day
    except:
        return None

    # Fetch events
    events = get_on_this_day_events(month, day)
    if not events:
        return None

    # Rank and select top event
    ranked = rank_events(events)
    if not ranked:
        return None

    top = ranked[0]
    event = top['event']
    page = top['page']

    title = page.get('title', 'Unknown Event')
    year = event.get('year', 0)
    text = event.get('text', '')
    extract = page.get('extract', '')

    # Generate summary
    summary = generate_summary(text, extract)

    # Get images for 5 lenses
    images = get_article_images(title, 5)

    lens_names = ['Wide', 'POV', 'Detail', 'Behind', 'After']
    lenses = []
    for i, (name, img) in enumerate(zip(lens_names, images)):
        lenses.append({
            'lens_id': i + 1,
            'name': name,
            'image_url': img
        })

    # Build Wikipedia URL
    wiki_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"

    return {
        'scene_id': f"{date_str}__en__{title[:30].lower().replace(' ', '-')}__v1",
        'date': date_str,
        'title': title,
        'year': year,
        'summary': summary,
        'sources': [
            {'label': 'Wikipedia', 'url': wiki_url},
            {'label': 'On this Day', 'url': f'https://en.wikipedia.org/wiki/Wikipedia:On_this_day/Today'}
        ],
        'lenses': lenses,
        'disclosure': 'AI Recreation'
    }


class FlashbackHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_json({})

    def do_GET(self):
        path = self.path.split('?')[0]
        query = {}
        if '?' in self.path:
            query = dict(urllib.parse.parse_qsl(self.path.split('?')[1]))

        if path == '/health':
            self.send_json({'status': 'healthy'})

        elif path == '/v1/flashback/today':
            today = datetime.now().strftime('%Y-%m-%d')
            scene = create_flashback(today)
            if scene:
                self.send_json({'status': 'ready', 'scene': scene})
            else:
                self.send_json({'status': 'failed', 'message': 'No events found'}, 404)

        elif path == '/v1/flashback/random':
            import random
            year = random.randint(1900, 2020)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            date_str = f"{year}-{month:02d}-{day:02d}"
            scene = create_flashback(date_str)
            if scene:
                self.send_json({'status': 'ready', 'scene': scene})
            else:
                self.send_json({'status': 'failed', 'message': 'No events found'}, 404)

        elif path == '/v1/flashback':
            date_str = query.get('date', datetime.now().strftime('%Y-%m-%d'))
            scene = create_flashback(date_str)
            if scene:
                self.send_json({'status': 'ready', 'scene': scene})
            else:
                self.send_json({'status': 'failed', 'message': 'No events found'}, 404)

        else:
            self.send_json({'error': 'Not found'}, 404)

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


if __name__ == '__main__':
    port = 8000
    server = HTTPServer(('0.0.0.0', port), FlashbackHandler)
    print(f"""
╔═══════════════════════════════════════════╗
║       FLASHBACK DAILY - API SERVER        ║
╠═══════════════════════════════════════════╣
║  Running at: http://localhost:{port}         ║
║                                           ║
║  Endpoints:                               ║
║    GET /v1/flashback?date=YYYY-MM-DD      ║
║    GET /v1/flashback/today                ║
║    GET /v1/flashback/random               ║
║                                           ║
║  Press Ctrl+C to stop                     ║
╚═══════════════════════════════════════════╝
""")
    server.serve_forever()
