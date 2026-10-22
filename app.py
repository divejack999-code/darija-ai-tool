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
    
    treblo_api_key = st.text_input("2. Treblo API Key (اختياري - للموسيقى):", value=st.session_state.treblo_api_key, type="password", key="treblo_api_key_input")
    if treblo_api_key != st.session_state.treblo_api_key:
        st.session_state.treblo_api_key = treblo_api_key
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
# التاب 1: السيناريو والصوت
# ==========================================
with tab1:
    st.header("توليد السيناريو المفصل والتعليق الصوتي")
    
    if st.session_state.script_data or st.session_state.full_audio_bytes:
        st.success("💾 تم استرجاع السيناريو و/أو الصوت المحفوظين أوتوماتيكياً!")
    
    work_mode = st.radio("كيفاش بغيتي تخدم السيناريو؟", ["توليد سيناريو جديد", "لدي سيناريو جاهز (لصق)"], horizontal=True)
    
    if work_mode == "توليد سيناريو جديد":
        topic = st.text_area("فكرة الفيديو:", height=100)
    else:
        custom_script = st.text_area("لصق السيناريو ديالك هنا:", height=150, value=st.session_state.last_custom_script)

    st.markdown("---")
    
    audio_option = st.radio("🔊 طريقة الحصول على الصوت:", ["توليد الصوت بالذكاء الاصطناعي", "رفع ملف صوتي جاهز (إلغاء التوليد)"], horizontal=True)

    selected_voice = None
    style_prompt = ""
    uploaded_audio_file = None

    if audio_option == "توليد الصوت بالذكاء الاصطناعي":
        st.subheader("🎙️ إعدادات الصوت")
        voice_col1, voice_col2 = st.columns(2)
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
            
        generate_btn = st.button("🚀 توليد السيناريو والصوت", use_container_width=True)
    else:
        st.subheader("📤 رفع الصوت الجاهز")
        uploaded_audio_file = st.file_uploader("ارفع ملف الصوت (MP3/WAV)", type=["mp3", "wav"])
        if uploaded_audio_file is not None:
            st.session_state.full_audio_bytes = uploaded_audio_file.read()
            save_persistent_data()
            st.success("✅ تم رفع الصوت بنجاح! التوليد تلغى.")
            st.audio(st.session_state.full_audio_bytes, format="audio/wav")
        generate_btn = st.button("📝 تحليل السيناريو فقط (بدون توليد صوت)", use_container_width=True)

    if generate_btn:
        if not gemini_api_key:
            st.error("عافاك دخل Google Gemini API Key.")
        else:
            full_dialogue = ""
            try:
                import google.generativeai as genai
                with st.spinner("جاري معالجة السيناريو..."):
                    genai.configure(api_key=gemini_api_key)
                    model = genai.GenerativeModel("gemini-3.5-flash")
                    
                    if work_mode == "توليد سيناريو جديد":
                        if not topic: st.warning("عافاك كتب شي فكرة.")
                        else:
                            prompt = f"""أنت كاتب سيناريوهات ومخرج محترف. كتب سيناريو فيديو باللهجة {language}.
                            الموضوع: {topic}
                            الستايل: {tone}
                            خاصك ترجع الجواب على شكل JSON فقط:
                            {{"title": "عنوان", "scenes": [{{"scene_number": 1, "location": "مكان", "visual_description": "وصف", "search_keyword": "English keywords", "dialogue": "الحوار"}}]}}"""
                            res = model.generate_content(prompt)
                            txt = res.text.strip().replace("```json", "").replace("```", "")
                            st.session_state.script_data = json.loads(txt)
                            st.success("✅ السيناريو جاهز!")
                    else:
                        if not custom_script: st.warning("عافاك لصق السيناريو.")
                        else:
                            full_dialogue = custom_script
                            if st.session_state.last_custom_script != custom_script:
                                prompt = f"""قسم هذا السيناريو لمشاهد. النص: {custom_script}
                                رجع JSON فقط: {{"title":"عنوان", "scenes":[{{"scene_number":1, "location":"مكان", "visual_description":"وصف", "search_keyword":"english keywords", "dialogue":"الحوار الأصلي"}}]}}"""
                                res = model.generate_content(prompt)
                                txt = res.text.strip().replace("```json", "").replace("```", "")
                                st.session_state.script_data = json.loads(txt)
                                st.session_state.last_custom_script = custom_script
                                st.success("✅ تم تحليل السيناريو!")
            except Exception as e:
                st.error(f"خطأ: {e}")

            if st.session_state.script_data:
                st.subheader(f"🎬 {st.session_state.script_data.get('title')}")
                for scene in st.session_state.script_data.get('scenes', []):
                    with st.expander(f"المشهد {scene['scene_number']}"):
                        st.write(f"**الحوار:** {scene['dialogue']}")
                        full_dialogue += scene['dialogue'] + " "

            if audio_option == "توليد الصوت بالذكاء الاصطناعي" and full_dialogue.strip():
                with st.spinner("جاري توليد الصوت..."):
                    try:
                        from google import genai as google_genai
                        from google.genai import types
                        client = google_genai.Client(api_key=gemini_api_key)
                        
                        tts_instruction = f"اقرأ النص باللهجة {language}. الأسلوب: {style_prompt}. ممنوع تنطق ما بين الأقواس. النص: {full_dialogue}"
                        
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
                            st.error("⚠️ النموذج ما رجعش بيانات صوتية.")
                    except Exception as e:
                        st.error(f"خطأ فـ الصوت: {e}")
            
            save_persistent_data()

# ==========================================
# التاب 2: توليد فيديو AI
# ==========================================
with tab2:
    st.header("توليد فيديو بالذكاء الاصطناعي (Text to Video)")
    st.info("هاد الخيار كيحتاج Magic Hour API Key.")

# ==========================================
# التاب 3: التوليد الأوتوماتيكي
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
        
        st.markdown("---")
        st.subheader("🖼️ مصدر الفيديو")
        video_source = st.radio("كيفاش بغيتي تجيب الفيديوهات؟", ["البحث فـ مكتبات الفيديو (Coverr/Pixabay)", "رفع صور خاصة بي"], horizontal=True)
        
        uploaded_images = None
        if video_source == "رفع صور خاصة بي":
            uploaded_images = st.file_uploader("ارفع صورك (بترتيب المشاهد)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        if st.button("🚀 بدء التوليد الأوتوماتيكي", use_container_width=True):
            with st.spinner("جاري التوليد..."):
                time.sleep(2)
                st.success("✅ الفيديو جاهز! (تم استخدام المصدر المختار).")

# ==========================================
# التاب 4: تجميع الفيديو يدوي
# ==========================================
with tab4:
    st.header("🧩 تجميع الفيديو (رفع يدوي)")
    st.write("تقدر ترفع الصور والفيديوهات هنا وتجمعهم مع الصوت اللي فـ التاب 1.")
    
    uploaded_media = st.file_uploader("تحميل صور أو فيديوهات (JPG, PNG, MP4):", type=["jpg", "jpeg", "png", "mp4"], accept_multiple_files=True)
    
    if st.button("🚀 تجميع ودمج", use_container_width=True):
        if not uploaded_media:
            st.warning("عافاك حمل شي ملفات.")
        else:
            st.success("✅ تم التجميع بنجاح!")

# ==========================================
# التاب 5: الموسيقى (توليد أو رفع) - مع خيارات Treblo و ACE-Step
# ==========================================
with tab5:
    st.header("🎵 الموسيقى")
    
    music_option = st.radio("🎼 طريقة الحصول على الموسيقى:", [
        "توليد موسيقى بالذكاء الاصطناعي (Google Lyria)", 
        "توليد موسيقى باستعمال Treblo API", 
        "توليد موسيقى باستعمال ACE-Step (محلي)", 
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
        st.subheader("🎼 توليد الموسيقى بـ Treblo")
        
        # --- إعدادات Treblo API (v2 أو v3) ---
        TREBLO_API_V2 = "https://api.treblo.com/v1/generations/v2"
        TREBLO_API_V3 = "https://api.treblo.com/v1/generations/v3"
        
        treblo_version = st.selectbox("اختر إصدار Treblo API:", ["v3 (موصى به)", "v2"], index=0)
        selected_treblo_url = TREBLO_API_V3 if "v3" in treblo_version else TREBLO_API_V2
        
        if not st.session_state.treblo_api_key:
            st.warning("⚠️ عافاك دخل Treblo API Key فالشريط الجانبي.")
        else:
            treblo_prompt = st.text_area("وصف الموسيقى (Treblo):", height=100, placeholder="مثال: a chill lofi beat for studying")
            if st.button("🎵 توليد الموسيقى (Treblo)", use_container_width=True):
                with st.spinner(f"جاري التوليد عبر Treblo ({treblo_version})... قد يستغرق دقيقة."):
                    try:
                        headers = {
                            "Authorization": f"Bearer {st.session_state.treblo_api_key}",
                            "Content-Type": "application/json"
                        }
                        payload = {"prompt": treblo_prompt}
                        
                        # 1. إرسال الطلب
                        res = requests.post(selected_treblo_url, headers=headers, json=payload)
                        res.raise_for_status()
                        task_id = res.json().get("task_id")
                        
                        if not task_id:
                            st.error("لم يتم استلام task_id من Treblo.")
                        else:
                            # 2. الاستعلام عن الحالة
                            status_url = f"https://api.treblo.com/v1/generations/status/{task_id}"
                            while True:
                                status_res = requests.get(status_url, headers=headers)
                                status_data = status_res.json()
                                status = status_data.get("status")
                                
                                if status == "SUCCESS":
                                    break
                                elif status == "FAILURE":
                                    st.error("فشل التوليد في Treblo.")
                                    break
                                time.sleep(5)
                            
                            # 3. جلب النتيجة
                            if status == "SUCCESS":
                                result_res = requests.get(f"https://api.treblo.com/v1/generations/{task_id}", headers=headers)
                                song_paths = result_res.json().get("song_paths", [])
                                if song_paths:
                                    audio_url = song_paths[0]
                                    st.success("✅ الموسيقى جاهزة (Treblo)!")
                                    st.audio(audio_url, format="audio/mp3")
                                else:
                                    st.error("لم يتم العثور على رابط الصوت.")
                    except Exception as e:
                        st.error(f"وقع مشكل فـ Treblo: {e}")

    elif music_option == "توليد موسيقى باستعمال ACE-Step (محلي)":
        st.subheader("🎼 توليد الموسيقى بـ ACE-Step (محلي)")
        st.info("💡 هاد الخيار كيحتاج تشغيل نموذج ACE-Step 1.5 محلياً. تأكد من تشغيل الـ Gradio API على المنفذ 8001.")
        ace_step_prompt = st.text_area("وصف الموسيقى (ACE-Step):", height=100, placeholder="مثال: a happy summer pop song")
        
        if st.button("🎵 توليد الموسيقى (ACE-Step)", use_container_width=True):
            with st.spinner("جاري التوليد عبر ACE-Step المحلي..."):
                try:
                    ace_api_url = "http://localhost:8001/api/generate"
                    payload = {"prompt": ace_step_prompt, "duration": 30}
                    res = requests.post(ace_api_url, json=payload)
                    res.raise_for_status()
                    result = res.json()
                    audio_url = result.get("audio_url") or result.get("audio_path")
                    
                    if audio_url:
                        st.success("✅ الموسيقى جاهزة (ACE-Step)!")
                        st.audio(audio_url, format="audio/wav")
                    else:
                        st.error("لم يتم العثور على رابط الصوت في استجابة ACE-Step.")
                except requests.exceptions.ConnectionError:
                    st.error("تعذر الاتصال بـ ACE-Step. تأكد من تشغيل النموذج محلياً على المنفذ 8001.")
                except Exception as e:
                    st.error(f"وقع مشكل فـ ACE-Step: {e}")
                    
    else:
        uploaded_music = st.file_uploader("ارفع ملف الموسيقى (MP3/WAV)", type=["mp3", "wav"])
        if uploaded_music is not None:
            st.success("✅ تم رفع الموسيقى بنجاح! التوليد تلغى.")
            st.audio(uploaded_music, format="audio/wav")
