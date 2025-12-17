"""Simple mock server for Flashback Daily demo."""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os

# Sample flashback data
SAMPLE_EVENTS = {
    "apollo": {
        "scene_id": "1969-07-20__en__apollo-11__v1",
        "date": "1969-07-20",
        "title": "Apollo 11 Moon Landing",
        "year": 1969,
        "summary": "NASA's Apollo 11 mission successfully landed the first humans on the Moon. Astronauts Neil Armstrong and Buzz Aldrin walked on the lunar surface while Michael Collins orbited above.",
        "sources": [
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Apollo_11"},
            {"label": "On this Day", "url": "https://en.wikipedia.org/wiki/Wikipedia:On_this_day/Today"}
        ],
        "lenses": [
            {"lens_id": 1, "name": "Wide", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Aldrin_Apollo_11_original.jpg/800px-Aldrin_Apollo_11_original.jpg"},
            {"lens_id": 2, "name": "POV", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Apollo_11_first_step.jpg/800px-Apollo_11_first_step.jpg"},
            {"lens_id": 3, "name": "Detail", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Aldrin_bootprint.jpg/800px-Aldrin_bootprint.jpg"},
            {"lens_id": 4, "name": "Behind", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Apollo_11_Mission_Control.jpg/800px-Apollo_11_Mission_Control.jpg"},
            {"lens_id": 5, "name": "After", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Apollo_11_Crew.jpg/800px-Apollo_11_Crew.jpg"}
        ],
        "disclosure": "AI Recreation"
    },
    "berlin": {
        "scene_id": "1989-11-09__en__berlin-wall__v1",
        "date": "1989-11-09",
        "title": "Fall of the Berlin Wall",
        "year": 1989,
        "summary": "The Berlin Wall fell after 28 years of dividing East and West Berlin. Thousands of East Germans crossed freely into West Berlin in scenes of jubilant celebration.",
        "sources": [
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Fall_of_the_Berlin_Wall"},
            {"label": "On this Day", "url": "https://en.wikipedia.org/wiki/Wikipedia:On_this_day/Today"}
        ],
        "lenses": [
            {"lens_id": 1, "name": "Wide", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/West_and_East_Germans_at_the_Brandenburg_Gate_in_1989.jpg/800px-West_and_East_Germans_at_the_Brandenburg_Gate_in_1989.jpg"},
            {"lens_id": 2, "name": "POV", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/Thefalloftheberlinwall1989.JPG/800px-Thefalloftheberlinwall1989.JPG"},
            {"lens_id": 3, "name": "Detail", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Berlin_Wall_graffiti.jpg/800px-Berlin_Wall_graffiti.jpg"},
            {"lens_id": 4, "name": "Behind", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Bundesarchiv_Bild_183-1989-1118-028%2C_Berlin%2C_Grenz%C3%BCbergang_Bornholmer_Stra%C3%9Fe.jpg/800px-Bundesarchiv_Bild_183-1989-1118-028%2C_Berlin%2C_Grenz%C3%BCbergang_Bornholmer_Stra%C3%9Fe.jpg"},
            {"lens_id": 5, "name": "After", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Berlin_Wall_Memorial%2C_2012.jpg/800px-Berlin_Wall_Memorial%2C_2012.jpg"}
        ],
        "disclosure": "AI Recreation"
    },
    "wright": {
        "scene_id": "1903-12-17__en__wright-brothers__v1",
        "date": "1903-12-17",
        "title": "Wright Brothers First Flight",
        "year": 1903,
        "summary": "Orville and Wilbur Wright achieved the first sustained, controlled, powered heavier-than-air flight at Kitty Hawk, North Carolina. The flight lasted 12 seconds and covered 120 feet.",
        "sources": [
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Wright_brothers"},
            {"label": "On this Day", "url": "https://en.wikipedia.org/wiki/Wikipedia:On_this_day/Today"}
        ],
        "lenses": [
            {"lens_id": 1, "name": "Wide", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/First_flight2.jpg/800px-First_flight2.jpg"},
            {"lens_id": 2, "name": "POV", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/1905_Wright_Flyer_III.jpg/800px-1905_Wright_Flyer_III.jpg"},
            {"lens_id": 3, "name": "Detail", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Wright_Flyer_Engine.jpg/800px-Wright_Flyer_Engine.jpg"},
            {"lens_id": 4, "name": "Behind", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Wrightcycle.jpg/800px-Wrightcycle.jpg"},
            {"lens_id": 5, "name": "After", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/Orville_Wright_1905-crop.jpg/800px-Orville_Wright_1905-crop.jpg"}
        ],
        "disclosure": "AI Recreation"
    }
}

class FlashbackHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # CORS headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if self.path == '/health':
            self.wfile.write(json.dumps({"status": "healthy"}).encode())
        elif self.path.startswith('/v1/flashback/today'):
            response = {"status": "ready", "scene": SAMPLE_EVENTS["wright"]}
            self.wfile.write(json.dumps(response).encode())
        elif self.path.startswith('/v1/flashback/random'):
            import random
            event = random.choice(list(SAMPLE_EVENTS.values()))
            response = {"status": "ready", "scene": event}
            self.wfile.write(json.dumps(response).encode())
        elif self.path.startswith('/v1/flashback'):
            # Default to Apollo 11
            response = {"status": "ready", "scene": SAMPLE_EVENTS["apollo"]}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.wfile.write(json.dumps({"error": "not found"}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

if __name__ == '__main__':
    port = 8000
    server = HTTPServer(('0.0.0.0', port), FlashbackHandler)
    print(f'Mock API running at http://localhost:{port}')
    print('Press Ctrl+C to stop')
    server.serve_forever()
