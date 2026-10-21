"""
Facebook Video / Reels Direct Upload
Supports:
1. Facebook Reels (Resumable upload to /video_reels + Pinned Comment)
2. Facebook Stories (Resumable upload to /video_stories)
3. Direct single-request Feed Video (/videos multipart)
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
import requests
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Load environment
for env_candidate in [Path(".env"), Path("../.env"), Path(__file__).resolve().parent / ".env", Path(__file__).resolve().parent.parent / ".env"]:
    if env_candidate.exists():
        load_dotenv(dotenv_path=env_candidate, override=True)
        break
else:
    load_dotenv()

GRAPH_API_VERSION = 'v21.0'
GRAPH_URL = f'https://graph.facebook.com/{GRAPH_API_VERSION}'


def safe_print(msg: str):
    try:
        print(msg)
    except Exception:
        print(msg.encode("ascii", "replace").decode("ascii"))


def post_pinned_comment(video_id, comment_text, page_token, max_retries=3, delay_seconds=8):
    """
    Posts the first comment on the Reel video and attempts to pin it.
    """
    if not comment_text or not video_id:
        return None

    safe_print(f"  [FB] Waiting {delay_seconds}s for video processing before commenting...")
    time.sleep(delay_seconds)

    comment_url = f"{GRAPH_URL}/{video_id}/comments"
    comment_id = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                comment_url,
                data={
                    'message': comment_text,
                    'access_token': page_token
                },
                timeout=30
            )
            if resp.status_code == 200:
                comment_id = resp.json().get('id')
                safe_print(f"  [FB] Comment posted successfully: {comment_id}")
                break
            else:
                safe_print(f"  [WARN] Comment attempt {attempt} failed ({resp.status_code}): {resp.text}")
                if attempt < max_retries:
                    time.sleep(5)
        except Exception as e:
            safe_print(f"  [WARN] Comment attempt {attempt} error: {e}")
            if attempt < max_retries:
                time.sleep(5)

    if not comment_id:
        safe_print("  [WARN] Could not post comment after retries")
        return None

    try:
        pin_url = f"{GRAPH_URL}/{comment_id}"
        pin_resp = requests.post(
            pin_url,
            data={'is_pinned': 'true', 'access_token': page_token},
            timeout=15
        )
        if pin_resp.status_code == 200:
            safe_print("  [FB] Comment pinned successfully!")
        else:
            safe_print("  [INFO] Comment is placed as top Page comment.")
    except Exception:
        pass

    return comment_id


def upload_reel(video_path, caption="", page_id=None, page_token=None, pin_comment=True, comment_text=None):
    """
    Uploads video as a Facebook Reel using the official 3-phase Reels Publishing API.
    Optionally posts a top/pinned comment.
    """
    page_id = page_id or os.environ.get('FB_PAGE_ID') or os.environ.get('FACEBOOK_PAGE_ID', '')
    page_token = page_token or os.environ.get('FB_PAGE_ACCESS_TOKEN') or os.environ.get('FACEBOOK_ACCESS_TOKEN') or os.environ.get('FB_ACCESS_TOKEN', '')

    if not page_token or not page_id:
        safe_print(f"[SKIP] Facebook credentials not set for page ID: {page_id}")
        return {'status': 'skipped', 'platform': 'facebook', 'page_id': page_id}

    if not os.path.exists(video_path):
        safe_print(f"[ERROR] Video not found: {video_path}")
        return {'status': 'failed', 'platform': 'facebook', 'page_id': page_id}

    file_size = os.path.getsize(video_path)
    safe_print(f"[FB] Uploading reel to Page ({page_id}): {os.path.basename(video_path)} ({file_size / 1024 / 1024:.1f}MB)")

    try:
        # Step 1: Create video container
        init_url = f"{GRAPH_URL}/{page_id}/video_reels"
        init_data = {
            'upload_phase': 'start',
            'access_token': page_token
        }
        resp = requests.post(init_url, data=init_data, timeout=30)
        if resp.status_code != 200:
            safe_print(f"  [ERROR] Init failed ({resp.status_code}): {resp.text}")
            return {'status': 'failed', 'platform': 'facebook', 'page_id': page_id, 'error': resp.text}

        res_json = resp.json()
        video_id = res_json.get('video_id')
        upload_url = res_json.get('upload_url')
        if not video_id or not upload_url:
            safe_print(f"  [ERROR] No video_id or upload_url returned: {res_json}")
            return {'status': 'failed', 'platform': 'facebook', 'page_id': page_id}

        safe_print(f"  Container created: {video_id}")

        # Step 2: Transfer video bytes
        with open(video_path, 'rb') as f:
            video_data = f.read()

        transfer_headers = {
            'Authorization': f'OAuth {page_token}',
            'offset': '0',
            'file_size': str(file_size)
        }
        resp = requests.post(upload_url, headers=transfer_headers, data=video_data, timeout=180)
        if resp.status_code != 200:
            safe_print(f"  [ERROR] Transfer failed ({resp.status_code}): {resp.text}")
            return {'status': 'failed', 'platform': 'facebook', 'page_id': page_id, 'error': resp.text}

        safe_print("  Video bytes transferred successfully")

        # Step 3: Finish and Publish
        publish_url = f"{GRAPH_URL}/{page_id}/video_reels"
        publish_data = {
            'upload_phase': 'finish',
            'video_id': video_id,
            'access_token': page_token,
            'description': caption,
            'video_state': 'PUBLISHED'
        }
        resp = requests.post(publish_url, data=publish_data, timeout=30)
        if resp.status_code != 200:
            safe_print(f"  [ERROR] Publish failed ({resp.status_code}): {resp.text}")
            return {'status': 'failed', 'platform': 'facebook', 'page_id': page_id, 'error': resp.text}

        safe_print(f"  Reel published: https://facebook.com/{page_id}/reels/{video_id}")

        # Step 4: Post pinned comment
        comment_id = None
        if pin_comment:
            target_comment = comment_text if comment_text else caption
            comment_id = post_pinned_comment(video_id, target_comment, page_token)

        return {
            'status': 'success',
            'platform': 'facebook',
            'page_id': page_id,
            'video_id': video_id,
            'comment_id': comment_id
        }
    except Exception as e:
        safe_print(f"  [ERROR] upload_reel exception: {e}")
        return {'status': 'failed', 'platform': 'facebook', 'page_id': page_id, 'error': str(e)}


def upload_story(video_path, page_id=None, page_token=None):
    """
    Uploads video as a Facebook Story.
    """
    page_id = page_id or os.environ.get('FB_PAGE_ID') or os.environ.get('FACEBOOK_PAGE_ID', '')
    page_token = page_token or os.environ.get('FB_PAGE_ACCESS_TOKEN') or os.environ.get('FACEBOOK_ACCESS_TOKEN') or os.environ.get('FB_ACCESS_TOKEN', '')

    if not page_token or not page_id:
        safe_print(f"[SKIP] Facebook credentials not set for story (Page: {page_id})")
        return {'status': 'skipped', 'platform': 'facebook_story', 'page_id': page_id}

    if not os.path.exists(video_path):
        safe_print(f"[ERROR] Video not found: {video_path}")
        return {'status': 'failed', 'platform': 'facebook_story', 'page_id': page_id}

    file_size = os.path.getsize(video_path)
    safe_print(f"[FB] Uploading story to Page ({page_id}): {os.path.basename(video_path)} ({file_size / 1024 / 1024:.1f}MB)")

    try:
        # Step 1: Create story container
        init_url = f"{GRAPH_URL}/{page_id}/video_stories"
        init_data = {
            'upload_phase': 'start',
            'access_token': page_token
        }
        resp = requests.post(init_url, data=init_data, timeout=30)
        if resp.status_code != 200:
            safe_print(f"  [ERROR] Story init failed ({resp.status_code}): {resp.text}")
            return {'status': 'failed', 'platform': 'facebook_story', 'page_id': page_id}

        res_json = resp.json()
        video_id = res_json.get('video_id')
        upload_url = res_json.get('upload_url')
        if not video_id or not upload_url:
            safe_print(f"  [ERROR] No story video_id: {res_json}")
            return {'status': 'failed', 'platform': 'facebook_story', 'page_id': page_id}

        safe_print(f"  Story container created: {video_id}")

        # Step 2: Transfer video bytes
        with open(video_path, 'rb') as f:
            video_data = f.read()

        transfer_headers = {
            'Authorization': f'OAuth {page_token}',
            'offset': '0',
            'file_size': str(file_size)
        }
        resp = requests.post(upload_url, headers=transfer_headers, data=video_data, timeout=120)
        if resp.status_code != 200:
            safe_print(f"  [ERROR] Story transfer failed ({resp.status_code}): {resp.text}")
            return {'status': 'failed', 'platform': 'facebook_story', 'page_id': page_id}

        safe_print("  Story bytes transferred")

        # Step 3: Publish story
        publish_url = f"{GRAPH_URL}/{page_id}/video_stories"
        publish_data = {
            'upload_phase': 'finish',
            'video_id': video_id,
            'access_token': page_token
        }
        resp = requests.post(publish_url, data=publish_data, timeout=30)
        if resp.status_code != 200:
            safe_print(f"  [ERROR] Story publish failed ({resp.status_code}): {resp.text}")
            return {'status': 'failed', 'platform': 'facebook_story', 'page_id': page_id}

        safe_print("  Story published successfully")
        return {'status': 'success', 'platform': 'facebook_story', 'page_id': page_id}
    except Exception as e:
        safe_print(f"  [ERROR] upload_story exception: {e}")
        return {'status': 'failed', 'platform': 'facebook_story', 'page_id': page_id, 'error': str(e)}


def upload_to_facebook(video_path, description, title="Video", thumbnail_path=None, page_id=None, access_token=None):
    """
    Direct multipart POST upload to Meta Graph Video API endpoint (/videos).
    Publishes to Facebook Page Feed.
    """
    access_token = access_token or os.getenv("FB_PAGE_ACCESS_TOKEN") or os.getenv("FACEBOOK_ACCESS_TOKEN") or os.getenv("FB_ACCESS_TOKEN")
    page_id = page_id or os.getenv("FB_PAGE_ID") or os.getenv("FACEBOOK_PAGE_ID")

    if not access_token or not page_id:
        safe_print("[Facebook] Notice: Access token or Page ID not set. Skipping upload.")
        return None

    video_file = Path(video_path)
    if not video_file.exists():
        safe_print(f"[Facebook] Error: Video file not found: {video_path}")
        return None

    file_size_mb = video_file.stat().st_size / (1024 * 1024)

    safe_print("\n" + "=" * 60)
    safe_print("FACEBOOK VIDEO PUBLISH (FEED DIRECT)")
    safe_print("=" * 60)
    safe_print(f"[Facebook] Page ID: {page_id}")
    safe_print(f"[Facebook] Video: {video_file.name} ({file_size_mb:.2f} MB)")
    safe_print(f"[Facebook] Title: {str(title)[:70]}")
    safe_print(f"[Facebook] Description length: {len(str(description))} chars")

    upload_url = f"https://graph-video.facebook.com/v21.0/{page_id}/videos"

    data = {
        "title": str(title)[:100],
        "description": str(description)[:5000],
        "published": "true",
        "access_token": access_token
    }

    video_fp = None
    thumb_fp = None

    try:
        video_fp = open(video_file, "rb")
        files = {
            "source": (video_file.name, video_fp, "video/mp4")
        }

        # Attach thumbnail if available
        if thumbnail_path and Path(thumbnail_path).exists():
            try:
                thumb_fp = open(thumbnail_path, "rb")
                files["thumb"] = (Path(thumbnail_path).name, thumb_fp, "image/jpeg")
            except Exception as te:
                safe_print(f"[Facebook] Notice reading thumbnail: {te}")

        safe_print("[Facebook] Sending multipart POST request...")
        res = requests.post(upload_url, data=data, files=files, timeout=600)

        if res.status_code in [200, 201]:
            res_data = res.json()
            video_id = res_data.get("id") or res_data.get("video_id")
            if video_id:
                safe_print("\n" + "=" * 60)
                safe_print("SUCCESS: FACEBOOK VIDEO PUBLISHED!")
                safe_print(f"[Facebook] Video ID: {video_id}")
                safe_print(f"[Facebook] Video URL: https://www.facebook.com/{video_id}")
                safe_print("=" * 60)
                return {
                    "id": str(video_id),
                    "video_id": str(video_id),
                    "platform": "facebook",
                    "status": "success",
                    "url": f"https://www.facebook.com/{video_id}",
                    "published_at": datetime.now().isoformat()
                }

        safe_print(f"[Facebook] API Response ({res.status_code}): {res.text[:400]}")
        return None

    except requests.exceptions.Timeout:
        safe_print("[Facebook] Error: Upload request timed out.")
        return None
    except Exception as e:
        safe_print(f"[Facebook] Error during upload: {e}")
        return None
    finally:
        if video_fp:
            try:
                video_fp.close()
            except Exception:
                pass
        if thumb_fp:
            try:
                thumb_fp.close()
            except Exception:
                pass


if __name__ == "__main__":
    test_file = Path("final_video.mp4")
    if test_file.exists():
        upload_to_facebook(str(test_file), "Daily automated post", "Daily Video")
