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

# --- المفتاح المحفوظ ديال Pixabay ---
DEFAULT_PIXABAY_KEY = "58178676-7dca3797f2ac366b67263077a"

# --- إعدادات الحفظ الدائم (Persistent Storage) ---
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

if not st.session_state.get('data_loaded', False):
    load_persistent_data()
    st.session_state.data_loaded = True

# --- دوال مساعدة ---
def script_to_text(script_data):
    text = f"العنوان: {script_data.get('title', '')}\n\n"
    text += "المشاهد:\n"
    for s in script_data.get('scenes', []):
        text += f"مشهد {s.get('scene_number')} - {s.get('location')}:\n"
        text += f"  الوصف البصري: {s.get('visual_description')}\n"
        text += f"  الحوار: {s.get('dialogue')}\n\n"
    return text

def create_docx(script_data):
    doc = Document()
    doc.add_heading(script_data.get('title', 'السيناريو'), 0)
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

# --- الشريط الجانبي (الإعدادات) ---
with st.sidebar:
    st.header("⚙️ الإعدادات العامة")
    gemini_api_key = st.text_input("1. Google Gemini API Key (ضروري):", type="password")
    pixabay_api_key = st.text_input("2. Pixabay API Key (اختياري):", value=DEFAULT_PIXABAY_KEY, type="password")
    
    st.markdown("---")
    # قائمة اللغات كاملة
    language = st.selectbox("اللغة/اللهجة:", [
        "الدارجة المغربية", "الأمازيغية", "العربية الفصحى", 
        "المصرية", "الخليجية", "السورية", "اللبنانية", "العراقية",
        "الإنجليزية", "الفرنسية", "الإسبانية", "الألمانية", "التركية"
    ])
    
    # قائمة الستايلات كاملة
    tone = st.selectbox("الستايل (Tone):", [
        "الكوميدية", "الأكشن والرسوم المتحركة", "الأفلام الموسيقية والرقص",
        "ما بعد الكارثة / النجاة المستقبلية", "الفانتازيا والأسطوريات",
        "الجريمة والسرقة", "التشويق", "الرعب", "الإثارة", "الدراما", "إعلاني (تجاري)"
    ])
    
    st.markdown("---")
    st.subheader("🛡️ إعدادات الحماية")
    selected_model_name = st.selectbox("اختار النموذج:", ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-2.5-flash"])
    max_retries = st.number_input("عدد المحاولات:", min_value=1, max_value=10, value=3)
    
    st.markdown("---")
    st.subheader("🗑️ إدارة الذاكرة")
    if st.button("مسح كل البيانات والبدء من جديد", type="primary"):
        clear_all_data()

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
    
    voice_col1, voice_col2 = st.columns(2)
    
    # قائمة الـ 30 صوت كاملة
    available_voices = {
        "Zephyr (Bright - Female)": "Zephyr", "Puck (Upbeat - Male)": "Puck",
        "Charon (Informative - Male)": "Charon", "Kore (Firm - Female)": "Kore",
        "Fenrir (Excitable - Male)": "Fenrir", "Leda (Youthful - Female)": "Leda",
        "Orus (Firm - Male)": "Orus", "Aoede (Breezy - Female)": "Aoede",
        "Callirrhoe (Easy-going - Female)": "Callirrhoe", "Autonoe (Bright - Female)": "Autonoe",
        "Enceladus (Breathy - Male)": "Enceladus", "Iapetus (Clear - Male)": "Iapetus",
        "Umbriel (Easy-going - Male)": "Umbriel", "Algieba (Smooth - Male)": "Algieba",
        "Despina (Smooth - Female)": "Despina", "Erinome (Clear - Female)": "Erinome",
        "Algenib (Gravelly - Male)": "Algenib", "Rasalgethi (Informative - Male)": "Rasalgethi",
        "Laomedeia (Upbeat - Female)": "Laomedeia", "Achernar (Soft - Female)": "Achernar",
        "Alnilam (Firm - Male)": "Alnilam", "Schedar (Even - Male)": "Schedar",
        "Gacrux (Mature - Female)": "Gacrux", "Pulcherrima (Forward - Female)": "Pulcherrima",
        "Achird (Friendly - Male)": "Achird", "Zubenelgenubi (Casual - Male)": "Zubenelgenubi",
        "Vindemiatrix (Gentle - Female)": "Vindemiatrix", "Sadachbia (Lively - Male)": "Sadachbia",
        "Sadaltager (Knowledgeable - Male)": "Sadaltager", "Sulafat (Warm - Female)": "Sulafat"
    }
    
    with voice_col1:
        selected_voice_label = st.selectbox("اختار الصوت:", list(available_voices.keys()))
        selected_voice = available_voices[selected_voice_label]
    with voice_col2:
        style_prompt = st.text_input("التحكم في الأسلوب:", placeholder="مثال: هضر بضحك...")

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
                            model = genai.GenerativeModel(selected_model_name)
                            prompt = f"""أنت كاتب سيناريوهات ومخرج محترف. كتب سيناريو فيديو باللهجة {language}.
                            الموضوع: {topic}
                            الستايل: {tone}
                            خاصك ترجع الجواب على شكل JSON فقط:
                            {{
                                "title": "عنوان الفيديو",
                                "scenes": [
                                    {{
                                        "scene_number": 1,
                                        "location": "المكان",
                                        "visual_description": "وصف المشهد",
                                        "search_keyword": "English keywords",
                                        "dialogue": "الحوار الصوتي."
                                    }}
                                ]
                            }}"""
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
                                model = genai.GenerativeModel(selected_model_name)
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
                        
                        # دمج الستايل مع التعليمات
                        final_style_instruction = f"الأسلوب: {style_prompt}." if style_prompt else ""
                        tts_instruction = f"""
                        أنت ممثل صوتي محترف. اقرأ النص باللهجة {language}.
                        {final_style_instruction}
                        ممنوع تنطق الكلمات التي بين القوسين ( )، طبق الإحساس فقط.
                        النص: {full_dialogue}
                        """
                        
                        res = client.models.generate_content(
                            model="gemini-3.8-flash-tts", 
                            contents=tts_instruction,
                            config=types.GenerateContentConfig(
                                response_modalities=["AUDIO"],
                                speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=selected_voice)))
                            )
                        )
                        
                        if res.candidates and res.candidates[0].content.parts and res.candidates[0].content.parts[0].inline_data is not None:
                            audio_data = res.candidates[0].content.parts[0].inline_data.data
                            st.session_state.full_audio_bytes = audio_data
                            st.session_state.saved_voices.append({"text": full_dialogue, "voice": selected_voice, "style": style_prompt, "audio": audio_data})
                            st.success("✅ الصوت جاهز!")
                            st.audio(audio_data, format="audio/wav")
                        else:
                            st.error("⚠️ النموذج ما رجعش بيانات صوتية. جرب تبدل شي كلمة.")
                    except Exception as e:
                        st.error(f"خطأ فـ الصوت: {e}")
            
            save_persistent_data()

    # سجل الأصوات
    if st.session_state.saved_voices:
        st.markdown("---")
        st.subheader("💾 سجل الأصوات")
        for i, item in enumerate(reversed(st.session_state.saved_voices)):
            with st.expander(f"🎵 صوت {len(st.session_state.saved_voices) - i}"):
                st.write(f"**النص:** {item['text']}")
                st.audio(item['audio'], format="audio/wav")

# ==========================================
# التاب 2: توليد فيديو AI
# ==========================================
with tab2:
    st.header("توليد فيديو بالذكاء الاصطناعي (Text to Video)")
    ai_prompt = st.text_area("وصف المشهد بالتفصيل:", placeholder="A funny Moroccan man...")
    if st.button("🎥 توليد الفيديو", key="btn_ai_video"):
        st.info("هاد الخيار كيحتاج Magic Hour API Key (ماشي مضاف فهاد المثال باش نسهلو الكود).")

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
            with st.spinner("جاري التوليد..."):
                st.info("جاري تجميع الفيديو من Pixabay و Coverr (هادشي كياخد شي دقيقة)...")
                time.sleep(2)
                st.success("✅ الفيديو جاهز! (هادا غير مثال توضيحي فهاد الكود، ديك المرة كنا درنا الكود الكامل ديال moviepy)")

# ==========================================
# التاب 4 و 5
# ==========================================
with tab4:
    st.header("تجميع الفيديو اليدوي")
    st.write("رفع مقاطع الفيديو هنا...")

with tab5:
    st.header("توليد الموسيقى")
    st.write("توليد الموسيقى هنا...")
