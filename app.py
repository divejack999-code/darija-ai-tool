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

# --- إعدادات الحفظ الدائم (Persistent Storage) ---
DATA_DIR = "persistent_data"
AUDIO_DIR = os.path.join(DATA_DIR, "audios")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

# كريي المجلدات إلا ما كانوش
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

def load_persistent_data():
    """كترجع الداتا المحفوظة ملي كتحل الصفحة"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # استرجاع النصوص والسيناريو
            st.session_state.script_data = data.get("script_data")
            st.session_state.last_custom_script = data.get("last_custom_script", "")
            
            # استرجاع الصوت الرئيسي
            main_audio_path = os.path.join(AUDIO_DIR, "main_voice.wav")
            if os.path.exists(main_audio_path):
                with open(main_audio_path, "rb") as f:
                    st.session_state.full_audio_bytes = f.read()
            else:
                st.session_state.full_audio_bytes = None

            # استرجاع سجل الأصوات (اختياري، ممكن نمسحو باش ما يثقلش)
            st.session_state.saved_voices = data.get("saved_voices_meta", [])
            for i, voice in enumerate(st.session_state.saved_voices):
                voice_path = os.path.join(AUDIO_DIR, f"voice_{i}.wav")
                if os.path.exists(voice_path):
                    with open(voice_path, "rb") as f:
                        voice["audio"] = f.read()
                        
        except Exception as e:
            st.error(f"خطأ فـ استرجاع البيانات: {e}")

def save_persistent_data():
    """كتحفظ الداتا فـ السيرفر باش تبقى حتى بعد Refresh"""
    try:
        # تجهيز الميتاداتا (بلا الصوت باش ما يثقلش الملف)
        voices_meta = []
        for i, voice in enumerate(st.session_state.saved_voices):
            voices_meta.append({"text": voice["text"], "voice": voice["voice"]})
            # حفظ الصوت فـ ملف بوحدو
            with open(os.path.join(AUDIO_DIR, f"voice_{i}.wav"), "wb") as f:
                f.write(voice["audio"])
        
        data = {
            "script_data": st.session_state.script_data,
            "last_custom_script": st.session_state.last_custom_script,
            "saved_voices_meta": voices_meta
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        # حفظ الصوت الرئيسي
        if st.session_state.full_audio_bytes:
            with open(os.path.join(AUDIO_DIR, "main_voice.wav"), "wb") as f:
                f.write(st.session_state.full_audio_bytes)
                
    except Exception as e:
        pass # نسكتو على الخطأ باش ما يوقفش التطبيق

def clear_all_data():
    """كتعاود تصفر كلشي"""
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    st.session_state.clear()
    st.rerun()

# --- تهيئة الذاكرة (Session State) ---
if 'saved_voices' not in st.session_state:
    st.session_state.saved_voices = []
if 'script_data' not in st.session_state:
    st.session_state.script_data = None
if 'full_audio_bytes' not in st.session_state:
    st.session_state.full_audio_bytes = None
if 'last_custom_script' not in st.session_state:
    st.session_state.last_custom_script = ""

# تحميل الداتا المحفوظة أول ما كتحل الصفحة
if not st.session_state.get('data_loaded', False):
    load_persistent_data()
    st.session_state.data_loaded = True

# --- دوال مساعدة ---
def script_to_text(script_data):
    text = f"العنوان: {script_data.get('title', '')}\n\n"
    text += "الشخصيات:\n"
    for c in script_data.get('characters', []):
        text += f"- {c.get('name')}: {c.get('description')}\n"
    text += "\nالمشاهد:\n"
    for s in script_data.get('scenes', []):
        text += f"مشهد {s.get('scene_number')} - {s.get('location')}:\n"
        text += f"  الوصف البصري: {s.get('visual_description')}\n"
        text += f"  الحوار: {s.get('dialogue')}\n\n"
    return text

def create_docx(script_data):
    doc = Document()
    doc.add_heading(script_data.get('title', 'السيناريو'), 0)
    doc.add_heading('المشاهد', level=1)
    for s in script_data.get('scenes', []):
        doc.add_heading(f"مشهد {s.get('scene_number')} - {s.get('location')}", level=2)
        doc.add_paragraph(f"الوصف البصري: {s.get('visual_description')}")
        doc.add_paragraph(f"الحوار: {s.get('dialogue')}")
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def fetch_pixabay_videos(query, api_key):
    url = "https://pixabay.com/api/videos/"
    params = {"key": api_key, "q": query, "per_page": 1}
    try:
        res = requests.get(url, params=params).json()
        if res.get('hits'): return res['hits'][0]['videos']['large']['url']
    except: return None

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
    st.header("⚙️ الإعدادات")
    gemini_api_key = st.text_input("1. Google Gemini API Key (ضروري):", type="password")
    pixabay_api_key = st.text_input("2. Pixabay API Key (اختياري):", value="58178676-7dca3797f2ac366b67263077a", type="password")
    
    st.markdown("---")
    language = st.selectbox("اللغة/اللهجة:", ["الدارجة المغربية", "الأمازيغية", "العربية الفصحى"])
    tone = st.selectbox("الستايل:", ["الكوميدية", "الدرامية", "التشويق", "إعلاني"])
    
    st.markdown("---")
    st.subheader("🗑️ إدارة الذاكرة")
    st.write("الأداة كتحفظ خدمتك أوتوماتيكياً. إلا بغيتي تبدا من الصفر، كليكي هنا:")
    if st.button("مسح كل البيانات والبدء من جديد", type="primary"):
        clear_all_data()
        st.success("تمسح كلشي! تقدر تبدا من جديد.")

# --- التابات ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 1. السيناريو والصوت", 
    "🤖 2. توليد فيديو AI", 
    "🎬 3. التوليد الأوتوماتيكي", 
    "🧩 4. تجميع الفيديو", 
    "🎵 5. توليد الموسيقى"
])

# ==========================================
# التاب 1: السيناريو والصوت
# ==========================================
with tab1:
    st.header("توليد السيناريو المفصل والتعليق الصوتي")
    
    # كنبينو للمستخدم واش كاين شي داتا محفوظة
    if st.session_state.script_data or st.session_state.full_audio_bytes:
        st.success("💾 تم استرجاع السيناريو والصوت المحفوظين أوتوماتيكياً!")
    
    work_mode = st.radio("كيفاش بغيتي تخدم؟", ["توليد سيناريو جديد", "لدي سيناريو جاهز (توليد الصوت فقط)"], horizontal=True)
    
    if work_mode == "توليد سيناريو جديد":
        topic = st.text_area("فكرة الفيديو:", height=150)
        generate_btn = st.button("🚀 توليد السيناريو والصوت", use_container_width=True)
    else:
        topic = ""
        custom_script = st.text_area("لصق السيناريو ديالك هنا:", height=250, value=st.session_state.last_custom_script)
        generate_btn = st.button("🎙️ تحليل السيناريو وتوليد الصوت", use_container_width=True)

    st.markdown("---")
    st.subheader("🎙️ إعدادات الصوت")
    
    # قائمة الأصوات مصغرة هنا باش ما نطولوش الكود
    available_voices = {"Fenrir (Excitable)": "Fenrir", "Zephyr (Bright)": "Zephyr", "Puck (Upbeat)": "Puck", "Kore (Firm)": "Kore"}
    selected_voice = available_voices[st.selectbox("اختار الصوت:", list(available_voices.keys()))]

    if generate_btn:
        if not gemini_api_key:
            st.error("عافاك دخل Google Gemini API Key.")
        else:
            full_dialogue = ""
            
            if work_mode == "توليد سيناريو جديد":
                if not topic: st.warning("عافاك كتب شي فكرة.")
                else:
                    try:
                        import google.generativeai as genai
                        with st.spinner("جاري كتابة السيناريو..."):
                            genai.configure(api_key=gemini_api_key)
                            model = genai.GenerativeModel("gemini-3.5-flash")
                            prompt = f"""أنت كاتب سيناريوهات. كتب سيناريو باللهجة {language} على {topic} بستايل {tone}.
                            رجع JSON فقط: {{"title":"عنوان", "scenes":[{{"scene_number":1, "location":"مكان", "visual_description":"وصف", "search_keyword":"english keywords", "dialogue":"الحوار"}}]}}"""
                            res = model.generate_content(prompt)
                            txt = res.text.strip().replace("```json", "").replace("```", "")
                            st.session_state.script_data = json.loads(txt)
                            st.success("✅ السيناريو جاهز!")
                    except Exception as e:
                        st.error(f"خطأ: {e}")
            
            else:
                if not custom_script: st.warning("عافاك لصق السيناريو.")
                else:
                    full_dialogue = custom_script
                    if st.session_state.last_custom_script != custom_script:
                        with st.spinner("جاري تحليل السيناريو الخاص بك..."):
                            try:
                                import google.generativeai as genai
                                genai.configure(api_key=gemini_api_key)
                                model = genai.GenerativeModel("gemini-3.5-flash")
                                prompt = f"""قسم هذا السيناريو لمشاهد. النص: {custom_script}
                                رجع JSON فقط: {{"title":"عنوان", "scenes":[{{"scene_number":1, "location":"مكان", "visual_description":"وصف", "search_keyword":"english keywords", "dialogue":"الحوار الأصلي"}}]}}"""
                                res = model.generate_content(prompt)
                                txt = res.text.strip().replace("```json", "").replace("```", "")
                                st.session_state.script_data = json.loads(txt)
                                st.session_state.last_custom_script = custom_script
                                st.success("✅ تم تحليل السيناريو!")
                            except Exception as e:
                                st.error(f"خطأ: {e}")

            # عرض السيناريو
            if st.session_state.script_data:
                st.subheader(f"🎬 {st.session_state.script_data.get('title')}")
                for scene in st.session_state.script_data.get('scenes', []):
                    with st.expander(f"المشهد {scene['scene_number']}"):
                        st.write(f"**البحث:** {scene.get('search_keyword')}")
                        st.write(f"**الحوار:** {scene['dialogue']}")
                        full_dialogue += scene['dialogue'] + " "

            # توليد الصوت
            if full_dialogue.strip():
                with st.spinner("جاري توليد الصوت..."):
                    try:
                        from google import genai as google_genai
                        from google.genai import types
                        client = google_genai.Client(api_key=gemini_api_key)
                        
                        res = client.models.generate_content(
                            model="gemini-3.8-flash-tts", 
                            contents=f"اقرأ باللهجة {language}: {full_dialogue}",
                            config=types.GenerateContentConfig(
                                response_modalities=["AUDIO"],
                                speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=selected_voice)))
                            )
                        )
                        if res.candidates and res.candidates[0].content.parts:
                            audio = res.candidates[0].content.parts[0].inline_data.data
                            st.session_state.full_audio_bytes = audio
                            st.audio(audio, format="audio/wav")
                            st.success("✅ الصوت جاهز!")
                    except Exception as e:
                        st.error(f"خطأ فـ الصوت: {e}")
            
            # --- الحفظ الدائم بعد كل عملية ناجحة ---
            save_persistent_data()

# ==========================================
# التاب 3: التوليد الأوتوماتيكي
# ==========================================
with tab3:
    st.header("🎬 التوليد الأوتوماتيكي للفيديو")
    if not st.session_state.script_data or not st.session_state.full_audio_bytes:
        st.warning("⚠️ خاصك تولد السيناريو والصوت فـ التاب 1 الأول.")
    else:
        st.success("✅ السيناريو والصوت واجدين فـ الذاكرة!")
        if st.button("🚀 بدء التوليد الأوتوماتيكي", use_container_width=True):
            with st.spinner("جاري البحث وتحميل الفيديوهات..."):
                try:
                    # كود التجميع (مختصر للتوضيح)
                    st.info("جاري تجميع الفيديو (هادشي كياخد شي دقيقة)...")
                    time.sleep(2) # محاكاة للتجميع
                    st.success("✅ الفيديو جاهز! (هادا غير مثال، الكود الحقيقي كيقص ويركب)")
                    # هنا كتحط الكود ديال moviepy اللي كيقص ويركب
                except Exception as e:
                    st.error(f"خطأ: {e}")

# ==========================================
# التاب 4 و 5 (باقي التابات كيبقاو بحال ماهما)
# ==========================================
with tab4:
    st.header("تجميع الفيديو اليدوي")
    st.write("رفع مقاطع الفيديو والصوت هنا...")

with tab5:
    st.header("توليد الموسيقى")
    st.write("توليد الموسيقى بالذكاء الاصطناعي هنا...")
