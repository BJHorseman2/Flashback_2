# Flashback Daily

A share-first "time capsule" app that generates editorial-realistic AI recreations of historical events.

Pick a date → we select the most culturally significant event → generate 5 consistent "Zoom Lens" recreations → present as a beautiful swipeable story with sources → one-tap share.

## Core Features

- **Grounded in Sources**: Everything derives from Wikimedia (Wikipedia, Wikidata, Pageviews API)
- **5 Zoom Lenses**: Wide, POV, Detail, Behind the Scenes, Aftermath
- **Quality Controlled**: Automated QC with vision checks and retries
- **Transparent**: AI Recreation labels, visible sources, no hallucinated history

## Architecture

```
apps/
  ios/                    # SwiftUI iOS app
services/
  api/                    # FastAPI backend
  worker/                 # Celery image generation worker
infra/
  docker/                 # Docker configs
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Google Cloud account (for Vertex AI image generation)

### Local Development

1. **Clone and setup**
```bash
git clone <repo>
cd Flashback_2
cp .env.example .env
# Edit .env with your credentials
```

2. **Start services with Docker**
```bash
cd infra/docker
docker-compose up -d
```

3. **Run API locally**
```bash
cd services/api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

4. **Run worker locally**
```bash
cd services/worker
pip install -r requirements.txt
celery -A app.celery_app worker --loglevel=info
```

### iOS App

Open `apps/ios/FlashbackDaily/FlashbackDaily.xcodeproj` in Xcode and run.

## API Endpoints

### GET /v1/flashback?date=YYYY-MM-DD&lang=en

Get flashback for a specific date.

```json
{
  "status": "ready",
  "scene": {
    "scene_id": "2024-07-20__en__apollo-11__v1",
    "date": "2024-07-20",
    "title": "Apollo 11 Moon Landing",
    "year": 1969,
    "summary": "Two sentences exactly.",
    "sources": [
      {"label": "Wikipedia", "url": "..."},
      {"label": "On this Day", "url": "..."}
    ],
    "lenses": [
      {"lens_id": 1, "name": "Wide", "image_url": "..."},
      {"lens_id": 2, "name": "POV", "image_url": "..."},
      {"lens_id": 3, "name": "Detail", "image_url": "..."},
      {"lens_id": 4, "name": "Behind", "image_url": "..."},
      {"lens_id": 5, "name": "After", "image_url": "..."}
    ],
    "disclosure": "AI Recreation"
  }
}
```

### GET /v1/flashback/today
### GET /v1/flashback/random
### POST /v1/flashback/generate

## The 5 Zoom Lenses

1. **Wide (Establishing)** - Place and scale, 35mm wide shot
2. **POV (Witness)** - "I'm there" perspective, shoulder-height
3. **Detail (Close-up)** - Defining object, macro lens
4. **Behind** - Decision room, mechanism view
5. **After (Aftermath)** - Immediate consequence, no gore

## Data Sources

- **Events**: [Wikimedia On This Day Feed API](https://api.wikimedia.org/wiki/Feed_API/Reference/On_this_day)
- **Ranking**: [Wikimedia Pageviews API](https://wikimedia.org/api/rest_v1/)
- **Structured Data**: [Wikidata](https://www.wikidata.org/) (CC0)
- **Images**: Vertex AI Imagen 3

## SceneSpec (Truth Contract)

```json
{
  "style_pack": "editorial_realism_v1",
  "event_title": "Apollo 11 Moon Landing",
  "year": 1969,
  "location": {"name": "Moon", "coords": [0, 0]},
  "setting": {"environment": "outdoor", "time_of_day": "day"},
  "era_cues": ["space equipment", "1960s technology"],
  "roles": ["astronauts", "scientists"],
  "key_objects": ["lunar module", "American flag"],
  "mood": "hopeful",
  "must_include": ["period-appropriate space suits"],
  "must_not_include": ["readable text", "logos", "identifiable faces"]
}
```

## Quality Control

After each image generation:
1. Vision model checks must_include/must_not_include
2. Checks for readable text, logos, identifiable faces
3. If fail → regenerate with corrections (max 2 retries)
4. Store QC results for debugging

## Attribution & Compliance

- Always show source links
- Label all generated images: "AI Recreation"
- Wikimedia content reuse per their guidelines
- Wikidata structured data is CC0

## Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
GCP_PROJECT_ID=your-project
GCP_REGION=us-central1
GCS_BUCKET=flashback-assets
GEMINI_MODEL=gemini-2.0-flash-exp
IMAGE_MODEL=imagen-3.0-generate-001
```

## License

MIT
