import streamlit as st
import base64
import re
import json
import os
import time
import tempfile
import numpy as np
import io
import requests
import shutil
from PIL import Image
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, VideoFileClip, CompositeVideoClip, ColorClip, CompositeAudioClip, concatenate_audioclips, vfx
from docx import Document
from google import genai
from google.genai import types

# --- إعدادات الواجهة ---
st.set_page_config(page_title="AI Studio Pro: Darija & Amazigh", page_icon="🎬", layout="wide")
st.title("🎬 استوديو الذكاء الاصطناعي الاحترافي")

# --- المفاتيح المحفوظة (Defaults) ---
DEFAULT_PIXABAY_API_KEY = "58178676-7dca3797f2ac366b67263077a"
DEFAULT_ACESTEP_API_KEY = "821f692a10974eaa960316f37a9001f6"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"

FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-1.5-flash-latest"]

# --- إعدادات الحفظ الدائم ---
DATA_DIR = "persistent_data"
AUDIO_DIR = os.path.join(DATA_DIR, "audios")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
if not os.path.exists(AUDIO_DIR): os.makedirs(AUDIO_DIR)

def load_persistent_data():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            st.session_state.script_data = data.get("script_data")
            st.session_state.last_custom_script = data.get("last_custom_script", "")
            st.session_state.saved_api_key = data.get("gemini_api_key", "")
            st.session_state.acestep_api_key = data.get("acestep_api_key", DEFAULT_ACESTEP_API_KEY)
            st.session_state.pixabay_api_key = data.get("pixabay_api_key", DEFAULT_PIXABAY_API_KEY)
            st.session_state.gemini_model = data.get("gemini_model", DEFAULT_GEMINI_MODEL)
            st.session_state.aspect_ratio = data.get("aspect_ratio", "9:16 (ريلز/تيك توك)")
            st.session_state.quality = data.get("quality", "1080p")
            st.session_state.max_duration = data.get("max_duration", 120)
            st.session_state.language = data.get("language", "الدارجة المغربية")
            st.session_state.tone = data.get("tone", "الكوميدية")
            
            st.session_state.current_step = data.get("current_step", 1)
            st.session_state.scene_assets = data.get("scene_assets", {})
            st.session_state.voice_mode = data.get("voice_mode", "توليد الصوت بالذكاء الاصطناعي (لكل مشهد)")
            
            main_audio_path = os.path.join(AUDIO_DIR, "main_voice.wav")
            if os.path.exists(main_audio_path):
                with open(main_audio_path, "rb") as f:
                    st.session_state.full_audio_bytes = f.read()
            else:
                st.session_state.full_audio_bytes = None
                
            music_path = os.path.join(AUDIO_DIR, "background_music.mp3")
            if os.path.exists(music_path):
                with open(music_path, "rb") as f:
                    st.session_state.background_music_bytes = f.read()
            else:
                st.session_state.background_music_bytes = None
        except Exception:
            pass

def save_persistent_data():
    try:
        data = {
            "script_data": st.session_state.script_data,
            "last_custom_script": st.session_state.last_custom_script,
            "gemini_api_key": st.session_state.get("gemini_api_key_input", ""),
            "acestep_api_key": st.session_state.get("acestep_api_key_input", DEFAULT_ACESTEP_API_KEY),
            "pixabay_api_key": st.session_state.get("pixabay_api_key_input", DEFAULT_PIXABAY_API_KEY),
            "gemini_model": st.session_state.get("gemini_model_input", DEFAULT_GEMINI_MODEL),
            "aspect_ratio": st.session_state.get("aspect_ratio_input", "9:16 (ريلز/تيك توك)"),
            "quality": st.session_state.get("quality_input", "1080p"),
            "max_duration": st.session_state.get("max_duration_input", 120),
            "language": st.session_state.get("language_input", "الدارجة المغربية"),
            "tone": st.session_state.get("tone_input", "الكوميدية"),
            "current_step": st.session_state.get("current_step", 1),
            "scene_assets": st.session_state.get("scene_assets", {}),
            "voice_mode": st.session_state.get("voice_mode", "توليد الصوت بالذكاء الاصطناعي (لكل مشهد)")
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        if st.session_state.full_audio_bytes:
            with open(os.path.join(AUDIO_DIR, "main_voice.wav"), "wb") as f:
                f.write(st.session_state.full_audio_bytes)
        if st.session_state.background_music_bytes:
            with open(os.path.join(AUDIO_DIR, "background_music.mp3"), "wb") as f:
                f.write(st.session_state.background_music_bytes)
    except Exception:
        pass

def clear_all_data():
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    st.session_state.clear()
    st.rerun()

# --- تهيئة الذاكرة ---
if 'script_data' not in st.session_state: st.session_state.script_data = None
if 'full_audio_bytes' not in st.session_state: st.session_state.full_audio_bytes = None
if 'background_music_bytes' not in st.session_state: st.session_state.background_music_bytes = None
if 'last_custom_script' not in st.session_state: st.session_state.last_custom_script = ""
if 'saved_api_key' not in st.session_state: st.session_state.saved_api_key = ""
if 'acestep_api_key' not in st.session_state: st.session_state.acestep_api_key = DEFAULT_ACESTEP_API_KEY
if 'pixabay_api_key' not in st.session_state: st.session_state.pixabay_api_key = DEFAULT_PIXABAY_API_KEY
if 'gemini_model' not in st.session_state: st.session_state.gemini_model = DEFAULT_GEMINI_MODEL
if 'aspect_ratio' not in st.session_state: st.session_state.aspect_ratio = "9:16 (ريلز/تيك توك)"
if 'quality' not in st.session_state: st.session_state.quality = "1080p"
if 'max_duration' not in st.session_state: st.session_state.max_duration = 120
if 'language' not in st.session_state: st.session_state.language = "الدارجة المغربية"
if 'tone' not in st.session_state: st.session_state.tone = "الكوميدية"
if 'current_step' not in st.session_state: st.session_state.current_step = 1
if 'scene_assets' not in st.session_state: st.session_state.scene_assets = {}
if 'voice_mode' not in st.session_state: st.session_state.voice_mode = "توليد الصوت بالذكاء الاصطناعي (لكل مشهد)"

if not st.session_state.get('data_loaded', False):
    load_persistent_data()
    st.session_state.data_loaded = True

# --- دوال مساعدة ---
def search_pixabay_videos(query, api_key, per_page=3):
    if not api_key: return None
    url = "https://pixabay.com/api/videos/"
    params = {"key": api_key, "q": query, "per_page": per_page, "video_type": "film", "safesearch": "true"}
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        hits = res.json().get('hits', [])
        if hits:
            hit = hits[0]
            preview_url = hit['videos'].get('tiny', {}).get('url') or hit['videos'].get('small', {}).get('url') or hit['videos'].get('medium', {}).get('url')
            download_url = hit['videos'].get('medium', {}).get('url') or hit['videos'].get('large', {}).get('url')
            if preview_url and download_url:
                return {"preview_url": preview_url, "download_url": download_url, "source": "Pixabay"}
    except Exception:
        pass
    return None

def search_coverr_videos(query, per_page=1):
    url = "https://api.coverr.co/videos"
    params = {"query": query, "page_size": per_page}
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        hits = res.json().get('hits', [])
        if hits:
            urls = hits[0].get('urls', {})
            preview_url = urls.get('mp4_720') or urls.get('mp4_1080') or urls.get('mp4_download')
            download_url = urls.get('mp4_1080') or urls.get('mp4_download')
            if preview_url and download_url:
                return {"preview_url": preview_url, "download_url": download_url, "source": "Coverr"}
    except Exception:
        pass
    return None

def search_sfxmint(query):
    if not query or str(query).lower() in ['n/a', 'none', 'null', '']: query = "cinematic"
    url = "https://sfxmint.com/api/v1/search"
    params = {"q": query, "limit": 1}
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        results = data.get('results', []) if isinstance(data, dict) else data if isinstance(data, list) else []
        if results:
            first = results[0]
            return first.get('audio_url') if isinstance(first, dict) else first if isinstance(first, str) else None
    except Exception:
        pass
    return None

def generate_audio_with_retry(client, model_name, prompt, voice_name, max_retries=3):
    for attempt in range(max_retries):
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)))
                )
            )
            return res
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_time = 10 * (attempt + 1)
                st.warning(f"⚠️ تم الوصول للحد الأقصى للطلبات. جاري إعادة المحاولة بعد {wait_time} ثانية...")
                time.sleep(wait_time)
            else:
                raise e
    raise Exception("فشلت جميع محاولات توليد الصوت.")

# --- الشريط الجانبي ---
with st.sidebar:
    st.header(":material/settings: الإعدادات العامة")
    gemini_api_key = st.text_input("1. Google Gemini API Key:", value=st.session_state.saved_api_key, type="password", key="gemini_api_key_input")
    gemini_model_input = st.text_input("2. Gemini Model Name:", value=st.session_state.gemini_model, key="gemini_model_input")
    if not gemini_model_input.strip(): gemini_model_input = DEFAULT_GEMINI_MODEL
    acestep_api_key = st.text_input("3. ACE Music API Key:", value=st.session_state.acestep_api_key, type="password", key="acestep_api_key_input")
    pixabay_api_key = st.text_input("4. Pixabay API Key:", value=st.session_state.pixabay_api_key, type="password", key="pixabay_api_key_input")
    
    st.markdown("---")
    st.subheader(":material/movie: إعدادات الفيديو")
    aspect_ratio = st.selectbox("أبعاد الفيديو:", ["9:16 (ريلز/تيك توك)", "16:9 (يوتيوب)", "1:1 (مربع)", "4:5 (إنستغرام)", "4:3 (كلاسيكي)"], index=["9:16 (ريلز/تيك توك)", "16:9 (يوتيوب)", "1:1 (مربع)", "4:5 (إنستغرام)", "4:3 (كلاسيكي)"].index(st.session_state.aspect_ratio) if st.session_state.aspect_ratio in ["9:16 (ريلز/تيك توك)", "16:9 (يوتيوب)", "1:1 (مربع)", "4:5 (إنستغرام)", "4:3 (كلاسيكي)"] else 0, key="aspect_ratio_input")
    quality = st.selectbox("جودة الفيديو:", ["1080p", "720p", "480p"], index=["1080p", "720p", "480p"].index(st.session_state.quality) if st.session_state.quality in ["1080p", "720p", "480p"] else 0, key="quality_input")
    max_duration = st.slider("المدة القصوى للفيديو (ثانية):", 10, 3600, st.session_state.max_duration, 10, key="max_duration_input")
    
    st.markdown("---")
    language_list = ["الدارجة المغربية", "الأمازيغية", "العربية الفصحى", "المصرية", "الخليجية", "السورية", "اللبنانية", "العراقية", "الأردنية", "الإماراتية", "السعودية", "التونسية", "الجزائرية", "الإنجليزية", "الفرنسية", "الإسبانية", "الألمانية", "التركية"]
    language = st.selectbox("اللغة/اللهجة:", language_list, index=language_list.index(st.session_state.language) if st.session_state.language in language_list else 0, key="language_input")
    tone_list = ["الكوميدية", "الأكشن والرسوم المتحركة", "الأفلام الموسيقية والرقص", "ما بعد الكارثة / النجاة المستقبلية", "الفانتازيا والأسطوريات", "الجريمة والسرقة", "التشويق", "الرعب", "الإثارة", "الدراما", "إعلاني (تجاري)"]
    tone = st.selectbox("الستايل (Tone):", tone_list, index=tone_list.index(st.session_state.tone) if st.session_state.tone in tone_list else 0, key="tone_input")
    
    st.markdown("---")
    if st.button(":material/delete: مسح كل البيانات والبدء من جديد", type="primary"):
        clear_all_data()
        
    save_persistent_data()

# --- عرض الخطوات (Workflow 5 Steps) ---
st.progress(st.session_state.current_step / 5)
st.write(f"**الخطوة {st.session_state.current_step} من 5**")

# ==========================================
# الخطوة 1: السيناريو
# ==========================================
if st.session_state.current_step == 1:
    st.header(":material/description: 1. توليد السيناريو")
    work_mode = st.radio("كيفاش بغيتي تخدم السيناريو؟", ["توليد سيناريو جديد", "لدي سيناريو جاهز (لصق)"], horizontal=True)
    
    if work_mode == "توليد سيناريو جديد":
        topic = st.text_area("فكرة الفيديو:", height=100)
        custom_script = ""
    else:
        custom_script = st.text_area("لصق السيناريو ديالك هنا:", height=150, value=st.session_state.last_custom_script)
        topic = ""

    if st.button(":material/rocket_launch: توليد/تحليل السيناريو", use_container_width=True, type="primary"):
        if not st.session_state.gemini_api_key_input:
            st.error("عافاك دخل Google Gemini API Key.")
        else:
            with st.spinner("جاري تحليل السيناريو واستخراج المؤثرات..."):
                try:
                    client = genai.Client(api_key=st.session_state.gemini_api_key_input)
                    prompt = f"""أنت كاتب سيناريوهات ومهندس صوت سينمائي. كتب سيناريو فيديو باللهجة {language} على {topic if topic else custom_script}.
                    
                    تحذير مهم جداً: فـ كل مشهد، خاصك تعمر خانة "search_keyword" بكلمات إنجليزية بسيطة جداً (من 1 إلى 3 كلمات فقط) تصف الفيديو بوضوح. ممنوع تكتب جمل طويلة.
                    أمثلة: "empty street", "water drop", "man walking", "dark room", "fire".
                    
                    رجع JSON فقط بهذا الهيكل:
                    {{"title":"عنوان", "scenes":[{{"scene_number":1, "location":"مكان", "visual_description":"وصف", "search_keyword":"simple english keywords", "sfx_keywords":["wind", "footsteps"], "dialogue":"الحوار"}}]}}"""
                    
                    response = client.models.generate_content(model=st.session_state.gemini_model, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
                    txt = response.text.strip().replace("```json", "").replace("```", "")
                    st.session_state.script_data = json.loads(txt)
                    st.session_state.scene_assets = {} 
                    st.success("✅ السيناريو جاهز!")
                except Exception as e:
                    st.error(f"خطأ: {e}")

    if st.session_state.script_data:
        st.subheader(f"🎬 {st.session_state.script_data.get('title')}")
        for scene in st.session_state.script_data.get('scenes', []):
            with st.expander(f":material/movie: المشهد {scene['scene_number']}"):
                st.write(f"**البحث:** {scene.get('search_keyword')}")
                st.write(f"**المؤثرات:** {', '.join(scene.get('sfx_keywords', []))}")
                st.write(f"**الحوار:** {scene['dialogue']}")
                
        if st.button(":material/arrow_forward: التالي: التعليق الصوتي", type="primary"):
            st.session_state.current_step = 2
            st.rerun()

# ==========================================
# الخطوة 2: التعليق الصوتي (توليد أو رفع)
# ==========================================
elif st.session_state.current_step == 2:
    st.header(":material/record_voice_over: 2. التعليق الصوتي")
    
    voice_mode = st.radio("🔊 طريقة الحصول على الصوت:", ["توليد الصوت بالذكاء الاصطناعي (لكل مشهد)", "رفع ملف صوتي جاهز (للتعليق كامل)"], horizontal=True)
    st.session_state.voice_mode = voice_mode
    
    if voice_mode == "توليد الصوت بالذكاء الاصطناعي (لكل مشهد)":
        st.info("غادي نولدوا صوت لكل مشهد بوحدو، هادشي غادي يضمن التزامن المثالي.")
        
        if st.button(":material/mic: توليد الأصوات", type="primary"):
            with st.spinner("جاري توليد الأصوات..."):
                try:
                    client = genai.Client(api_key=st.session_state.gemini_api_key_input)
                    for scene in st.session_state.script_data['scenes']:
                        scene_num = scene['scene_number']
                        if str(scene_num) not in st.session_state.scene_assets or 'audio_path' not in st.session_state.scene_assets[str(scene_num)]:
                            res = generate_audio_with_retry(
                                client=client,
                                model_name="gemini-3.8-flash-lite-tts",
                                prompt=f"اقرأ باللهجة {st.session_state.language}: {scene['dialogue']}",
                                voice_name="Fenrir"
                            )
                            
                            if res.candidates and res.candidates[0].content.parts and res.candidates[0].content.parts[0].inline_data:
                                audio_data = res.candidates[0].content.parts[0].inline_data.data
                                
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                                    tmp.write(audio_data)
                                    audio_path = tmp.name
                                    
                                st.session_state.scene_assets[str(scene_num)] = {
                                    **st.session_state.scene_assets.get(str(scene_num), {}),
                                    "audio_path": audio_path
                                }
                            else:
                                st.error(f"فشل توليد صوت المشهد {scene_num}. قد يكون النص فارغًا أو غير صالح.")
                                st.stop()
                    st.success("✅ الأصوات جاهزة!")
                except Exception as e:
                    st.error(f"خطأ: {e}")
                    
        if st.session_state.scene_assets:
            for scene in st.session_state.script_data['scenes']:
                scene_num = str(scene['scene_number'])
                if scene_num in st.session_state.scene_assets and 'audio_path' in st.session_state.scene_assets[scene_num]:
                    st.write(f"**المشهد {scene_num}:** {scene['dialogue']}")
                    st.audio(st.session_state.scene_assets[scene_num]['audio_path'])

    else:
        st.info("ارفع ملف صوتي كامل (MP3/WAV). غادي نقسمو الوقت على المشاهد بالتساوي.")
        uploaded_audio = st.file_uploader("ارفع ملف الصوت (MP3/WAV)", type=["mp3", "wav"])
        if uploaded_audio:
            st.session_state.full_audio_bytes = uploaded_audio.read()
            save_persistent_data()
            st.success("✅ تم رفع الصوت بنجاح!")
            st.audio(st.session_state.full_audio_bytes)

    col1, col2 = st.columns(2)
    with col1:
        if st.button(":material/arrow_back: السابق: السيناريو"):
            st.session_state.current_step = 1
            st.rerun()
    with col2:
        if st.button(":material/arrow_forward: التالي: المؤثرات الصوتية", type="primary"):
            st.session_state.current_step = 3
            st.rerun()

# ==========================================
# الخطوة 3: المؤثرات الصوتية (SFX)
# ==========================================
elif st.session_state.current_step == 3:
    st.header(":material/graphic_eq: 3. المؤثرات الصوتية (SFX)")
    st.info("الذكاء الاصطناعي كيجيب المؤثرات الصوتية المناسبة لكل مشهد. تقدر تسمعهم هنا قبل المونتاج.")
    
    if st.button(":material/search: جلب المؤثرات الصوتية", type="primary"):
        with st.spinner("جاري البحث عن المؤثرات الصوتية..."):
            for scene in st.session_state.script_data['scenes']:
                scene_num = str(scene['scene_number'])
                sfx_list = scene.get('sfx_keywords', [])
                
                if scene_num not in st.session_state.scene_assets:
                    st.session_state.scene_assets[scene_num] = {}
                
                scene_assets = st.session_state.scene_assets[scene_num]
                scene_assets['sfx_urls'] = []
                
                for sfx_kw in sfx_list:
                    sfx_url = search_sfxmint(sfx_kw)
                    if sfx_url:
                        scene_assets['sfx_urls'].append({"keyword": sfx_kw, "url": sfx_url})
            st.success("✅ تم جلب المؤثرات!")
            st.rerun()

    # عرض المؤثرات
    if st.session_state.scene_assets:
        for scene in st.session_state.script_data['scenes']:
            scene_num = str(scene['scene_number'])
            assets = st.session_state.scene_assets.get(scene_num, {})
            sfx_urls = assets.get('sfx_urls', [])
            
            if sfx_urls:
                st.subheader(f"المشهد {scene_num}")
                for sfx in sfx_urls:
                    st.write(f"🔊 {sfx['keyword']}")
                    st.audio(sfx['url'])

    col1, col2 = st.columns(2)
    with col1:
        if st.button(":material/arrow_back: السابق: التعليق الصوتي"):
            st.session_state.current_step = 2
            st.rerun()
    with col2:
        if st.button(":material/arrow_forward: التالي: الموسيقى", type="primary"):
            st.session_state.current_step = 4
            st.rerun()

# ==========================================
# الخطوة 4: الموسيقى
# ==========================================
elif st.session_state.current_step == 4:
    st.header(":material/music_note: 4. الموسيقى الخلفية")
    
    music_mode = st.radio("🎵 طريقة الحصول على الموسيقى:", ["توليد بالذكاء الاصطناعي (ACE Music)", "رفع ملف موسيقى جاهز"], horizontal=True)
    
    if music_mode == "توليد بالذكاء الاصطناعي (ACE Music)":
        music_prompt = st.text_area("وصف الموسيقى:", placeholder="مثال: a happy summer pop beat, uplifting synths")
        if st.button(":material/auto_awesome: توليد الموسيقى", type="primary"):
            with st.spinner("جاري توليد الموسيقى..."):
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.acestep_api_key}", "Content-Type": "application/json"}
                    payload = {"prompt": music_prompt, "duration": 60, "task_type": "text2music"}
                    
                    res = requests.post("https://api.acemusic.ai/v1/music/generate", headers=headers, json=payload)
                    res.raise_for_status()
                    result = res.json()
                    job_id = result.get("job_id") or result.get("task_id") or result.get("id")
                    
                    if job_id:
                        status_url = f"https://api.acemusic.ai/v1/jobs/{job_id}"
                        for _ in range(60):
                            time.sleep(2)
                            status_res = requests.get(status_url, headers=headers)
                            status_data = status_res.json()
                            status = status_data.get("status")
                            
                            if status in ["succeeded", "completed"]:
                                audio_url = status_data.get("audio_url")
                                if audio_url:
                                    audio_data = requests.get(audio_url).content
                                    st.session_state.background_music_bytes = audio_data
                                    save_persistent_data()
                                    st.success("✅ الموسيقى جاهزة!")
                                    st.audio(audio_data, format="audio/mp3")
                                break
                            elif status == "failed":
                                st.error("فشل التوليد.")
                                break
                    else:
                        st.error("لم يتم استلام job_id.")
                except Exception as e:
                    st.error(f"وقع مشكل: {e}")
                    
    else:
        uploaded_music = st.file_uploader("ارفع ملف الموسيقى (MP3/WAV)", type=["mp3", "wav"])
        if uploaded_music:
            st.session_state.background_music_bytes = uploaded_music.read()
            save_persistent_data()
            st.success("✅ تم رفع الموسيقى!")
            st.audio(st.session_state.background_music_bytes)

    col1, col2 = st.columns(2)
    with col1:
        if st.button(":material/arrow_back: السابق: المؤثرات الصوتية"):
            st.session_state.current_step = 3
            st.rerun()
    with col2:
        if st.button(":material/arrow_forward: التالي: المونتاج النهائي", type="primary"):
            st.session_state.current_step = 5
            st.rerun()

# ==========================================
# الخطوة 5: المونتاج النهائي
# ==========================================
elif st.session_state.current_step == 5:
    st.header(":material/movie_edit: 5. المونتاج النهائي")
    st.info("غادي نجيبو الفيديوهات المناسبة لكل مشهد ونركبو كلشي مع بعضياتو.")
    
    # جلب الفيديوهات
    for scene in st.session_state.script_data['scenes']:
        scene_num = str(scene['scene_number'])
        if scene_num not in st.session_state.scene_assets:
            st.session_state.scene_assets[scene_num] = {}
            
        if 'selected_video' not in st.session_state.scene_assets[scene_num]:
            with st.spinner(f"جاري البحث عن فيديو لـ '{scene['search_keyword']}'..."):
                video_data = search_pixabay_videos(scene['search_keyword'], st.session_state.pixabay_api_key)
                if not video_data:
                    video_data = search_coverr_videos(scene['search_keyword'])
                st.session_state.scene_assets[scene_num]['selected_video'] = video_data

    # عرض الفيديوهات اللي لقا
    st.subheader("🎥 المقاطع اللي غادي تتستعمل:")
    for scene in st.session_state.script_data['scenes']:
        scene_num = str(scene['scene_number'])
        selected_vid = st.session_state.scene_assets[scene_num].get('selected_video')
        
        if selected_vid:
            st.write(f"**المشهد {scene_num}:**")
            st.markdown(f"[🔗 شوف الفيديو]({selected_vid['preview_url']})")
        else:
            st.warning(f"المشهد {scene_num}: ما لقيناش فيديو، غادي نستعملو خلفية سوداء.")

    if st.button(":material/play_circle: بدء التركيب النهائي", type="primary"):
        with st.spinner("جاري تركيب الفيديو النهائي... (هادشي كياخد وقت)"):
            temp_files = []
            try:
                aspect_map = {"9:16 (ريلز/تيك توك)": (1080, 1920), "16:9 (يوتيوب)": (1920, 1080), "1:1 (مربع)": (1080, 1080), "4:5 (إنستغرام)": (1080, 1350), "4:3 (كلاسيكي)": (1440, 1080)}
                quality_map = {"480p": 480, "720p": 720, "1080p": 1080}
                target_h = quality_map[st.session_state.quality]
                target_w = int(target_h * aspect_map[st.session_state.aspect_ratio][0] / aspect_map[st.session_state.aspect_ratio][1])

                video_clips = []
                audio_tracks = []
                current_time = 0
                
                scenes = st.session_state.script_data['scenes']
                num_scenes = len(scenes)

                # التعامل مع الصوت
                master_audio_used = False
                if st.session_state.get("full_audio_bytes") and st.session_state.get("voice_mode") == "رفع ملف صوتي جاهز (للتعليق كامل)":
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                        tmp_audio.write(st.session_state.full_audio_bytes)
                        master_audio_path = tmp_audio.name
                        temp_files.append(master_audio_path)
                    master_audio = AudioFileClip(master_audio_path)
                    total_duration = master_audio.duration
                    audio_tracks.append(master_audio)
                    scene_duration = total_duration / num_scenes
                    master_audio_used = True

                for i, scene in enumerate(scenes):
                    scene_num = str(scene['scene_number'])
                    assets = st.session_state.scene_assets.get(scene_num, {})
                    
                    if not master_audio_used:
                        audio_path = assets.get('audio_path')
                        if not audio_path:
                            st.error(f"ما كاينش صوت للمشهد {scene_num}.")
                            st.stop()
                        
                        voiceover_clip = AudioFileClip(audio_path)
                        scene_duration = voiceover_clip.duration
                        
                        if current_time + scene_duration > st.session_state.max_duration:
                            scene_duration = st.session_state.max_duration - current_time
                            if scene_duration <= 0: break
                            voiceover_clip = voiceover_clip.subclipped(0, scene_duration)
                        
                        audio_tracks.append(voiceover_clip.with_start(current_time))
                    
                    # الفيديو
                    selected_vid = assets.get('selected_video')
                    if not selected_vid:
                        clip = ColorClip(size=(target_w, target_h), color=(0,0,0), duration=scene_duration)
                        video_clips.append(clip.with_start(current_time).with_effects([vfx.FadeIn(0.5), vfx.FadeOut(0.5)]))
                    else:
                        video_url = selected_vid['download_url'] 
                        headers = {"User-Agent": "Mozilla/5.0"}
                        vid_data = requests.get(video_url, headers=headers).content
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_vid:
                            tmp_vid.write(vid_data)
                            vid_path = tmp_vid.name
                            temp_files.append(vid_path)
                        
                        clip = VideoFileClip(vid_path)
                        clip = clip.without_audio() 
                        
                        if clip.duration >= scene_duration:
                            clip = clip.subclipped(0, scene_duration)
                        else:
                            loop_count = int(scene_duration / clip.duration) + 1
                            clip = concatenate_videoclips([clip] * loop_count).subclipped(0, scene_duration)
                        
                        clip = clip.resized(height=target_h)
                        if clip.w < target_w: clip = clip.resized(width=target_w)
                        clip = clip.cropped(x_center=clip.w/2, y_center=clip.h/2, width=target_w, height=target_h)
                        
                        video_clips.append(clip.with_start(current_time).with_effects([vfx.FadeIn(0.5), vfx.FadeOut(0.5)]))

                    # المؤثرات الصوتية
                    sfx_urls = assets.get('sfx_urls', [])
                    for idx, sfx in enumerate(sfx_urls):
                        try:
                            sfx_data = requests.get(sfx['url'], timeout=10).content
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_sfx:
                                tmp_sfx.write(sfx_data)
                                sfx_path = tmp_sfx.name
                                temp_files.append(sfx_path)
                            sfx_clip = AudioFileClip(sfx_path)
                            audio_tracks.append(sfx_clip.with_start(current_time + (idx * 0.5)).with_volume_scaled(0.6))
                        except Exception as e:
                            st.warning(f"تعذر تحميل المؤثر {sfx['keyword']}: {e}")

                    current_time += scene_duration

                # الموسيقى
                if st.session_state.background_music_bytes:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_music:
                        tmp_music.write(st.session_state.background_music_bytes)
                        music_path = tmp_music.name
                        temp_files.append(music_path)
                    music_clip = AudioFileClip(music_path)
                    if music_clip.duration < current_time:
                        loop_count = int(current_time / music_clip.duration) + 1
                        music_clip = concatenate_audioclips([music_clip] * loop_count)
                    music_clip = music_clip.subclipped(0, current_time).with_volume_scaled(0.15)
                    audio_tracks.append(music_clip)

                # التجميع
                final_video = CompositeVideoClip(video_clips, size=(target_w, target_h))
                final_audio = CompositeAudioClip(audio_tracks)
                final_video = final_video.with_audio(final_audio)
                
                output_path = "final_output.mp4"
                final_video.write_videofile(
                    output_path, fps=24, codec="libx264", audio_codec="aac",
                    preset="ultrafast", threads=1, logger=None
                )
                
                st.success("✅ الفيديو النهائي جاهز!")
                st.video(output_path)
                with open(output_path, "rb") as file:
                    st.download_button(":material/download: تحميل الفيديو", data=file, file_name="final_output.mp4", mime="video/mp4")

            except Exception as e:
                st.error(f"وقع مشكل: {e}")
            finally:
                for f in temp_files:
                    try:
                        if os.path.exists(f): os.remove(f)
                    except: pass

    if st.button(":material/arrow_back: السابق: الموسيقى"):
        st.session_state.current_step = 4
        st.rerun()
