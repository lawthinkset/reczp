# 📞 RecepZo — 24/7 AI Phone Receptionist Automation

[![Run Pipeline](https://github.com/lawthinkset/reczp/actions/workflows/run.yml/badge.svg)](https://github.com/lawthinkset/reczp/actions/workflows/run.yml)

**RecepZo** ([recepzo.com](https://recepzo.com/)) is an automated Facebook Reels publishing bot demonstrating how AI receptionists handle business phone calls, book appointments, and capture leads 24/7.

---

## ⚡ How It Works

```
Google Drive (RecepZo Video Folder)
    ↓
auto_pipeline.py
    ↓
[1] Fetch video from Google Drive
[2] Remove watermark & format for Reels (1080x1920)
[3] Generate high-converting AI SaaS caption via Pollinations AI
[4] Publish as Facebook Reel + Pinned Comment + Story
```

---

## 🚀 GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `FB_PAGE_ID` | RecepZo Facebook Page ID (`1365270799997392`) |
| `FB_PAGE_ACCESS_TOKEN` | RecepZo Facebook Page Access Token |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | Google Service Account JSON key |
| `GOOGLE_DRIVE_FOLDER_ID` | RecepZo video folder in Google Drive (`1Z_9_J1jq5ZwiuNYwWpQTLUQBA7Eg23vU`) |
| `POLLINATIONS_API_KEY` | AI caption generation (optional — fallback captions built-in) |

---

## 📁 Project Structure

```
recepzo/
├── auto_pipeline.py         # Main pipeline orchestrator
├── daily_publisher.py       # Caption generation + Facebook publish
├── google_drive_fetch.py    # Google Drive video fetcher
├── process_videos.py        # FFmpeg video processor for Reels
├── upload/
│   ├── upload_facebook.py   # Facebook Reel + Story uploader
│   └── upload_instagram.py  # Instagram Reel uploader (optional)
├── published_videos.json    # Published history log
├── requirements.txt         # Python dependencies
└── .github/workflows/
    └── run.yml              # Daily scheduling at 4 AM, 12 PM & 8 PM UTC
```
