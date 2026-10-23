import os
import requests
import time
import subprocess

GRAPH_API_VERSION = 'v21.0'
GRAPH_URL = f'https://graph.facebook.com/{GRAPH_API_VERSION}'

def get_connected_instagram_account(page_id, page_token):
    """
    Auto-discovers the Instagram Professional Account connected to a Facebook Page.
    Returns (account_id, username) or (None, None).
    """
    if not page_id or not page_token:
        return None, None

    url = f"{GRAPH_URL}/{page_id}"
    params = {
        'fields': 'instagram_business_account{id,username,name},connected_instagram_account{id,username,name}',
        'access_token': page_token
    }
    try:
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            ig_bus = data.get('instagram_business_account')
            if ig_bus and ig_bus.get('id'):
                return ig_bus.get('id'), ig_bus.get('username') or ig_bus.get('name') or 'Instagram'
            ig_conn = data.get('connected_instagram_account')
            if ig_conn and ig_conn.get('id'):
                return ig_conn.get('id'), ig_conn.get('username') or ig_conn.get('name') or 'Instagram'
        else:
            print(f"  [DEBUG] Instagram detection response ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"  [WARN] Error querying connected Instagram account from Facebook Page: {e}")

    return None, None

def upload_reel(video_path, caption="", page_token=None, ig_account_id=None, share_to_feed=None):
    page_token = page_token or os.environ.get('FB_PAGE_ACCESS_TOKEN', '')
    ig_account_id = ig_account_id or os.environ.get('INSTAGRAM_ACCOUNT_ID', '')

    if not page_token or not ig_account_id:
        print("[SKIP] Instagram credentials not set (FB_PAGE_ACCESS_TOKEN or INSTAGRAM_ACCOUNT_ID missing)")
        return {'status': 'skipped', 'platform': 'instagram'}

    if not os.path.exists(video_path):
        print(f"[ERROR] Video not found: {video_path}")
        return {'status': 'failed', 'platform': 'instagram'}

    # Determine feed sharing: defaults to True (shared on grid and reels) unless disabled
    if share_to_feed is None:
        share_to_feed = os.environ.get('IG_SHARE_TO_FEED', 'true').lower() in ('1', 'true', 'yes')

    file_size = os.path.getsize(video_path)
    print(f"[IG] Uploading Reel: {os.path.basename(video_path)} ({file_size / 1024 / 1024:.1f}MB, share_to_feed={share_to_feed})")

    # Auto-compress if over 100MB while preserving audio specifications
    if file_size > 100 * 1024 * 1024:
        print("  Compressing video to fit under 100MB...")
        compressed_path = video_path.replace('.mp4', '_compressed.mp4')
        subprocess.run([
            'ffmpeg', '-y', '-i', video_path,
            '-c:v', 'libx264', '-crf', '28', '-preset', 'fast', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k', '-ar', '44100', '-ac', '2',
            '-fs', '95M',
            compressed_path
        ], capture_output=True)
        video_path = compressed_path
        file_size = os.path.getsize(video_path)

    # Step 1: Initialize Resumable Media Container
    feed_flag = 'true' if share_to_feed else 'false'
    audio_name = os.environ.get('IG_AUDIO_NAME', 'Original Audio')
    init_url = f"{GRAPH_URL}/{ig_account_id}/media"
    init_data = {
        'media_type': 'REELS',
        'upload_type': 'resumable',
        'caption': caption,
        'share_to_feed': feed_flag,
        'audio_name': audio_name,
        'access_token': page_token
    }
    init_params = {
        'share_to_feed': feed_flag
    }

    try:
        resp = requests.post(init_url, params=init_params, data=init_data, timeout=30)
    except Exception as e:
        print(f"  [ERROR] Container init request failed: {e}")
        return {'status': 'failed', 'platform': 'instagram'}

    if resp.status_code != 200:
        print(f"  [ERROR] Reel container creation failed ({resp.status_code}): {resp.text}")
        return {'status': 'failed', 'platform': 'instagram'}

    init_json = resp.json()
    container_id = init_json.get('id')
    upload_uri = init_json.get('uri') or f"https://rupload.facebook.com/ig-api-upload/{GRAPH_API_VERSION}/{container_id}"

    if not container_id:
        print(f"  [ERROR] No container ID in response: {init_json}")
        return {'status': 'failed', 'platform': 'instagram'}

    print(f"  Reel container initialized: {container_id}")

    # Step 2: Binary Video Upload to rupload.facebook.com
    upload_headers = {
        'Authorization': f'OAuth {page_token}',
        'offset': '0',
        'file_size': str(file_size),
        'Content-Type': 'application/octet-stream'
    }

    try:
        with open(video_path, 'rb') as f:
            upload_resp = requests.post(upload_uri, headers=upload_headers, data=f, timeout=180)
    except Exception as e:
        print(f"  [ERROR] Binary upload request failed: {e}")
        return {'status': 'failed', 'platform': 'instagram'}

    if upload_resp.status_code not in (200, 201):
        print(f"  [ERROR] Binary upload failed ({upload_resp.status_code}): {upload_resp.text}")
        return {'status': 'failed', 'platform': 'instagram'}

    print("  Binary video uploaded successfully. Polling processing status...")

    # Step 3: Wait for Meta processing
    for attempt in range(40):
        time.sleep(10)
        status_url = f"{GRAPH_URL}/{container_id}?fields=status_code,status&access_token={page_token}"
        try:
            status_resp = requests.get(status_url, timeout=30)
            if status_resp.status_code == 200:
                body = status_resp.json()
                status = body.get('status_code', '')
                if status == 'FINISHED':
                    print("  Processing complete!")
                    break
                elif status == 'ERROR':
                    print(f"  [ERROR] Media processing failed: {body}")
                    return {'status': 'failed', 'platform': 'instagram', 'error': body}
        except Exception as e:
            print(f"  [WARN] Status check transient error: {e}")
        print(f"  Processing Reel... ({attempt + 1}/40)")
    else:
        print("  [WARN] Processing timed out after 400 seconds.")

    # Step 4: Publish
    publish_url = f"{GRAPH_URL}/{ig_account_id}/media_publish"
    publish_data = {
        'creation_id': container_id,
        'access_token': page_token
    }

    try:
        resp = requests.post(publish_url, data=publish_data, timeout=30)
    except Exception as e:
        print(f"  [ERROR] Publish request failed: {e}")
        return {'status': 'failed', 'platform': 'instagram'}

    if resp.status_code != 200:
        print(f"  [ERROR] Publish failed ({resp.status_code}): {resp.text}")
        return {'status': 'failed', 'platform': 'instagram'}

    media_id = resp.json().get('id')
    print(f"  [SUCCESS] Reel published on Instagram: {media_id}")
    return {'status': 'success', 'platform': 'instagram', 'media_id': media_id}

def upload_story(video_path, page_token=None, ig_account_id=None):
    page_token = page_token or os.environ.get('FB_PAGE_ACCESS_TOKEN', '')
    ig_account_id = ig_account_id or os.environ.get('INSTAGRAM_ACCOUNT_ID', '')

    if not page_token or not ig_account_id:
        print("[SKIP] Instagram credentials not set (FB_PAGE_ACCESS_TOKEN or INSTAGRAM_ACCOUNT_ID missing)")
        return {'status': 'skipped', 'platform': 'instagram_story'}

    if not os.path.exists(video_path):
        print(f"[ERROR] Video not found: {video_path}")
        return {'status': 'failed', 'platform': 'instagram_story'}

    file_size = os.path.getsize(video_path)
    print(f"[IG] Uploading Story: {os.path.basename(video_path)} ({file_size / 1024 / 1024:.1f}MB)")

    # Step 1: Initialize Resumable Story Container
    init_url = f"{GRAPH_URL}/{ig_account_id}/media"
    init_data = {
        'media_type': 'STORIES',
        'upload_type': 'resumable',
        'access_token': page_token
    }

    try:
        resp = requests.post(init_url, data=init_data, timeout=30)
    except Exception as e:
        print(f"  [ERROR] Story init request failed: {e}")
        return {'status': 'failed', 'platform': 'instagram_story'}

    if resp.status_code != 200:
        print(f"  [ERROR] Story container failed ({resp.status_code}): {resp.text}")
        return {'status': 'failed', 'platform': 'instagram_story'}

    init_json = resp.json()
    container_id = init_json.get('id')
    upload_uri = init_json.get('uri') or f"https://rupload.facebook.com/ig-api-upload/{GRAPH_API_VERSION}/{container_id}"

    if not container_id:
        print(f"  [ERROR] No container ID: {init_json}")
        return {'status': 'failed', 'platform': 'instagram_story'}

    print(f"  Story container initialized: {container_id}")

    # Step 2: Binary Video Upload
    upload_headers = {
        'Authorization': f'OAuth {page_token}',
        'offset': '0',
        'file_size': str(file_size),
        'Content-Type': 'application/octet-stream'
    }

    try:
        with open(video_path, 'rb') as f:
            upload_resp = requests.post(upload_uri, headers=upload_headers, data=f, timeout=180)
    except Exception as e:
        print(f"  [ERROR] Story binary upload failed: {e}")
        return {'status': 'failed', 'platform': 'instagram_story'}

    if upload_resp.status_code not in (200, 201):
        print(f"  [ERROR] Story upload failed ({upload_resp.status_code}): {upload_resp.text}")
        return {'status': 'failed', 'platform': 'instagram_story'}

    print("  Binary video uploaded. Polling story processing status...")

    # Step 3: Wait for Meta processing
    for attempt in range(30):
        time.sleep(10)
        status_url = f"{GRAPH_URL}/{container_id}?fields=status_code,status&access_token={page_token}"
        try:
            status_resp = requests.get(status_url, timeout=30)
            if status_resp.status_code == 200:
                status = status_resp.json().get('status_code', '')
                if status == 'FINISHED':
                    print("  Story processing complete!")
                    break
                elif status == 'ERROR':
                    print(f"  [ERROR] Story processing failed: {status_resp.json()}")
                    return {'status': 'failed', 'platform': 'instagram_story'}
        except Exception as e:
            print(f"  [WARN] Transient error checking status: {e}")
        print(f"  Processing Story... ({attempt + 1}/30)")

    # Step 4: Publish
    publish_url = f"{GRAPH_URL}/{ig_account_id}/media_publish"
    publish_data = {
        'creation_id': container_id,
        'access_token': page_token
    }

    try:
        resp = requests.post(publish_url, data=publish_data, timeout=30)
    except Exception as e:
        print(f"  [ERROR] Story publish request failed: {e}")
        return {'status': 'failed', 'platform': 'instagram_story'}

    if resp.status_code != 200:
        print(f"  [ERROR] Story publish failed ({resp.status_code}): {resp.text}")
        return {'status': 'failed', 'platform': 'instagram_story'}

    media_id = resp.json().get('id')
    print(f"  [SUCCESS] Story published on Instagram: {media_id}")
    return {'status': 'success', 'platform': 'instagram_story', 'media_id': media_id}
