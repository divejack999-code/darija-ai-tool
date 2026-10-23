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
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, VideoFileClip, CompositeVideoClip, ColorClip, vfx
from docx import Document

# --- إعدادات الواجهة ---
st.set_page_config(page_title="AI Studio: Darija & Amazigh", page_icon="🎬", layout="wide")
st.title("🎬 استوديو الذكاء الاصطناعي الشامل")

# --- المفاتيح المحفوظة (Defaults) ---
DEFAULT_ACESTEP_API_KEY = "821f692a10974eaa960316f37a9001f6"

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
            st.session_state.hf_api_key = data.get("hf_api_key", "")
            
            main_audio_path = os.path.join(AUDIO_DIR, "main_voice.wav")
            if os.path.exists(main_audio_path):
                with open(main_audio_path, "rb") as f:
                    st.session_state.full_audio_bytes = f.read()
            else:
                st.session_state.full_audio_bytes = None
        except Exception:
            pass

def save_persistent_data():
    try:
        data = {
            "script_data": st.session_state.script_data,
            "last_custom_script": st.session_state.last_custom_script,
            "gemini_api_key": st.session_state.get("gemini_api_key_input", ""),
            "acestep_api_key": st.session_state.get("acestep_api_key_input", DEFAULT_ACESTEP_API_KEY),
            "hf_api_key": st.session_state.get("hf_api_key_input", ""),
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
if 'script_data' not in st.session_state: st.session_state.script_data = None
if 'full_audio_bytes' not in st.session_state: st.session_state.full_audio_bytes = None
if 'last_custom_script' not in st.session_state: st.session_state.last_custom_script = ""
if 'saved_api_key' not in st.session_state: st.session_state.saved_api_key = ""
if 'acestep_api_key' not in st.session_state: st.session_state.acestep_api_key = DEFAULT_ACESTEP_API_KEY
if 'hf_api_key' not in st.session_state: st.session_state.hf_api_key = ""

if not st.session_state.get('data_loaded', False):
    load_persistent_data()
    st.session_state.data_loaded = True

# --- دوال مساعدة للبحث عن الفيديو ---
def search_pexels_videos(query, api_key, per_page=1):
    if not api_key: return None
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": per_page, "orientation": "portrait"}
    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        videos = res.json().get('videos', [])
        if videos:
            files = videos[0]['video_files']
            files.sort(key=lambda x: x.get('width', 0), reverse=True)
            return files[0]['link']
    except Exception:
        return None
    return None

def search_pixabay_videos(query, api_key, per_page=3):
    if not api_key: return None
    url = "https://pixabay.com/api/videos/"
    params = {"key": api_key, "q": query, "per_page": per_page, "video_type": "film"}
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        hits = res.json().get('hits', [])
        if hits:
            return hits[0]['videos']['large']['url']
    except Exception:
        return None
    return None

# --- الشريط الجانبي (الإعدادات) ---
with st.sidebar:
    st.header("⚙️ الإعدادات العامة")
    gemini_api_key = st.text_input("1. Google Gemini API Key (ضروري):", value=st.session_state.saved_api_key, type="password", key="gemini_api_key_input")
    if gemini_api_key != st.session_state.saved_api_key:
        st.session_state.saved_api_key = gemini_api_key
        save_persistent_data()
    
    acestep_api_key = st.text_input("2. ACE Music API Key (مجاني):", value=st.session_state.acestep_api_key, type="password", key="acestep_api_key_input")
    if acestep_api_key != st.session_state.acestep_api_key:
        st.session_state.acestep_api_key = acestep_api_key
        save_persistent_data()

    hf_api_key = st.text_input("3. Hugging Face API Key (اختياري):", value=st.session_state.hf_api_key, type="password", key="hf_api_key_input")
    if hf_api_key != st.session_state.hf_api_key:
        st.session_state.hf_api_key = hf_api_key
        save_persistent_data()
    
    st.markdown("---")
    st.subheader("🎬 إعدادات الفيديو النهائي")
    # هنا درنا إعدادات الفيديو فالسيدبار باش تكون واضحة
    aspect_ratio = st.selectbox("أبعاد الفيديو:", [
        "9:16 (ريلز/تيك توك)", 
        "16:9 (يوتيوب)", 
        "1:1 (مربع)", 
        "4:5 (إنستغرام)", 
        "4:3 (كلاسيكي)"
    ])
    
    quality = st.selectbox("جودة الفيديو:", ["1080p", "720p", "480p"])
    
    max_duration = st.slider("المدة القصوى للفيديو (ثانية):", min_value=10, max_value=3600, value=60, step=10, help="إذا كان الصوت أطول، سيتم قص الفيديو عند هذه المدة.")
    
    st.markdown("---")
    st.subheader("🔑 مفاتيح مكتبات الفيديو")
    st.info("هذه المفاتيح مجانية وضرورية للبحث عن فيديوهات.")
    pixabay_api_key = st.text_input("Pixabay API Key:", type="password", key="pixabay_key")
    pexels_api_key = st.text_input("Pexels API Key:", type="password", key="pexels_key")
    
    st.markdown("---")
    language = st.selectbox("اللغة/اللهجة:", ["الدارجة المغربية", "الأمازيغية", "العربية الفصحى", "الإنجليزية", "الفرنسية"])
    tone = st.selectbox("الستايل (Tone):", ["الكوميدية", "الدرامية", "التشويق", "الرعب", "إعلاني (تجاري)"])
    
    st.markdown("---")
    st.subheader("🗑️ إدارة الذاكرة")
    if st.button("مسح كل البيانات والبدء من جديد", type="primary"):
        clear_all_data()

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
        st.success("💾 تم استرجاع السيناريو و/أو الصوت المحفوظين أوتوماتيكياً!")
    
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
        if not gemini_api_key:
            st.error("عافاك دخل Google Gemini API Key.")
        else:
            full_dialogue = ""
            try:
                import google.generativeai as genai
                with st.spinner("جاري معالجة السيناريو..."):
                    genai.configure(api_key=gemini_api_key)
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    
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
                        st.write(f"**البحث:** {scene.get('search_keyword', 'N/A')}")
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
    st.info("هذا الخيار يتطلب مفتاح API لخدمة مثل RunwayML أو Magic Hour (غير مدمج حالياً).")

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
        st.info(f"⚙️ الإعدادات الحالية من الشريط الجانبي: الأبعاد **{aspect_ratio}**، الجودة **{quality}**، المدة القصوى **{max_duration} ثانية**.")
        
        st.markdown("---")
        st.subheader("🖼️ مصدر الفيديو")
        video_source = st.radio("كيفاش بغيتي تجيب الفيديوهات؟", ["البحث فـ مكتبات الفيديو (Pexels/Pixabay)", "رفع صور خاصة بي"], horizontal=True)
        
        uploaded_images = None
        if video_source == "رفع صور خاصة بي":
            uploaded_images = st.file_uploader("ارفع صورك (بترتيب المشاهد)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

        if st.button("🚀 بدء التوليد الأوتوماتيكي", use_container_width=True):
            if video_source == "البحث فـ مكتبات الفيديو (Pexels/Pixabay)" and not (pexels_api_key or pixabay_api_key):
                st.error("⚠️ عافاك دخل على الأقل مفتاح API واحد (Pexels أو Pixabay) فالشريط الجانبي باش نقدرو نقلبو على الفيديوهات.")
            elif video_source == "رفع صور خاصة بي" and not uploaded_images:
                st.error("⚠️ عافاك ارفع على الأقل صورة وحدة.")
            else:
                with st.spinner("جاري البحث، التحميل، والتجميع... هادشي ممكن ياخد شي دقيقة."):
                    try:
                        # 1. تحضير الصوت وقصه إذا كان أطول من المدة القصوى
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                            tmp_audio.write(st.session_state.full_audio_bytes)
                            audio_path = tmp_audio.name
                        
                        full_audio_clip = AudioFileClip(audio_path)
                        audio_duration = full_audio_clip.duration
                        
                        # تطبيق المدة القصوى
                        actual_duration = min(audio_duration, max_duration)
                        full_audio_clip = full_audio_clip.subclipped(0, actual_duration)
                        
                        scenes = st.session_state.script_data.get('scenes', [])
                        num_scenes = len(scenes)
                        
                        if num_scenes == 0:
                            st.error("ما كاينش مشاهد فـ السيناريو.")
                        else:
                            duration_per_scene = actual_duration / num_scenes
                            
                            # 2. إعدادات الأبعاد من الشريط الجانبي
                            aspect_map = {
                                "9:16 (ريلز/تيك توك)": (1080, 1920), 
                                "16:9 (يوتيوب)": (1920, 1080), 
                                "1:1 (مربع)": (1080, 1080),
                                "4:5 (إنستغرام)": (1080, 1350),
                                "4:3 (كلاسيكي)": (1440, 1080)
                            }
                            quality_map = {"480p": 480, "720p": 720, "1080p": 1080}
                            
                            target_h = quality_map[quality]
                            target_w = int(target_h * aspect_map[aspect_ratio][0] / aspect_map[aspect_ratio][1])
                            
                            video_clips = []
                            
                            # 3. معالجة كل مشهد
                            if video_source == "رفع صور خاصة بي":
                                for i, img_file in enumerate(uploaded_images[:num_scenes]): 
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                                        tmp_img.write(img_file.getvalue())
                                        img_path = tmp_img.name
                                    
                                    img = Image.open(img_path)
                                    img = img.resize((target_w, target_h))
                                    img_array = np.array(img)
                                    
                                    clip = ImageClip(img_array).with_duration(duration_per_scene)
                                    clip = clip.resized(lambda t: 1 + 0.05 * t)
                                    clip = clip.with_position('center')
                                    
                                    video_clips.append(clip)
                                    os.remove(img_path)
                            else:
                                for i, scene in enumerate(scenes):
                                    keyword = scene.get('search_keyword', 'abstract background')
                                    st.write(f"🔍 كنقلب على مشهد {i+1}: '{keyword}'...")
                                    
                                    video_url = None
                                    if pexels_api_key:
                                        video_url = search_pexels_videos(keyword, pexels_api_key)
                                    if not video_url and pixabay_api_key:
                                        video_url = search_pixabay_videos(keyword, pixabay_api_key)
                                    
                                    if video_url:
                                        vid_data = requests.get(video_url).content
                                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_vid:
                                            tmp_vid.write(vid_data)
                                            vid_path = tmp_vid.name
                                        
                                        clip = VideoFileClip(vid_path)
                                        
                                        if clip.duration >= duration_per_scene:
                                            clip = clip.subclipped(0, duration_per_scene)
                                        else:
                                            loop_count = int(duration_per_scene / clip.duration) + 1
                                            clip = concatenate_videoclips([clip] * loop_count).subclipped(0, duration_per_scene)
                                        
                                        # تغيير الأبعاد بشكل احترافي (Crop + Resize)
                                        clip = clip.resized(height=target_h)
                                        if clip.w < target_w:
                                            clip = clip.resized(width=target_w)
                                        clip = clip.cropped(x_center=clip.w/2, y_center=clip.h/2, width=target_w, height=target_h)
                                        
                                        video_clips.append(clip)
                                        os.remove(vid_path)
                                    else:
                                        st.warning(f"⚠️ ما لقيتش فيديو لـ '{keyword}'. غادي نستعملو خلفية سوداء.")
                                        clip = ColorClip(size=(target_w, target_h), color=(0,0,0), duration=duration_per_scene)
                                        video_clips.append(clip)
                            
                            # 4. تجميع الفيديو النهائي
                            if video_clips:
                                st.write("🎬 كنركب الفيديو النهائي...")
                                final_video = concatenate_videoclips(video_clips, method="compose")
                                final_video = final_video.with_audio(full_audio_clip)
                                
                                output_path = "auto_generated_video.mp4"
                                final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
                                
                                st.success("✅ الفيديو الأوتوماتيكي جاهز!")
                                st.video(output_path)
                                
                                with open(output_path, "rb") as file:
                                    st.download_button("⬇️ تحميل الفيديو", data=file, file_name="auto_generated_video.mp4", mime="video/mp4")
                            else:
                                st.error("ما قدرناش نصنعو الفيديو. تأكد من الصور أو مفاتيح API.")
                                
                    except Exception as e:
                        st.error(f"وقع مشكل فالتوليد: {e}")

# ==========================================
# التاب 4: تجميع الفيديو (يدوي)
# ==========================================
with tab4:
    st.header("🧩 تجميع الفيديو (رفع يدوي)")
    st.write("تقدر ترفع الصور والفيديوهات هنا وتجمعهم مع الصوت اللي فـ التاب 1.")
    
    uploaded_media = st.file_uploader("تحميل صور أو فيديوهات (JPG, PNG, MP4):", type=["jpg", "jpeg", "png", "mp4"], accept_multiple_files=True)
    
    if st.button("🚀 تجميع ودمج", use_container_width=True):
        if not uploaded_media:
            st.warning("عافاك حمل شي ملفات.")
        else:
            st.success("✅ تم التجميع بنجاح! (هذا مجرد مثال توضيحي)")

# ==========================================
# التاب 5: الموسيقى
# ==========================================
with tab5:
    st.header("🎵 الموسيقى")
    
    music_option = st.radio("🎼 طريقة الحصول على الموسيقى:", [
        "توليد موسيقى بالذكاء الاصطناعي (Google Lyria)", 
        "توليد موسيقى باستعمال ACE Music API (مجاني)", 
        "رفع ملف موسيقى جاهز (إلغاء التوليد)"
    ], horizontal=False)
    
    if music_option == "توليد موسيقى بالذكاء الاصطناعي (Google Lyria)":
        st.info("ملاحظة: خدمة Lyria 3 قد تكون مقطوعة مؤقتاً (Error 429).")
        if not gemini_api_key:
            st.warning("⚠️ عافاك دخل Google Gemini API Key.")
        else:
            music_prompt = st.text_area("وصف الموسيقى:", height=100)
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
                        headers = {
                            "Authorization": f"Bearer {st.session_state.acestep_api_key}",
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "prompt": ace_music_prompt,
                            "duration": 30,
                            "task_type": "text2music"
                        }
                        
                        res = requests.post(
                            "https://api.acemusic.ai/v1/music/generate",
                            headers=headers,
                            json=payload
                        )
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
                                st.success("✅ الموسيقى جاهزة (ACE Music)!")
                                st.audio(audio_data, format="audio/mp3")
                            else:
                                st.error("لم يتم الحصول على رابط الصوت بعد انتهاء المهلة.")
                                
                    except Exception as e:
                        st.error(f"وقع مشكل مع ACE Music API: {e}")

    else:
        uploaded_music = st.file_uploader("ارفع ملف الموسيقى (MP3/WAV)", type=["mp3", "wav"])
        if uploaded_music is not None:
            st.success("✅ تم رفع الموسيقى بنجاح!")
            st.audio(uploaded_music, format="audio/wav")
