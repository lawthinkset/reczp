# 📞 RecepZo — 24/7 AI Phone Receptionist Automation

[![Run Pipeline](https://github.com/lawthinkset/reczp/actions/workflows/run.yml/badge.svg)](https://github.com/lawthinkset/reczp/actions/workflows/run.yml)

**RecepZo** ([recepzo.com](https://recepzo.com/)) is an automated multi-platform Reels publishing bot demonstrating how AI receptionists handle business phone calls, book appointments, and capture leads 24/7.

---

## ⚡ How It Works

```
Google Drive (RecepZo Video Folder)
    ↓
auto_pipeline.py
    ↓
[1] Fetch video from Google Drive
[2] Remove watermark & format for Reels (1080x1920, AAC 44.1kHz stereo audio, loudnorm -16 LUFS)
[3] Generate high-converting AI SaaS caption via Pollinations AI
[4] Publish as Facebook Reel + Pinned Comment + Story
[5] Auto-discover & Publish to linked Instagram Professional Account (Reels + Feed)
```

---

## 🔗 Connecting Instagram to Facebook

The pipeline supports **automatic Instagram Reel publishing**:

1. **Convert your Instagram account to Professional**:
   - In the Instagram mobile app, go to **Settings** > **Account** > **Switch to Professional Account** (choose *Creator* or *Business*).
2. **Link Instagram to your Facebook Page**:
   - In **Meta Business Suite** ([business.facebook.com](https://business.facebook.com/)) or Facebook Page Settings:
   - Navigate to **Page Settings** > **Linked Accounts** > **Instagram**.
   - Click **Connect Account** and log in to authorize.
3. **Automatic Detection**:
   - The pipeline queries your Facebook Page via the Graph API and **automatically detects** your linked Instagram account (`instagram_business_account`).
   - You can also optionally set `INSTAGRAM_ACCOUNT_ID` in your GitHub repository secrets if you prefer explicit configuration.
4. **Voice & Audio Guarantee**:
   - Video processing in `process_videos.py` ensures audio tracks are encoded to **AAC stereo at 44,100 Hz** with **-16 LUFS loudness normalization** and `+faststart`.
   - This satisfies Meta's strict Instagram Reels audio ingestion specifications so spoken voice and AI phone audio are never muted or dropped.

---

## 🔍 Diagnostic Tool

To verify your Facebook Page, linked Instagram account, token permissions, and audio codecs:

```bash
python check_instagram.py
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
| `INSTAGRAM_ACCOUNT_ID` | *(Optional)* Explicit Instagram account ID (auto-detected if linked to Facebook Page) |
| `PINNED_COMMENT_LINK` | *(Optional)* Link for pinned comment (default: `https://recepzo.com/`) |

---

## 📁 Project Structure

```
recepzo/
├── auto_pipeline.py         # Main pipeline orchestrator (Facebook + Instagram)
├── check_instagram.py       # Diagnostic script for Meta & Instagram linking
├── daily_publisher.py       # Caption generation + Facebook & Instagram publisher
├── google_drive_fetch.py    # Google Drive video fetcher
├── process_videos.py        # FFmpeg video & audio processor for Reels (AAC 44.1kHz)
├── upload/
│   ├── upload_facebook.py   # Facebook Reel + Story uploader
│   └── upload_instagram.py  # Instagram Reel uploader with auto-discovery & feed sharing
├── published_videos.json    # Published history log
├── requirements.txt         # Python dependencies
└── .github/workflows/
    └── run.yml              # Daily scheduling at 4 AM, 12 PM & 8 PM UTC
```
