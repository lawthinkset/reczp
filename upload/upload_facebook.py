import os
import sys
import requests
import json
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

GRAPH_API_VERSION = 'v21.0'
GRAPH_URL = f'https://graph.facebook.com/{GRAPH_API_VERSION}'

def post_pinned_comment(video_id, comment_text, page_token, max_retries=3, delay_seconds=8):
    """
    Posts the first comment on the Reel video and attempts to pin it.
    """
    if not comment_text or not video_id:
        return None

    print(f"  [FB] Waiting {delay_seconds}s for video processing before commenting...")
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
                print(f"  [FB] Comment posted successfully: {comment_id}")
                break
            else:
                print(f"  [WARN] Comment attempt {attempt} failed ({resp.status_code}): {resp.text}")
                if attempt < max_retries:
                    time.sleep(5)
        except Exception as e:
            print(f"  [WARN] Comment attempt {attempt} error: {e}")
            if attempt < max_retries:
                time.sleep(5)

    if not comment_id:
        print("  [WARN] Could not post comment after retries")
        return None

    try:
        pin_url = f"{GRAPH_URL}/{comment_id}"
        pin_resp = requests.post(
            pin_url,
            data={'is_pinned': 'true', 'access_token': page_token},
            timeout=15
        )
        if pin_resp.status_code == 200:
            print(f"  [FB] Comment pinned successfully!")
        else:
            print("  [INFO] Comment is placed as top Page comment.")
    except Exception:
        pass

    return comment_id

def upload_reel(video_path, caption="", page_id=None, page_token=None, pin_comment=True, comment_text=None):
    page_id = page_id or os.environ.get('FB_PAGE_ID', '')
    page_token = page_token or os.environ.get('FB_PAGE_ACCESS_TOKEN', '')

    if not page_token or not page_id:
        print(f"[SKIP] Facebook credentials not set for page ID: {page_id}")
        return {'status': 'skipped', 'platform': 'facebook', 'page_id': page_id}

    if not os.path.exists(video_path):
        print(f"[ERROR] Video not found: {video_path}")
        return {'status': 'failed', 'platform': 'facebook', 'page_id': page_id}

    file_size = os.path.getsize(video_path)
    print(f"[FB] Uploading reel to Kathy's Guitar ({page_id}): {os.path.basename(video_path)} ({file_size / 1024 / 1024:.1f}MB)")

    # Step 1: Create video container
    init_url = f"{GRAPH_URL}/{page_id}/video_reels"
    init_data = {
        'upload_phase': 'start',
        'access_token': page_token
    }
    resp = requests.post(init_url, data=init_data, timeout=30)
    if resp.status_code != 200:
        print(f"  [ERROR] Init failed: {resp.text}")
        return {'status': 'failed', 'platform': 'facebook', 'page_id': page_id, 'error': resp.text}

    video_id = resp.json().get('video_id')
    upload_url = resp.json().get('upload_url')
    if not video_id or not upload_url:
        print(f"  [ERROR] No video_id or upload_url returned: {resp.json()}")
        return {'status': 'failed', 'platform': 'facebook', 'page_id': page_id}

    print(f"  Container created: {video_id}")

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
        print(f"  [ERROR] Transfer failed: {resp.text}")
        return {'status': 'failed', 'platform': 'facebook', 'page_id': page_id, 'error': resp.text}

    print("  Video bytes transferred successfully")

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
        print(f"  [ERROR] Publish failed: {resp.text}")
        return {'status': 'failed', 'platform': 'facebook', 'page_id': page_id, 'error': resp.text}

    print(f"  Reel published: https://facebook.com/{page_id}/reels/{video_id}")

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

def upload_story(video_path, page_id=None, page_token=None):
    page_id = page_id or os.environ.get('FB_PAGE_ID', '')
    page_token = page_token or os.environ.get('FB_PAGE_ACCESS_TOKEN', '')

    if not page_token or not page_id:
        print(f"[SKIP] Facebook credentials not set for story (Page: {page_id})")
        return {'status': 'skipped', 'platform': 'facebook_story', 'page_id': page_id}

    if not os.path.exists(video_path):
        print(f"[ERROR] Video not found: {video_path}")
        return {'status': 'failed', 'platform': 'facebook_story', 'page_id': page_id}

    file_size = os.path.getsize(video_path)
    print(f"[FB] Uploading story to Kathy's Guitar ({page_id}): {os.path.basename(video_path)} ({file_size / 1024 / 1024:.1f}MB)")

    # Step 1: Create story container
    init_url = f"{GRAPH_URL}/{page_id}/video_stories"
    init_data = {
        'upload_phase': 'start',
        'access_token': page_token
    }
    resp = requests.post(init_url, data=init_data, timeout=30)
    if resp.status_code != 200:
        print(f"  [ERROR] Story init failed: {resp.text}")
        return {'status': 'failed', 'platform': 'facebook_story', 'page_id': page_id}

    video_id = resp.json().get('video_id')
    upload_url = resp.json().get('upload_url')
    if not video_id or not upload_url:
        print(f"  [ERROR] No story video_id: {resp.json()}")
        return {'status': 'failed', 'platform': 'facebook_story', 'page_id': page_id}

    print(f"  Story container created: {video_id}")

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
        print(f"  [ERROR] Story transfer failed: {resp.text}")
        return {'status': 'failed', 'platform': 'facebook_story', 'page_id': page_id}

    print("  Story bytes transferred")

    # Step 3: Publish story
    publish_url = f"{GRAPH_URL}/{page_id}/video_stories"
    publish_data = {
        'upload_phase': 'finish',
        'video_id': video_id,
        'access_token': page_token
    }
    resp = requests.post(publish_url, data=publish_data, timeout=30)
    if resp.status_code != 200:
        print(f"  [ERROR] Story publish failed: {resp.text}")
        return {'status': 'failed', 'platform': 'facebook_story', 'page_id': page_id}

    print("  Story published successfully")
    return {'status': 'success', 'platform': 'facebook_story', 'page_id': page_id}
