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
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, VideoFileClip, CompositeVideoClip, concatenate_audioclips
from docx import Document

# --- إعدادات الواجهة ---
st.set_page_config(page_title="AI Studio: Darija & Amazigh", page_icon="🎬", layout="wide")
st.title("🎬 استوديو الذكاء الاصطناعي الشامل")

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
            st.session_state.treblo_api_key = data.get("treblo_api_key", "")
            st.session_state.hf_api_key = data.get("hf_api_key", "")
            
            main_audio_path = os.path.join(AUDIO_DIR, "main_voice.wav")
            if os.path.exists(main_audio_path):
                with open(main_audio_path, "rb") as f:
                    st.session_state.full_audio_bytes = f.read()
            else:
                st.session_state.full_audio_bytes = None

            st.session_state.saved_voices = data.get("saved_voices_meta", [])
            for i, voice in enumerate(st.session_state.saved_voices):
                voice_path = os.path.join(AUDIO_DIR, f"voice_{i}.wav")
                if os.path.exists(voice_path):
                    with open(voice_path, "rb") as f:
                        voice["audio"] = f.read()
        except Exception:
            pass

def save_persistent_data():
    try:
        voices_meta = []
        for i, voice in enumerate(st.session_state.saved_voices):
            voices_meta.append({"text": voice["text"], "voice": voice["voice"], "style": voice.get("style","")})
            with open(os.path.join(AUDIO_DIR, f"voice_{i}.wav"), "wb") as f:
                f.write(voice["audio"])
        
        data = {
            "script_data": st.session_state.script_data,
            "last_custom_script": st.session_state.last_custom_script,
            "gemini_api_key": st.session_state.get("gemini_api_key_input", ""),
            "treblo_api_key": st.session_state.get("treblo_api_key_input", ""),
            "hf_api_key": st.session_state.get("hf_api_key_input", ""),
            "saved_voices_meta": voices_meta
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        if st.session_state.full_audio_bytes:
            with open(os.path.join(AUDIO_DIR, "main_voice.wav"), "wb") as f:
                f.write(st.session_state.full_audio_bytes)
    except Exception:
        pass

def clear_all_data():
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    st.session_state.clear()
    st.rerun()

# --- تهيئة الذاكرة ---
if 'saved_voices' not in st.session_state: st.session_state.saved_voices = []
if 'script_data' not in st.session_state: st.session_state.script_data = None
if 'full_audio_bytes' not in st.session_state: st.session_state.full_audio_bytes = None
if 'last_custom_script' not in st.session_state: st.session_state.last_custom_script = ""
if 'saved_api_key' not in st.session_state: st.session_state.saved_api_key = ""
if 'treblo_api_key' not in st.session_state: st.session_state.treblo_api_key = ""
if 'hf_api_key' not in st.session_state: st.session_state.hf_api_key = ""

if not st.session_state.get('data_loaded', False):
    load_persistent_data()
    st.session_state.data_loaded = True

# --- دوال مساعدة ---
def fetch_coverr_videos(query):
    url = "https://api.coverr.co/videos"
    params = {"query": query, "page_size": 1}
    try:
        res = requests.get(url, params=params).json()
        if res.get('hits'):
            urls = res['hits'][0].get('urls', {})
            return urls.get('mp4_download') or urls.get('mp4_1080')
    except: return None

# --- الشريط الجانبي ---
with st.sidebar:
    st.header("⚙️ الإعدادات العامة")
    gemini_api_key = st.text_input("1. Google Gemini API Key (ضروري):", value=st.session_state.saved_api_key, type="password", key="gemini_api_key_input")
    if gemini_api_key != st.session_state.saved_api_key:
        st.session_state.saved_api_key = gemini_api_key
        save_persistent_data()
    
    treblo_api_key = st.text_input("2. Treblo API Key (اختياري):", value=st.session_state.treblo_api_key, type="password", key="treblo_api_key_input")
    if treblo_api_key != st.session_state.treblo_api_key:
        st.session_state.treblo_api_key = treblo_api_key
        save_persistent_data()

    hf_api_key = st.text_input("3. Hugging Face API Key (اختياري - لـ ACE-Step السحابي):", value=st.session_state.hf_api_key, type="password", key="hf_api_key_input")
    if hf_api_key != st.session_state.hf_api_key:
        st.session_state.hf_api_key = hf_api_key
        save_persistent_data()
    
    st.markdown("---")
    language = st.selectbox("اللغة/اللهجة:", [
        "الدارجة المغربية", "الأمازيغية", "العربية الفصحى", 
        "المصرية", "الخليجية", "السورية", "اللبنانية", "العراقية",
        "الإنجليزية", "الفرنسية", "الإسبانية", "الألمانية", "التركية"
    ])
    
    tone = st.selectbox("الستايل (Tone):", [
        "الكوميدية", "الأكشن والرسوم المتحركة", "الأفلام الموسيقية والرقص",
        "ما بعد الكارثة / النجاة المستقبلية", "الفانتازيا والأسطوريات",
        "الجريمة والسرقة", "التشويق", "الرعب", "الإثارة", "الدراما", "إعلاني (تجاري)"
    ])
    
    st.markdown("---")
    st.subheader("🗑️ إدارة الذاكرة")
    if st.button("مسح كل البيانات والبدء من جديد", type="primary"):
        clear_all_data()

# --- التابات ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 1. السيناريو والصوت", 
    "🤖 2. توليد فيديو AI", 
    "🎬 3. التوليد الأوتوماتيكي", 
    "🧩 4. تجميع الفيديو (صور/فيديو)", 
    "🎵 5. الموسيقى"
])

# ==========================================
# التاب 1: السيناريو والصوت (بقية الكود كما هو)
# ==========================================
# ... (نفس كود التاب 1 السابق) ...

# ==========================================
# التاب 5: الموسيقى (محدث)
# ==========================================
with tab5:
    st.header("🎵 الموسيقى")
    
    music_option = st.radio("🎼 طريقة الحصول على الموسيقى:", [
        "توليد موسيقى بالذكاء الاصطناعي (Google Lyria)", 
        "توليد موسيقى باستعمال Treblo API", 
        "توليد موسيقى باستعمال ACE-Step", 
        "رفع ملف موسيقى جاهز (إلغاء التوليد)"
    ], horizontal=False)
    
    if music_option == "توليد موسيقى بالذكاء الاصطناعي (Google Lyria)":
        st.info("ملاحظة: خدمة Lyria 3 قد تكون مقطوعة مؤقتاً (Error 429). استعمل الخيارات الأخرى.")
        if not gemini_api_key:
            st.warning("⚠️ عافاك دخل Google Gemini API Key.")
        else:
            music_prompt = st.text_area("وصف الموسيقى:", height=100, placeholder="مثال: موسيقى هادئة...")
            if st.button("🎵 توليد الموسيقى (Lyria)", use_container_width=True):
                with st.spinner("جاري التوليد..."):
                    try:
                        from google import genai as google_genai
                        client = google_genai.Client(api_key=gemini_api_key)
                        res = client.models.generate_content(model="lyria-3-clip-preview", contents=music_prompt)
                        audio_data = next((part.inline_data.data for part in res.parts if part.inline_data), None)
                        if audio_data:
                            st.success("✅ الموسيقى جاهزة!")
                            st.audio(audio_data, format="audio/mp3")
                        else:
                            st.error("⚠️ ما رجعش صوت.")
                    except Exception as e:
                        st.error(f"وقع مشكل (الكوطا ممكن تكون كملات): {e}")
    
    elif music_option == "توليد موسيقى باستعمال Treblo API":
        # ... (نفس كود Treblo السابق) ...

    elif music_option == "توليد موسيقى باستعمال ACE-Step":
        st.subheader("🎼 توليد الموسيقى بـ ACE-Step")
        
        ace_step_source = st.radio(
            "اختر مصدر ACE-Step:",
            ["Hugging Face Space (سحابي)", "خادم محلي (Local Server)"],
            horizontal=True
        )
        
        if ace_step_source == "Hugging Face Space (سحابي)":
            st.info("💡 يستخدم هذا الخيار مساحة Hugging Face الرسمية لـ ACE-Step. يفضل إدخال Hugging Face API Key في الشريط الجانبي لتجنب حدود الاستخدام.")
            ace_step_prompt = st.text_area("وصف الموسيقى (ACE-Step):", height=100, placeholder="مثال: a happy summer pop song")
            
            if st.button("🎵 توليد الموسيقى (ACE-Step HF)", use_container_width=True):
                with st.spinner("جاري التوليد عبر Hugging Face... قد يستغرق بعض الوقت."):
                    try:
                        # استخدام عميل Gradio للاتصال بمساحة Hugging Face
                        from gradio_client import Client
                        
                        client = Client("ACE-Step/ACE-Step-v1.5", hf_token=st.session_state.hf_api_key if st.session_state.hf_api_key else None)
                        result = client.predict(
                            caption=ace_step_prompt,
                            duration=30,
                            api_name="/generate_music"
                        )
                        
                        if result and "audio" in result:
                            audio_path = result["audio"]
                            with open(audio_path, "rb") as f:
                                audio_data = f.read()
                            st.success("✅ الموسيقى جاهزة (ACE-Step HF)!")
                            st.audio(audio_data, format="audio/wav")
                        else:
                            st.error("لم يتم استلام ملف صوتي من Hugging Face.")
                    except Exception as e:
                        st.error(f"وقع مشكل مع Hugging Face: {e}")
        
        else: # خادم محلي
            st.info("💡 هذا الخيار يعمل فقط إذا كنت تشغل تطبيق Streamlit محلياً على جهازك (وليس على Streamlit Cloud) وتشغل خادم ACE-Step على المنفذ 8001.")
            ace_step_prompt = st.text_area("وصف الموسيقى (ACE-Step):", height=100, placeholder="مثال: a happy summer pop song")
            
            if st.button("🎵 توليد الموسيقى (ACE-Step محلي)", use_container_width=True):
                with st.spinner("جاري التوليد عبر الخادم المحلي..."):
                    try:
                        ace_api_url = "http://localhost:8001/generate"
                        payload = {"prompt": ace_step_prompt, "duration": 30}
                        res = requests.post(ace_api_url, json=payload, timeout=10)
                        res.raise_for_status()
                        result = res.json()
                        audio_url = result.get("audio_url") or result.get("audio_path")
                        
                        if audio_url:
                            st.success("✅ الموسيقى جاهزة (ACE-Step محلي)!")
                            st.audio(audio_url, format="audio/wav")
                        else:
                            st.error("لم يتم العثور على رابط الصوت في استجابة ACE-Step.")
                    except requests.exceptions.ConnectionError:
                        st.error("تعذر الاتصال بـ ACE-Step المحلي. تأكد من تشغيله على المنفذ 8001.")
                    except Exception as e:
                        st.error(f"وقع مشكل فـ ACE-Step: {e}")
                    
    else: # رفع موسيقى جاهزة
        uploaded_music = st.file_uploader("ارفع ملف الموسيقى (MP3/WAV)", type=["mp3", "wav"])
        if uploaded_music is not None:
            st.success("✅ تم رفع الموسيقى بنجاح! التوليد تلغى.")
            st.audio(uploaded_music, format="audio/wav")
