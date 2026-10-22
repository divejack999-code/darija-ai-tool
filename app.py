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

# --- الشريط الجانبي ---
with st.sidebar:
    st.header("⚙️ الإعدادات العامة")
    gemini_api_key = st.text_input("1. Google Gemini API Key (ضروري):", type="password")
    
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
    st.subheader("🛡️ إعدادات الحماية")
    selected_model_name = st.selectbox("اختار النموذج:", ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-2.5-flash"])
    
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

    # --- جديد: خيار رفع الصوت الجاهز ---
    st.markdown("---")
    st.subheader("📤 رفع الصوت الجاهز (اختياري)")
    st.write("إلا كنتي صايبتي الصوت من قبل وبغيتي تستعملو بلا ما تصرف الكوطا، ارفعو هنا:")
    uploaded_audio_file = st.file_uploader("ارفع ملف الصوت (MP3/WAV)", type=["mp3", "wav"])
    
    if uploaded_audio_file is not None:
        # إلا رفع المستخدم صوت، كنحطوه ديريكت فـ الذاكرة ونحفظوه
        st.session_state.full_audio_bytes = uploaded_audio_file.read()
        save_persistent_data()
        st.success("✅ تم رفع الصوت بنجاح! التابات لخرين غادي يستعملو هاد الصوت.")
        st.audio(st.session_state.full_audio_bytes, format="audio/wav")

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
    st.info("هاد الخيار كيحتاج Magic Hour API Key (تقدر تزيدو فالشريط الجانبي).")

# ==========================================
# التاب 3: التوليد الأوتوماتيكي
# ==========================================
with tab3:
    st.header("🎬 التوليد الأوتوماتيكي للفيديو")
    if not st.session_state.script_data or not st.session_state.full_audio_bytes:
        st.warning("⚠️ خاصك تكون واجد السيناريو والصوت (سواء ولدتيهم ولا رفعتياهم فـ التاب 1).")
    else:
        st.success("✅ السيناريو والصوت واجدين فـ الذاكرة!")
        if st.button("🚀 بدء التوليد الأوتوماتيكي", use_container_width=True):
            with st.spinner("جاري التوليد..."):
                st.info("جاري البحث وتحميل الفيديوهات (محاكاة)...")
                time.sleep(2)
                st.success("✅ الفيديو جاهز! (تقدر تزيد الكود ديال moviepy هنا).")

# ==========================================
# التاب 4: تجميع الفيديو يدوي + رفع الصور
# ==========================================
with tab4:
    st.header("🧩 تجميع الفيديو (رفع يدوي)")
    st.write("تقدر ترفع الصور والفيديوهات اللي صايبتي من قبل، وتزيد عليهم الصوت اللي فـ التاب 1.")
    
    uploaded_images = st.file_uploader("تحميل الصور (JPG, PNG) باش نديرو ليهم حركة الكاميرا:", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    uploaded_videos = st.file_uploader("تحميل مقاطع الفيديو (MP4, MOV):", type=["mp4", "mov"], accept_multiple_files=True)
    
    if st.button("🚀 تجميع ودمج (مع الصوت المحفوظ)", use_container_width=True):
        if not uploaded_images and not uploaded_videos:
            st.warning("عافاك حمل على الأقل شي صورة ولا شي فيديو.")
        else:
            with st.spinner("جاري تجميع الفيديو..."):
                try:
                    st.info("جاري تجميع الملفات (هادا مثال توضيحي، الكود الحقيقي كيقص ويركب بـ moviepy).")
                    time.sleep(2)
                    st.success("✅ الفيديو النهائي جاهز!")
                    # هنا كتحط الكود ديال MoviePy اللي كيركب الصور والفيديوهات مع st.session_state.full_audio_bytes
                except Exception as e:
                    st.error(f"وقع مشكل: {e}")

# ==========================================
# التاب 5: توليد الموسيقى + رفع الموسيقى
# ==========================================
with tab5:
    st.header("🎵 الموسيقى")
    st.write("توليد الموسيقى بالذكاء الاصطناعي أو رفع موسيقى جاهزة للاستعمال.")
    
    # 1. خيار رفع موسيقى جاهزة
    st.subheader("📤 رفع موسيقى جاهزة (اختياري)")
    uploaded_music = st.file_uploader("ارفع ملف الموسيقى (MP3/WAV)", type=["mp3", "wav"])
    if uploaded_music is not None:
        st.success("✅ تم رفع الموسيقى! (تقدر تستعملها فالتجميع)")
        st.audio(uploaded_music, format="audio/wav")
    
    st.markdown("---")
    
    # 2. توليد موسيقى بالذكاء الاصطناعي
    st.subheader("🤖 توليد موسيقى بالذكاء الاصطناعي")
    if not gemini_api_key:
        st.warning("⚠️ عافاك دخل Google Gemini API Key.")
    else:
        music_prompt = st.text_area("وصف الموسيقى:", height=100, placeholder="مثال: موسيقى هادئة...")
        
        if st.button("🎵 توليد الموسيقى", use_container_width=True):
            with st.spinner("جاري التوليد..."):
                try:
                    from google import genai as google_genai
                    client = google_genai.Client(api_key=gemini_api_key)
                    res = client.models.generate_content(model="lyria-3-clip-preview", contents=music_prompt)
                    
                    audio_data = None
                    for part in res.parts:
                        if part.inline_data is not None:
                            audio_data = part.inline_data.data
                            break
                    
                    if audio_data:
                        st.success("✅ الموسيقى جاهزة!")
                        st.audio(audio_data, format="audio/mp3")
                        st.download_button("⬇️ تحميل", data=audio_data, file_name="music.mp3", mime="audio/mpeg")
                    else:
                        st.error("⚠️ ما رجعش صوت.")
                except Exception as e:
                    st.error(f"وقع مشكل: {e}")
