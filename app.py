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
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, VideoFileClip, CompositeVideoClip, ColorClip, vfx, CompositeAudioClip, concatenate_audioclips
from docx import Document
from google import genai
from google.genai import types

# --- إعدادات الواجهة ---
st.set_page_config(page_title="AI Studio: Darija & Amazigh", page_icon="🎬", layout="wide")
st.title("🎬 استوديو الذكاء الاصطناعي الشامل")

# --- المفاتيح المحفوظة (Defaults) ---
DEFAULT_PIXABAY_API_KEY = "58178676-7dca3797f2ac366b67263077a"
DEFAULT_ACESTEP_API_KEY = "821f692a10974eaa960316f37a9001f6"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"

# --- قائمة النماذج البديلة (Fallback Chain) ---
FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-1.5-flash-latest"
]

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
            
            saved_acestep = data.get("acestep_api_key", "")
            st.session_state.acestep_api_key = saved_acestep if saved_acestep else DEFAULT_ACESTEP_API_KEY
            
            saved_pixabay = data.get("pixabay_api_key", "")
            st.session_state.pixabay_api_key = saved_pixabay if saved_pixabay else DEFAULT_PIXABAY_API_KEY
            
            st.session_state.hf_api_key = data.get("hf_api_key", "")
            
            saved_model = data.get("gemini_model", "")
            st.session_state.gemini_model = saved_model if saved_model else DEFAULT_GEMINI_MODEL
            
            st.session_state.aspect_ratio = data.get("aspect_ratio", "9:16 (ريلز/تيك توك)")
            st.session_state.quality = data.get("quality", "1080p")
            st.session_state.max_duration = data.get("max_duration", 60)
            st.session_state.language = data.get("language", "الدارجة المغربية")
            st.session_state.tone = data.get("tone", "الكوميدية")
            
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
            "hf_api_key": st.session_state.get("hf_api_key_input", ""),
            "gemini_model": st.session_state.get("gemini_model_input", DEFAULT_GEMINI_MODEL),
            "aspect_ratio": st.session_state.get("aspect_ratio_input", "9:16 (ريلز/تيك توك)"),
            "quality": st.session_state.get("quality_input", "1080p"),
            "max_duration": st.session_state.get("max_duration_input", 60),
            "language": st.session_state.get("language_input", "الدارجة المغربية"),
            "tone": st.session_state.get("tone_input", "الكوميدية"),
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

# --- تهيئة الذاكرة الافتراضية ---
if 'script_data' not in st.session_state: st.session_state.script_data = None
if 'full_audio_bytes' not in st.session_state: st.session_state.full_audio_bytes = None
if 'background_music_bytes' not in st.session_state: st.session_state.background_music_bytes = None
if 'last_custom_script' not in st.session_state: st.session_state.last_custom_script = ""
if 'saved_api_key' not in st.session_state: st.session_state.saved_api_key = ""
if 'acestep_api_key' not in st.session_state: st.session_state.acestep_api_key = DEFAULT_ACESTEP_API_KEY
if 'pixabay_api_key' not in st.session_state: st.session_state.pixabay_api_key = DEFAULT_PIXABAY_API_KEY
if 'hf_api_key' not in st.session_state: st.session_state.hf_api_key = ""
if 'gemini_model' not in st.session_state: st.session_state.gemini_model = DEFAULT_GEMINI_MODEL

if 'aspect_ratio' not in st.session_state: st.session_state.aspect_ratio = "9:16 (ريلز/تيك توك)"
if 'quality' not in st.session_state: st.session_state.quality = "1080p"
if 'max_duration' not in st.session_state: st.session_state.max_duration = 60
if 'language' not in st.session_state: st.session_state.language = "الدارجة المغربية"
if 'tone' not in st.session_state: st.session_state.tone = "الكوميدية"

if not st.session_state.get('data_loaded', False):
    load_persistent_data()
    st.session_state.data_loaded = True

# --- دوال مساعدة للبحث ---
def search_pixabay_videos(query, api_key, per_page=3):
    if not api_key: return None
    url = "https://pixabay.com/api/videos/"
    params = {"key": api_key, "q": query, "per_page": per_page, "video_type": "film", "safesearch": "true"}
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        hits = res.json().get('hits', [])
        if hits:
            video_url = hits[0].get('videos', {}).get('large', {}).get('url') or hits[0].get('videos', {}).get('medium', {}).get('url')
            return video_url
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
            return urls.get('mp4_download') or urls.get('mp4_1080') or urls.get('mp4_720')
    except Exception:
        pass
    return None

def search_sfxmint(query):
    if not query or str(query).lower() in ['n/a', 'none', 'null', '']:
        query = "cinematic"
    url = "https://sfxmint.com/api/v1/search"
    params = {"q": query, "limit": 1}
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        results = []
        if isinstance(data, dict):
            results = data.get('results', [])
        elif isinstance(data, list):
            results = data
            
        if results and len(results) > 0:
            first_item = results[0]
            if isinstance(first_item, dict):
                return first_item.get('audio_url')
            elif isinstance(first_item, str):
                return first_item 
    except Exception as e:
        print(f"SFXMint Error: {e}")
    return None

# --- الشريط الجانبي ---
with st.sidebar:
    st.header("⚙️ الإعدادات العامة")
    gemini_api_key = st.text_input("1. Google Gemini API Key (ضروري):", value=st.session_state.saved_api_key, type="password", key="gemini_api_key_input")
    
    gemini_model_input = st.text_input("2. Gemini Model Name:", value=st.session_state.gemini_model, key="gemini_model_input", help="مثال: gemini-3.5-flash-lite")
    
    if not gemini_model_input.strip():
        gemini_model_input = DEFAULT_GEMINI_MODEL
        st.session_state.gemini_model = DEFAULT_GEMINI_MODEL
        
    acestep_api_key = st.text_input("3. ACE Music API Key (مجاني):", value=st.session_state.acestep_api_key, type="password", key="acestep_api_key_input")

    hf_api_key = st.text_input("4. Hugging Face API Key (اختياري):", value=st.session_state.hf_api_key, type="password", key="hf_api_key_input")
    
    st.markdown("---")
    st.subheader("🎬 إعدادات الفيديو النهائي")
    
    aspect_ratio = st.selectbox(
        "أبعاد الفيديو:", 
        ["9:16 (ريلز/تيك توك)", "16:9 (يوتيوب)", "1:1 (مربع)", "4:5 (إنستغرام)", "4:3 (كلاسيكي)"],
        index=["9:16 (ريلز/تيك توك)", "16:9 (يوتيوب)", "1:1 (مربع)", "4:5 (إنستغرام)", "4:3 (كلاسيكي)"].index(st.session_state.aspect_ratio) if st.session_state.aspect_ratio in ["9:16 (ريلز/تيك توك)", "16:9 (يوتيوب)", "1:1 (مربع)", "4:5 (إنستغرام)", "4:3 (كلاسيكي)"] else 0,
        key="aspect_ratio_input"
    )
    
    quality = st.selectbox(
        "جودة الفيديو:", 
        ["1080p", "720p", "480p"],
        index=["1080p", "720p", "480p"].index(st.session_state.quality) if st.session_state.quality in ["1080p", "720p", "480p"] else 0,
        key="quality_input"
    )
    
    max_duration = st.slider(
        "المدة القصوى للفيديو (ثانية):", 
        min_value=10, 
        max_value=3600, 
        value=st.session_state.max_duration, 
        step=10,
        key="max_duration_input"
    )
    
    st.markdown("---")
    st.subheader("🔑 مفاتيح مكتبات الفيديو")
    
    pixabay_api_key = st.text_input("Pixabay API Key:", value=st.session_state.pixabay_api_key, type="password", key="pixabay_api_key_input")
    
    st.markdown("---")
    
    language_list = [
        "الدارجة المغربية", "الأمازيغية", "العربية الفصحى", 
        "المصرية", "الخليجية", "السورية", "اللبنانية", "العراقية",
        "الأردنية", "الإماراتية", "السعودية", "التونسية", "الجزائرية",
        "الإنجليزية", "الفرنسية", "الإسبانية", "الألمانية", "التركية"
    ]
    language = st.selectbox(
        "اللغة/اللهجة:", 
        language_list,
        index=language_list.index(st.session_state.language) if st.session_state.language in language_list else 0,
        key="language_input"
    )
    
    tone_list = [
        "الكوميدية", "الأكشن والرسوم المتحركة", "الأفلام الموسيقية والرقص",
        "ما بعد الكارثة / النجاة المستقبلية", "الفانتازيا والأسطوريات",
        "الجريمة والسرقة", "التشويق", "الرعب", "الإثارة", "الدراما", "إعلاني (تجاري)"
    ]
    tone = st.selectbox(
        "الستايل (Tone):", 
        tone_list,
        index=tone_list.index(st.session_state.tone) if st.session_state.tone in tone_list else 0,
        key="tone_input"
    )
    
    st.markdown("---")
    st.subheader("🗑️ إدارة الذاكرة")
    if st.button("مسح كل البيانات والبدء من جديد", type="primary"):
        clear_all_data()
        
    save_persistent_data()

# --- التابات ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 1. السيناريو والصوت", 
    "🤖 2. توليد فيديو AI", 
    "🎬 3. التوليد الأوتوماتيكي", 
    "🧩 4. تجميع الفيديو (يدوي)", 
    "🎵 5. الموسيقى"
])

# ==========================================
# التاب 1: السيناريو والصوت
# ==========================================
with tab1:
    st.header("توليد السيناريو المفصل والتعليق الصوتي")
    
    if st.session_state.script_data or st.session_state.full_audio_bytes:
        st.success("💾 تم استرجاع البيانات المحفوظة!")
    
    work_mode = st.radio("كيفاش بغيتي تخدم السيناريو؟", ["توليد سيناريو جديد", "لدي سيناريو جاهز (لصق)"], horizontal=True)
    
    if work_mode == "توليد سيناريو جديد":
        topic = st.text_area("فكرة الفيديو:", height=100)
    else:
        custom_script = st.text_area("لصق السيناريو ديالك هنا:", height=150, value=st.session_state.last_custom_script)

    st.markdown("---")
    
    audio_option = st.radio("🔊 طريقة الحصول على الصوت:", ["توليد الصوت بالذكاء الاصطناعي", "رفع ملف صوتي جاهز"], horizontal=True)

    selected_voice = None
    style_prompt = ""
    uploaded_audio_file = None

    if audio_option == "توليد الصوت بالذكاء الاصطناعي":
        st.subheader("🎙️ إعدادات الصوت")
        voice_col1, voice_col2 = st.columns(2)
        available_voices = {
            "Fenrir (Excitable - Male)": "Fenrir", "Puck (Upbeat - Male)": "Puck",
            "Zephyr (Bright - Female)": "Zephyr", "Kore (Firm - Female)": "Kore",
            "Charon (Informative - Male)": "Charon", "Leda (Youthful - Female)": "Leda"
        }
        with voice_col1:
            selected_voice_label = st.selectbox("اختار الصوت:", list(available_voices.keys()))
            selected_voice = available_voices[selected_voice_label]
        with voice_col2:
            style_prompt = st.text_input("التحكم في الأسلوب:", placeholder="مثال: هضر بضحك...")
            
        generate_btn = st.button("🚀 توليد السيناريو والصوت", use_container_width=True)
    else:
        st.subheader("📤 رفع الصوت الجاهز")
        uploaded_audio_file = st.file_uploader("ارفع ملف الصوت (MP3/WAV)", type=["mp3", "wav"])
        if uploaded_audio_file is not None:
            st.session_state.full_audio_bytes = uploaded_audio_file.read()
            save_persistent_data()
            st.success("✅ تم رفع الصوت بنجاح!")
            st.audio(st.session_state.full_audio_bytes, format="audio/wav")
        generate_btn = st.button("📝 تحليل السيناريو فقط (بدون توليد صوت)", use_container_width=True)

    if generate_btn:
        if not st.session_state.get("gemini_api_key_input"):
            st.error("عافاك دخل Google Gemini API Key.")
        else:
            full_dialogue = ""
            try:
                with st.spinner("جاري تحليل السيناريو واستخراج المؤثرات الصوتية..."):
                    client = genai.Client(api_key=st.session_state.gemini_api_key_input)
                    
                    current_model = st.session_state.gemini_model.strip() if st.session_state.gemini_model else ""
                    models_to_try = []
                    if current_model:
                        models_to_try.append(current_model)
                    models_to_try.extend([m for m in FALLBACK_MODELS if m != current_model])
                    
                    used_model_name = None
                    model_working = False
                    
                    for model_name in models_to_try:
                        try:
                            client.models.generate_content(
                                model=model_name, 
                                contents="Hi", 
                                config=types.GenerateContentConfig(max_output_tokens=5)
                            )
                            used_model_name = model_name
                            model_working = True
                            break
                        except Exception as e:
                            if "429" in str(e):
                                st.warning(f"⚠️ النموذج '{model_name}' وصل للحد الأقصى. جاري تجربة نموذج آخر...")
                            elif "404" in str(e) or "not found" in str(e).lower() or "400" in str(e) or "unexpected model name" in str(e).lower():
                                st.warning(f"⚠️ النموذج '{model_name}' غير متوفر أو غير صالح. جاري تجربة نموذج آخر...")
                            else:
                                raise e
                    
                    if not model_working:
                        st.error("❌ فشلت جميع النماذج المتاحة. يرجى المحاولة لاحقاً أو استخدام مفتاح API آخر.")
                        st.stop()
                    
                    if used_model_name != st.session_state.gemini_model:
                        st.session_state.gemini_model = used_model_name
                        save_persistent_data()
                        st.success(f"✅ تم التحديث التلقائي للنموذج إلى: {used_model_name}")
                        time.sleep(1.5)
                        st.rerun()

                    if work_mode == "توليد سيناريو جديد":
                        if not topic: st.warning("عافاك كتب شي فكرة.")
                        else:
                            prompt = f"""أنت كاتب سيناريوهات ومهندس صوت سينمائي محترف. كتب سيناريو فيديو باللهجة {language}.
                            الموضوع: {topic}
                            الستايل: {tone}
                            
                            تحذير: فـ كل مشهد، خاصك تعمر الخانة ديال "sfx_keywords" بـ **ليستة (Array) ديال الكلمات الإنجليزية** (من 2 إلى 4 كلمات) تصف المؤثرات الصوتية المناسبة للمشهد بناءً على الوصف والحوار.
                            ممنوع تكتب N/A. ممنوع تخليها خاوية.
                            أمثلة: ["wind", "footsteps", "tension"], ["ambient city", "car passing", "rain"].
                            
                            خاصك ترجع الجواب على شكل JSON فقط بهذا الهيكل:
                            {{
                                "title": "عنوان",
                                "scenes": [
                                    {{
                                        "scene_number": 1,
                                        "location": "مكان",
                                        "visual_description": "وصف بصري مفصل",
                                        "search_keyword": "english keywords for video",
                                        "sfx_keywords": ["keyword1", "keyword2", "keyword3"],
                                        "dialogue": "الحوار"
                                    }}
                                ]
                            }}"""
                            response = client.models.generate_content(
                                model=used_model_name,
                                contents=prompt,
                                config=types.GenerateContentConfig(response_mime_type="application/json")
                            )
                            txt = response.text.strip().replace("```json", "").replace("```", "")
                            st.session_state.script_data = json.loads(txt)
                            st.success("✅ السيناريو جاهز!")
                    else:
                        if not custom_script: st.warning("عافاك لصق السيناريو.")
                        else:
                            full_dialogue = custom_script
                            if st.session_state.last_custom_script != custom_script:
                                prompt = f"""قسم هذا السيناريو لمشاهد.
                                النص: {custom_script}
                                
                                تحذير: فـ كل مشهد، خاصك تعمر "sfx_keywords" بليستة ديال 2 إلى 4 كلمات إنجليزية للمؤثرات الصوتية بناءً على الحوار والوصف. ممنوع N/A.
                                
                                رجع JSON فقط:
                                {{
                                    "title":"عنوان",
                                    "scenes":[
                                        {{
                                            "scene_number":1,
                                            "location":"مكان",
                                            "visual_description":"وصف",
                                            "search_keyword":"english keywords for video",
                                            "sfx_keywords":["keyword1", "keyword2"],
                                            "dialogue":"الحوار الأصلي"
                                        }}
                                    ]
                                }}"""
                                response = client.models.generate_content(
                                    model=used_model_name,
                                    contents=prompt,
                                    config=types.GenerateContentConfig(response_mime_type="application/json")
                                )
                                txt = response.text.strip().replace("```json", "").replace("```", "")
                                st.session_state.script_data = json.loads(txt)
                                st.session_state.last_custom_script = custom_script
                                st.success("✅ تم تحليل السيناريو!")

                    # --- الحماية ببايثون (Python Fallback) للمؤثرات ---
                    for scene in st.session_state.script_data.get('scenes', []):
                        sfx_list = scene.get('sfx_keywords', [])
                        if isinstance(sfx_list, str): sfx_list = [sfx_list]
                        if not sfx_list or all(str(s).lower() in ['n/a', 'none', 'null', ''] for s in sfx_list):
                            sfx_list = []
                            text = (str(scene.get('visual_description','')) + " " + str(scene.get('dialogue','')) + " " + str(scene.get('search_keyword',''))).lower()
                            if "wind" in text or "ريح" in text: sfx_list.append("wind")
                            if "footstep" in text or "walk" in text or "مشي" in text or "خطوات" in text: sfx_list.append("footsteps")
                            if "rain" in text or "مطر" in text: sfx_list.append("rain")
                            if "water" in text or "drop" in text or "ماء" in text or "قطرة" in text: sfx_list.append("water drop")
                            if "fire" in text or "flame" in text or "نار" in text or "لهب" in text: sfx_list.append("fire")
                            if "city" in text or "street" in text or "مدينة" in text or "زنقة" in text: sfx_list.append("ambient city")
                            if "tension" in text or "suspense" in text or "توتر" in text or "قلق" in text: sfx_list.append("tension")
                            if "think" in text or "reflect" in text or "تفكير" in text or "يخاطب نفسه" in text: sfx_list.append("thinking")
                            if not sfx_list: sfx_list = ["cinematic"]
                        scene['sfx_keywords'] = list(set(sfx_list))

            except Exception as e:
                st.error(f"خطأ: {e}")

            if st.session_state.script_data:
                st.subheader(f"🎬 {st.session_state.script_data.get('title')}")
                for scene in st.session_state.script_data.get('scenes', []):
                    with st.expander(f"المشهد {scene['scene_number']}"):
                        st.write(f"**البحث:** {scene.get('search_keyword', 'N/A')}")
                        st.write(f"**المؤثرات الصوتية:** {', '.join(scene.get('sfx_keywords', []))}")
                        st.write(f"**الحوار:** {scene['dialogue']}")
                        full_dialogue += scene['dialogue'] + " "

            if audio_option == "توليد الصوت بالذكاء الاصطناعي" and full_dialogue.strip():
                with st.spinner("جاري توليد الصوت..."):
                    try:
                        tts_instruction = f"اقرأ النص باللهجة {language}. الأسلوب: {style_prompt}. ممنوع تنطق ما بين الأقواس. النص: {full_dialogue}"
                        
                        response_tts = client.models.generate_content(
                            model="gemini-3.8-flash-tts",
                            contents=tts_instruction,
                            config=types.GenerateContentConfig(
                                response_modalities=["AUDIO"],
                                speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=selected_voice)))
                            )
                        )
                        
                        if response_tts.candidates and response_tts.candidates[0].content.parts and response_tts.candidates[0].content.parts[0].inline_data is not None:
                            audio_data = response_tts.candidates[0].content.parts[0].inline_data.data
                            st.session_state.full_audio_bytes = audio_data
                            st.success("✅ الصوت جاهز!")
                            st.audio(audio_data, format="audio/wav")
                        else:
                            st.error("⚠️ النموذج ما رجعش بيانات صوتية.")
                    except Exception as e:
                        st.error(f"خطأ فـ الصوت: {e}")
            
            save_persistent_data()

# ==========================================
# التاب 2: توليد فيديو AI
# ==========================================
with tab2:
    st.header("توليد فيديو بالذكاء الاصطناعي (Text to Video)")
    st.info("هذا الخيار يتطلب مفتاح API لخدمة مثل RunwayML أو Magic Hour.")

# ==========================================
# التاب 3: التوليد الأوتوماتيكي (المحسن)
# ==========================================
with tab3:
    st.header("🎬 التوليد الأوتوماتيكي للفيديو")
    
    has_script = st.session_state.script_data is not None
    has_audio = st.session_state.full_audio_bytes is not None
    
    if not has_script or not has_audio:
        missing_msg = "⚠️ خاصك تجهز: "
        if not has_script: missing_msg += "**السيناريو** (سير للتاب 1) "
        if not has_audio: missing_msg += "**والصوت** (سير للتاب 1) "
        st.warning(missing_msg)
    else:
        st.success("✅ السيناريو والصوت واجدين فـ الذاكرة!")
        if st.session_state.background_music_bytes:
            st.info("🎵 الموسيقى موجودة فـ الذاكرة.")
        else:
            st.warning("⚠️ ما كاينش موسيقى محفوظة. إلا بغيتي تزيد موسيقى، سير للتاب 5.")
            
        st.markdown("---")
        st.subheader("🖼️ مصدر الفيديو")
        video_source = st.radio("كيفاش بغيتي تجيب الفيديوهات؟", ["البحث فـ مكتبات الفيديو (Pixabay/Coverr)", "رفع صور خاصة بي"], horizontal=True)
        
        uploaded_images = None
        if video_source == "رفع صور خاصة بي":
            uploaded_images = st.file_uploader("ارفع صورك (بترتيب المشاهد)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

        if st.button("🚀 بدء التوليد الأوتوماتيكي", use_container_width=True):
            if video_source == "البحث فـ مكتبات الفيديو (Pixabay/Coverr)" and not st.session_state.pixabay_api_key:
                st.error("⚠️ عافاك دخل مفتاح Pixabay API فالشريط الجانبي.")
            elif video_source == "رفع صور خاصة بي" and not uploaded_images:
                st.error("⚠️ عافاك ارفع على الأقل صورة وحدة.")
            else:
                with st.spinner("جاري البحث، التحميل، التجميع، وإضافة المؤثرات..."):
                    temp_files = []
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                            tmp_audio.write(st.session_state.full_audio_bytes)
                            audio_path = tmp_audio.name
                            temp_files.append(audio_path)
                        
                        full_audio_clip = AudioFileClip(audio_path)
                        audio_duration = full_audio_clip.duration
                        actual_duration = min(audio_duration, st.session_state.max_duration)
                        voiceover_clip = full_audio_clip.subclipped(0, actual_duration)
                        
                        audio_tracks = [voiceover_clip]
                        if st.session_state.background_music_bytes:
                            try:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_music:
                                    tmp_music.write(st.session_state.background_music_bytes)
                                    music_path = tmp_music.name
                                    temp_files.append(music_path)
                                
                                music_clip = AudioFileClip(music_path)
                                if music_clip.duration < actual_duration:
                                    loop_count = int(actual_duration / music_clip.duration) + 1
                                    music_clip = concatenate_audioclips([music_clip] * loop_count)
                                
                                music_clip = music_clip.subclipped(0, actual_duration)
                                music_clip = music_clip.with_volume_scaled(0.15)
                                audio_tracks.append(music_clip)
                            except Exception as e:
                                st.warning(f"⚠️ تعذر تحميل الموسيقى الخلفية: {e}")

                        scenes = st.session_state.script_data.get('scenes', [])
                        num_scenes = len(scenes)
                        
                        if num_scenes == 0:
                            st.error("ما كاينش مشاهد فـ السيناريو.")
                        else:
                            duration_per_scene = actual_duration / num_scenes
                            
                            aspect_map = {"9:16 (ريلز/تيك توك)": (1080, 1920), "16:9 (يوتيوب)": (1920, 1080), "1:1 (مربع)": (1080, 1080), "4:5 (إنستغرام)": (1080, 1350), "4:3 (كلاسيكي)": (1440, 1080)}
                            quality_map = {"480p": 480, "720p": 720, "1080p": 1080}
                            
                            target_h = quality_map[st.session_state.quality]
                            target_w = int(target_h * aspect_map[st.session_state.aspect_ratio][0] / aspect_map[st.session_state.aspect_ratio][1])
                            
                            video_clips = []
                            
                            if video_source == "رفع صور خاصة بي":
                                for i, img_file in enumerate(uploaded_images[:num_scenes]): 
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                                        tmp_img.write(img_file.getvalue())
                                        img_path = tmp_img.name
                                        temp_files.append(img_path)
                                    
                                    img = Image.open(img_path)
                                    img = img.resize((target_w, target_h))
                                    img_array = np.array(img)
                                    
                                    clip = ImageClip(img_array).with_duration(duration_per_scene)
                                    clip = clip.with_position('center')
                                    
                                    video_clips.append(clip)
                            else:
                                for i, scene in enumerate(scenes):
                                    keyword = scene.get('search_keyword', 'abstract background')
                                    st.write(f"🔍 كنقلب على مشهد {i+1}: '{keyword}'...")
                                    
                                    video_url = search_pixabay_videos(keyword, st.session_state.pixabay_api_key)
                                    if not video_url:
                                        video_url = search_coverr_videos(keyword)
                                    
                                    if video_url:
                                        vid_data = requests.get(video_url).content
                                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_vid:
                                            tmp_vid.write(vid_data)
                                            vid_path = tmp_vid.name
                                            temp_files.append(vid_path)
                                        
                                        try:
                                            clip = VideoFileClip(vid_path)
                                            
                                            if clip.duration >= duration_per_scene:
                                                clip = clip.subclipped(0, duration_per_scene)
                                            else:
                                                loop_count = int(duration_per_scene / clip.duration) + 1
                                                clip = concatenate_videoclips([clip] * loop_count).subclipped(0, duration_per_scene)
                                            
                                            clip = clip.resized(height=target_h)
                                            if clip.w < target_w:
                                                clip = clip.resized(width=target_w)
                                            clip = clip.cropped(x_center=clip.w/2, y_center=clip.h/2, width=target_w, height=target_h)
                                            
                                            video_clips.append(clip)
                                        except Exception as e:
                                            st.warning(f"⚠️ تعذر تحميل الفيديو: {e}")
                                            clip = ColorClip(size=(target_w, target_h), color=(0,0,0), duration=duration_per_scene)
                                            video_clips.append(clip)
                                    else:
                                        st.warning(f"⚠️ ما لقيتش فيديو لـ '{keyword}'. غادي نستعملو خلفية سوداء.")
                                        clip = ColorClip(size=(target_w, target_h), color=(0,0,0), duration=duration_per_scene)
                                        video_clips.append(clip)

                                    sfx_keywords = scene.get('sfx_keywords', [])
                                    for idx, sfx_kw in enumerate(sfx_keywords):
                                        st.write(f"🔊 كنقلب على مؤثر صوتي {idx+1}: '{sfx_kw}'...")
                                        sfx_url = search_sfxmint(sfx_kw)
                                        if sfx_url:
                                            try:
                                                sfx_res = requests.get(sfx_url, timeout=10)
                                                sfx_data = sfx_res.content
                                                
                                                if b"<html" in sfx_data.lower() or b"<!doctype" in sfx_data.lower():
                                                    st.warning(f"⚠️ المؤثر '{sfx_kw}' رجع صفحة ويب بدل ملف صوتي. تخطي...")
                                                    continue
                                                
                                                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_sfx:
                                                    tmp_sfx.write(sfx_data)
                                                    sfx_path = tmp_sfx.name
                                                    temp_files.append(sfx_path)
                                                
                                                sfx_clip = AudioFileClip(sfx_path)
                                                
                                                base_start = i * duration_per_scene
                                                offset = idx * 0.5 
                                                start_time = base_start + offset
                                                
                                                sfx_clip = sfx_clip.with_start(start_time).with_volume_scaled(0.5)
                                                audio_tracks.append(sfx_clip)
                                            except Exception as e:
                                                st.warning(f"⚠️ تعذر تحميل المؤثر الصوتي {sfx_kw}: {e}")
                            
                            if video_clips:
                                st.write("🎬 كنركب الفيديو النهائي مع المؤثرات...")
                                try:
                                    # استعمال method="chain" بدل "compose" باش نتفاداو استهلاك الذاكرة الكبير
                                    final_video = concatenate_videoclips(video_clips, method="chain")
                                    
                                    valid_audio_tracks = [track for track in audio_tracks if track is not None]
                                    if valid_audio_tracks:
                                        final_audio = CompositeAudioClip(valid_audio_tracks)
                                        final_video = final_video.with_audio(final_audio)
                                    
                                    output_path = "auto_generated_video.mp4"
                                    
                                    # إعدادات خفيفة جدا على السيرفر
                                    final_video.write_videofile(
                                        output_path, 
                                        fps=15, # تقليل الـ FPS باش نخففو المعالجة
                                        codec="libx264", 
                                        audio_codec="aac",
                                        preset="ultrafast",
                                        threads=1,
                                        logger=None
                                    )
                                    
                                    st.success("✅ الفيديو الأوتوماتيكي جاهز مع المؤثرات السينمائية!")
                                    st.video(output_path)
                                    
                                    with open(output_path, "rb") as file:
                                        # هنا التصحيح: استعملنا data=file بدل file=file
                                        st.download_button("⬇️ تحميل الفيديو", data=file, file_name="auto_generated_video.mp4", mime="video/mp4")
                                except Exception as e:
                                    st.error(f"❌ فشل في تركيب الفيديو النهائي: {e}")
                            else:
                                st.error("ما قدرناش نصنعو الفيديو.")
                                
                    except Exception as e:
                        st.error(f"وقع مشكل فالتوليد: {e}")
                    finally:
                        for f in temp_files:
                            try:
                                if os.path.exists(f):
                                    os.remove(f)
                            except:
                                pass

# ==========================================
# التاب 4 و 5
# ==========================================
with tab4:
    st.header("🧩 تجميع الفيديو (رفع يدوي)")
    st.write("تقدر ترفع الصور والفيديوهات هنا وتجمعهم مع الصوت اللي فـ التاب 1.")
    uploaded_media = st.file_uploader("تحميل صور أو فيديوهات (JPG, PNG, MP4):", type=["jpg", "jpeg", "png", "mp4"], accept_multiple_files=True)
    if st.button("🚀 تجميع ودمج", use_container_width=True):
        if not uploaded_media: st.warning("عافاك حمل شي ملفات.")
        else: st.success("✅ تم التجميع بنجاح! (هذا مجرد مثال توضيحي)")

with tab5:
    st.header("🎵 الموسيقى")
    music_option = st.radio("🎼 طريقة الحصول على الموسيقى:", [
        "توليد موسيقى بالذكاء الاصطناعي (Google Lyria)", 
        "توليد موسيقى باستعمال ACE Music API (مجاني)", 
        "رفع ملف موسيقى جاهز"
    ], horizontal=False)
    
    if music_option == "توليد موسيقى بالذكاء الاصطناعي (Google Lyria)":
        st.info("ملاحظة: خدمة Lyria 3 قد تكون مقطوعة مؤقتاً (Error 429).")
        if not st.session_state.get("gemini_api_key_input"):
            st.warning("⚠️ عافاك دخل Google Gemini API Key.")
        else:
            music_prompt = st.text_area("وصف الموسيقى:", height=100)
            if st.button("🎵 توليد الموسيقى (Lyria)", use_container_width=True):
                with st.spinner("جاري التوليد..."):
                    try:
                        client = genai.Client(api_key=st.session_state.gemini_api_key_input)
                        response = client.models.generate_content(
                            model="lyria-3-clip-preview", 
                            contents=music_prompt
                        )
                        audio_data = None
                        if response.candidates and response.candidates[0].content.parts:
                            for part in response.candidates[0].content.parts:
                                if part.inline_data:
                                    audio_data = part.inline_data.data
                                    break
                        if audio_data:
                            st.session_state.background_music_bytes = audio_data
                            save_persistent_data()
                            st.success("✅ الموسيقى جاهزة ومحفوظة!")
                            st.audio(audio_data, format="audio/mp3")
                        else:
                            st.error("⚠️ ما رجعش صوت.")
                    except Exception as e:
                        st.error(f"وقع مشكل: {e}")
    
    elif music_option == "توليد موسيقى باستعمال ACE Music API (مجاني)":
        st.subheader("🎼 توليد الموسيقى بـ ACE Music API")
        st.info("💡 ACE Music API مجاني تماماً. المفتاح ديالك محفوظ أوتوماتيكياً.")
        
        if not st.session_state.acestep_api_key:
            st.warning("⚠️ عافاك دخل ACE Music API Key فالشريط الجانبي.")
        else:
            ace_music_prompt = st.text_area("وصف الموسيقى (ACE Music):", height=100, placeholder="مثال: a happy summer pop beat, uplifting synths")
            
            if st.button("🎵 توليد الموسيقى (ACE Music)", use_container_width=True, key="btn_ace_music"):
                with st.spinner("جاري التوليد عبر ACE Music API..."):
                    try:
                        headers = {"Authorization": f"Bearer {st.session_state.acestep_api_key}", "Content-Type": "application/json"}
                        payload = {"prompt": ace_music_prompt, "duration": 30, "task_type": "text2music"}
                        
                        res = requests.post("https://api.acemusic.ai/v1/music/generate", headers=headers, json=payload)
                        res.raise_for_status()
                        result = res.json()
                        job_id = result.get("job_id") or result.get("task_id") or result.get("id")
                        
                        if not job_id:
                            st.error(f"لم يتم استلام job_id. الرد: {result}")
                        else:
                            st.info(f"تم إنشاء المهمة: {job_id}. جاري الانتظار...")
                            status_url = f"https://api.acemusic.ai/v1/jobs/{job_id}"
                            audio_url = None
                            
                            for _ in range(60):
                                time.sleep(2)
                                status_res = requests.get(status_url, headers=headers)
                                status_data = status_res.json()
                                status = status_data.get("status")
                                
                                if status in ["succeeded", "completed"]:
                                    audio_url = status_data.get("audio_url")
                                    break
                                elif status == "failed":
                                    st.error(f"فشل التوليد: {status_data}")
                                    break
                            
                            if audio_url:
                                audio_data = requests.get(audio_url).content
                                st.session_state.background_music_bytes = audio_data
                                save_persistent_data()
                                st.success("✅ الموسيقى جاهزة ومحفوظة!")
                                st.audio(audio_data, format="audio/mp3")
                            else:
                                st.error("لم يتم الحصول على رابط الصوت بعد انتهاء المهلة.")
                                
                    except Exception as e:
                        st.error(f"وقع مشكل مع ACE Music API: {e}")

    else:
        uploaded_music = st.file_uploader("ارفع ملف الموسيقى (MP3/WAV)", type=["mp3", "wav"])
        if uploaded_music is not None:
            st.session_state.background_music_bytes = uploaded_music.read()
            save_persistent_data()
            st.success("✅ تم رفع الموسيقى بنجاح ومحفوظة!")
            st.audio(uploaded_music, format="audio/wav")
