import os
import sys
import json
import random
import re
import urllib.parse
import requests
from upload.upload_facebook import upload_reel, upload_story
from upload.upload_instagram import upload_reel as ig_reel, get_connected_instagram_account

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PUBLISHED_FILE = 'published_videos.json'

INDUSTRY_PROFILES = {
    'law': {
        'name': 'Law Firms & Solo Attorneys',
        'hook': '⚖️ Lawyers: Stop losing high-value legal cases to missed phone calls!',
        'body': (
            "Over 68% of legal clients hire the first attorney who answers their call. "
            "RecepZo provides a dedicated 24/7 AI Phone Receptionist that answers instantly on the 1st ring, "
            "conducts preliminary client intake, screens case details, and books consultations directly on your calendar."
        ),
        'keywords': ['virtual receptionist for law firms', 'legal intake automation', 'law firm phone answering', 'after hours attorney calls', 'legal tech'],
        'hashtags': ['#LawFirmMarketing', '#LegalTech', '#SoloAttorney', '#LawPractice', '#AIReceptionist', '#VirtualReceptionist', '#RecepZo', '#LegalIntake']
    },
    'dental': {
        'name': 'Dental Practices & Orthodontics',
        'hook': '🦷 Dentists: Are after-hours missed calls costing your clinic thousands in patient revenue?',
        'body': (
            "Patients experiencing tooth pain or needing cleanings won't leave voicemails—they call the next practice on Google. "
            "RecepZo AI answers 24/7, schedules dental appointments, handles routine clinic FAQs, and escalates emergency dental calls."
        ),
        'keywords': ['dental receptionist', 'dentist appointment booking', 'after hours patient answering', 'dental office automation', 'clinic management'],
        'hashtags': ['#DentalOffice', '#DentistLife', '#DentalMarketing', '#ClinicManagement', '#AIReceptionist', '#RecepZo', '#DentalCare']
    },
    'medspa': {
        'name': 'Med Spas & Aesthetics Clinics',
        'hook': '✨ Med Spas: Never miss a high-ticket consultation booking again!',
        'body': (
            "Prospective aesthetic clients call after work hours. If no one answers, they book elsewhere. "
            "RecepZo AI answers instantly, answers treatment questions about Botox, fillers, and lasers, and locks in consultation bookings."
        ),
        'keywords': ['med spa phone answering', 'aesthetic clinic receptionist', 'botox consultation booking', 'after hours patient answering', 'med spa marketing'],
        'hashtags': ['#MedSpaBusiness', '#AestheticsClinic', '#SpaOwner', '#ClinicMarketing', '#AIReceptionist', '#RecepZo', '#BotoxBooking']
    },
    'auto': {
        'name': 'Auto Repair Shops & Mechanics',
        'hook': '🔧 Mechanics: Stop dropping your tools to answer quote calls all day!',
        'body': (
            "When your hands are covered in grease, answering the phone is impossible. But missed calls mean missed repair jobs. "
            "RecepZo AI answers 24/7 on the 1st ring, collects vehicle make/model details, provides basic estimates, and schedules service drop-offs."
        ),
        'keywords': ['auto repair shop answering service', 'mechanic phone answering', 'automotive shop receptionist', 'quote request phone agent', 'auto shop management'],
        'hashtags': ['#AutoRepairShop', '#MechanicLife', '#AutoShopOwner', '#ShopManagement', '#AIReceptionist', '#RecepZo', '#AutoRepair']
    },
    'hvac': {
        'name': 'HVAC, Plumbing & Home Service Contractors',
        'hook': '❄️ Contractors: Capture high-ticket emergency calls even while on a roof or asleep!',
        'body': (
            "When a furnace breaks or a pipe bursts at 11 PM, the homeowner calls until someone answers. "
            "RecepZo AI phone receptionist answers immediately, collects address and emergency details, and routes jobs straight to your field dispatch."
        ),
        'keywords': ['contractor answering service', 'HVAC phone answering', 'plumber emergency dispatch', 'field service receptionist', 'contractor leads'],
        'hashtags': ['#HVACContractor', '#PlumbingBusiness', '#ContractorLife', '#HomeServices', '#AIReceptionist', '#RecepZo', '#FieldService']
    },
    'realestate': {
        'name': 'Real Estate Agents & Property Managers',
        'hook': '🏡 Realtors: Lock in prospective buyer inquiries and property tours 24/7!',
        'body': (
            "Sign calls and Zillow leads demand instant responses. "
            "RecepZo AI answers every inbound property inquiry within 1 ring, collects buyer/renter qualifications, and schedules viewing walkthroughs."
        ),
        'keywords': ['AI receptionist for real estate', 'realtor phone answering', 'property management answering', 'lead qualification agent', 'real estate tech'],
        'hashtags': ['#RealEstateAgent', '#RealtorMarketing', '#PropertyManagement', '#RealEstateTech', '#AIReceptionist', '#RecepZo', '#RealtorLife']
    },
    'general': {
        'name': 'Small Businesses & Service Teams',
        'hook': '📞 Over 67% of callers hang up if they reach voicemail! Stop losing revenue.',
        'body': (
            "Every missed call is a customer walking straight to your competitor. "
            "RecepZo gives your business full front-desk coverage 24/7/365 without the $40,000 receptionist salary. "
            "It answers on the 1st ring, schedules appointments, answers questions, and never takes a sick day."
        ),
        'keywords': ['AI phone receptionist', 'virtual receptionist for small business', '24/7 call answering service', 'never miss a customer call', 'front desk automation'],
        'hashtags': ['#AIReceptionist', '#VirtualReceptionist', '#PhoneAnsweringService', '#NeverMissACall', '#SmallBusinessOwner', '#RecepZo', '#BusinessAutomation']
    }
}

def load_published():
    if os.path.exists(PUBLISHED_FILE):
        try:
            with open(PUBLISHED_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_published(data):
    with open(PUBLISHED_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def detect_industry(filename):
    fn = filename.lower()
    if any(k in fn for k in ['law', 'attorney', 'legal', 'lawyer']):
        return 'law'
    if any(k in fn for k in ['dent', 'teeth', 'tooth']):
        return 'dental'
    if any(k in fn for k in ['medspa', 'spa', 'clinic', 'botox', 'doctor', 'aesthetic']):
        return 'medspa'
    if any(k in fn for k in ['auto', 'mechanic', 'repair', 'car', 'garage']):
        return 'auto'
    if any(k in fn for k in ['hvac', 'plumb', 'pipe', 'roof', 'electric', 'contractor']):
        return 'hvac'
    if any(k in fn for k in ['realestate', 'realtor', 'property', 'house', 'agent']):
        return 'realestate'
    return 'general'

def extract_subject_from_filename(filename):
    name = os.path.splitext(filename)[0]
    name = re.sub(r'_\d{8,}', '', name)
    name = re.sub(r'\d+', '', name)
    name = name.replace('_', ' ').replace('-', ' ').strip()
    return name or "AI receptionist business phone answering"

def generate_seo_title(filename, industry_key):
    profile = INDUSTRY_PROFILES.get(industry_key, INDUSTRY_PROFILES['general'])
    options = [
        f"24/7 AI Receptionist for {profile['name']}: Never Miss a Call | RecepZo",
        f"How {profile['name']} Automate 24/7 Phone Answering & Bookings | RecepZo",
        f"AI Phone Receptionist for {profile['name']}: Answers on 1st Ring | RecepZo",
        f"Stop Losing Customers to Voicemail: 24/7 AI Answering for {profile['name']}"
    ]
    return random.choice(options)[:80]

def format_seo_caption(hook, body, industry_key):
    profile = INDUSTRY_PROFILES.get(industry_key, INDUSTRY_PROFILES['general'])
    kw_str = ", ".join(profile['keywords'])
    ht_str = " ".join(profile['hashtags'])
    
    caption = (
        f"{hook}\n\n"
        f"{body}\n\n"
        f"Why Businesses Choose RecepZo AI:\n"
        f"✅ 24/7/365 Coverage: Answers every call on the 1st ring\n"
        f"✅ Automated Bookings: Syncs directly to your calendar\n"
        f"✅ Lead Qualification: Collects details & handles FAQs\n"
        f"✅ Keep Your Number: Seamless call forwarding setup\n\n"
        f"🔗 Try it free today: https://recepzo.com (Link in bio!)\n"
        f"👉 Never lose another customer: recepzo.com\n\n"
        f"Search keywords: {kw_str}\n\n"
        f"{ht_str}"
    )
    return caption

def clean_caption_text(text):
    if not text:
        return None
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    clean_lines = []
    for l in lines:
        if re.search(r'^(role\s*:|reasoning|thought|thinking|here is|here\'s|note:)', l, re.IGNORECASE):
            continue
        clean_lines.append(l)
    text = '\n\n'.join(clean_lines)
    text = re.sub(r'\*\*(title|caption|description|hashtags)[^\*]*\*\*[:\s]*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(title|caption|description|hashtags)\s*:\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'(Support\s+Pollinations|Powered\s+by\s+Pollinations|🌸\s*Ad\s*🌸).*$', '', text, flags=re.IGNORECASE | re.DOTALL).strip()
    text = text.replace('"', '').replace('“', '').replace('”', '').replace('*', '').strip()
    return text if len(text) > 30 else None

def generate_seo_content(filename=""):
    industry_key = detect_industry(filename)
    profile = INDUSTRY_PROFILES.get(industry_key, INDUSTRY_PROFILES['general'])
    title = generate_seo_title(filename, industry_key)

    pollinations_key = os.environ.get('POLLINATIONS_API_KEY', '').strip()
    subject = extract_subject_from_filename(filename)

    ai_generated_body = None
    if pollinations_key:
        prompt = (
            f"Write a high-converting, viral social media caption hook and explanation for RecepZo (recepzo.com). "
            f"Industry: {profile['name']}. Video subject: {subject}. "
            f"Explain how an AI receptionist answers phone calls on the 1st ring 24/7, books appointments, and eliminates missed leads. "
            f"Write 2 concise, compelling paragraphs. No hashtags, no role tags, no markdown titles."
        )
        for model in ['openai', 'mistral']:
            try:
                url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
                params = {'model': model, 'seed': random.randint(1, 999999)}
                headers = {'Authorization': f'Bearer {pollinations_key}'}
                resp = requests.get(url, params=params, headers=headers, timeout=12)
                if resp.status_code == 200:
                    cleaned = clean_caption_text(resp.text)
                    if cleaned and 'role assistant' not in cleaned.lower():
                        ai_generated_body = cleaned
                        break
            except Exception:
                continue

    if ai_generated_body:
        caption = (
            f"{profile['hook']}\n\n"
            f"{ai_generated_body}\n\n"
            f"Why Businesses Choose RecepZo AI:\n"
            f"✅ 24/7/365 Coverage: Answers every call on the 1st ring\n"
            f"✅ Automated Bookings: Syncs directly to your calendar\n"
            f"✅ Lead Qualification: Collects details & handles FAQs\n"
            f"✅ Keep Your Number: Seamless call forwarding setup\n\n"
            f"🔗 Try it free today: https://recepzo.com (Link in bio!)\n"
            f"👉 Never lose another customer: recepzo.com\n\n"
            f"Search keywords: {', '.join(profile['keywords'])}\n\n"
            f"{' '.join(profile['hashtags'])}"
        )
    else:
        caption = format_seo_caption(profile['hook'], profile['body'], industry_key)

    return title, caption, industry_key

def generate_pinned_comment(industry_key='general'):
    link = os.environ.get('PINNED_COMMENT_LINK', 'https://recepzo.com/').strip() or 'https://recepzo.com/'
    profile = INDUSTRY_PROFILES.get(industry_key, INDUSTRY_PROFILES['general'])

    return (
        f"📞 Never miss another customer call, lead, or appointment!\n\n"
        f"RecepZo provides a dedicated 24/7 AI Phone Receptionist for {profile['name']}:\n"
        f"✅ Zero hold times — answers on the 1st ring\n"
        f"✅ Direct calendar appointment scheduling\n"
        f"✅ Resolves caller FAQs, captures contact info & escalates emergencies\n"
        f"✅ Keeps your existing business phone number\n\n"
        f"👉 Get started free today: {link}"
    )

def select_video(video_list, published):
    published_names = {p.get('filename') for p in published}
    unpublished = [v for v in video_list if os.path.basename(v) not in published_names]

    if unpublished:
        return random.choice(unpublished)

    if video_list:
        counts = {}
        for p in published:
            name = p.get('filename', '')
            counts[name] = counts.get(name, 0) + 1

        weights = []
        for v in video_list:
            name = os.path.basename(v)
            count = counts.get(name, 0)
            weight = max(1, 1000 // (3 ** min(count, 6)))
            weights.append(weight)

        return random.choices(video_list, weights=weights, k=1)[0]

    return None

def resolve_target_pages():
    tokens_json_env = os.environ.get('FB_PAGE_TOKENS_JSON', '').strip()
    if tokens_json_env:
        try:
            tokens_data = json.loads(tokens_json_env)
            page_configs = []
            for pid, info in tokens_data.items():
                if isinstance(info, dict):
                    page_configs.append({
                        'id': str(pid),
                        'name': info.get('name', f'Page {pid}'),
                        'token': info.get('token')
                    })
                elif isinstance(info, str):
                    page_configs.append({
                        'id': str(pid),
                        'name': f'Page {pid}',
                        'token': info
                    })
            if page_configs:
                return page_configs
        except Exception as e:
            print(f"[WARN] Failed to parse FB_PAGE_TOKENS_JSON: {e}")

    single_page_id = os.environ.get('FB_PAGE_ID', '').strip()
    single_page_token = os.environ.get('FB_PAGE_ACCESS_TOKEN', '').strip()

    if single_page_id and single_page_token:
        return [{
            'id': single_page_id,
            'name': "Recepzo",
            'token': single_page_token
        }]

    return []

def publish_to_facebook_pages(video_path, title, caption, pinned_comment, page_configs):
    results = []
    print(f"\n[FB] Publishing to {len(page_configs)} Facebook Page(s)...")

    for p in page_configs:
        pid = p['id']
        pname = p.get('name', pid)
        token = p['token']
        print(f"\n--- Publishing to Facebook Page: {pname} (ID: {pid}) ---")

        # 1. Reel + Title + Pinned Comment
        reel_res = upload_reel(
            video_path=video_path,
            caption=caption,
            title=title,
            page_id=pid,
            page_token=token,
            pin_comment=True,
            comment_text=pinned_comment
        )
        reel_res['page_name'] = pname
        results.append(reel_res)

        # 2. Story
        story_res = upload_story(
            video_path=video_path,
            page_id=pid,
            page_token=token
        )
        story_res['page_name'] = pname
        results.append(story_res)

    return results

def publish(video_path, publish_to_facebook=True, publish_to_instagram=True):
    filename = os.path.basename(video_path)
    title, caption, industry_key = generate_seo_content(filename)
    pinned_comment = generate_pinned_comment(industry_key)

    print(f"\n[SEO TITLE] {title}")
    print(f"[SEO CAPTION]\n{caption}")
    print(f"[PINNED COMMENT]\n{pinned_comment}")

    results = []
    pages = []
    if publish_to_facebook or publish_to_instagram:
        pages = resolve_target_pages()

    if publish_to_facebook:
        if not pages:
            print("[WARN] No target Facebook pages resolved. Please configure FB_PAGE_ID + FB_PAGE_ACCESS_TOKEN.")
        else:
            fb_results = publish_to_facebook_pages(video_path, title, caption, pinned_comment, pages)
            results.extend(fb_results)

    if publish_to_instagram:
        ig_account_id = os.environ.get('INSTAGRAM_ACCOUNT_ID', '').strip()
        single_page_token = os.environ.get('FB_PAGE_ACCESS_TOKEN', '').strip()
        first_page_id = None

        if pages:
            if not single_page_token:
                single_page_token = pages[0].get('token', '')
            first_page_id = pages[0].get('id', '')
        else:
            first_page_id = os.environ.get('FB_PAGE_ID', '').strip()

        if not ig_account_id and first_page_id and single_page_token:
            auto_id, auto_username = get_connected_instagram_account(first_page_id, single_page_token)
            if auto_id:
                ig_account_id = str(auto_id)
                print(f"\n[IG AUTO-DETECT] Found linked Instagram Account: @{auto_username} (ID: {ig_account_id}) on Facebook Page {first_page_id}")

        if ig_account_id and single_page_token:
            share_to_feed = os.environ.get('IG_SHARE_TO_FEED', 'true').lower() in ('1', 'true', 'yes')
            print(f"\n[IG] Publishing Reel to Instagram Account: {ig_account_id} (share_to_feed={share_to_feed})")
            ig_res = ig_reel(
                video_path=video_path,
                caption=caption,
                page_token=single_page_token,
                ig_account_id=ig_account_id,
                share_to_feed=share_to_feed
            )
            results.append(ig_res)
        elif not ig_account_id:
            print("\n[INFO] Instagram publishing skipped: No Instagram Professional Account linked to Facebook Page.")
        elif not single_page_token:
            print("\n[SKIP] Facebook Page access token not found for Instagram.")

    return results

def run_daily_publish(processed_videos):
    published = load_published()
    video = select_video(processed_videos, published)

    if not video:
        print("[INFO] No videos available to publish")
        return []

    filename = os.path.basename(video)
    print(f"\n[SELECTED VIDEO] {filename}")

    results = publish(video, publish_to_facebook=True, publish_to_instagram=True)

    entry = {
        'filename': filename,
        'results': results
    }
    published.append(entry)
    save_published(published)

    return results

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    import glob
    processed = glob.glob('Processed_Videos/*.mp4') + glob.glob('Processed_Videos/*.mov')
    results = run_daily_publish(processed)
    print(f"\nPublish results total: {len(results)}")
