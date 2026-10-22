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
from PIL import Image
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, VideoFileClip, CompositeVideoClip, concatenate_audioclips
from docx import Document

# --- إعدادات الواجهة ---
st.set_page_config(page_title="AI Studio: Darija & Amazigh", page_icon="🎬", layout="wide")
st.title("🎬 استوديو الذكاء الاصطناعي الشامل")

# --- المفتاح المحفوظ ديال Pixabay ---
DEFAULT_PIXABAY_KEY = "58178676-7dca3797f2ac366b67263077a"

# --- تهيئة الذاكرة ديال الجلسة (Session State) ---
if 'saved_voices' not in st.session_state:
    st.session_state.saved_voices = []
if 'script_data' not in st.session_state:
    st.session_state.script_data = None
if 'full_audio_bytes' not in st.session_state:
    st.session_state.full_audio_bytes = None

# --- دوال مساعدة للتحميل ---
def script_to_text(script_data):
    text = f"العنوان: {script_data.get('title', '')}\n\n"
    text += "الشخصيات:\n"
    for c in script_data.get('characters', []):
        text += f"- {c.get('name')}: {c.get('description')}\n"
    text += "\nالمواقع:\n"
    for l in script_data.get('locations', []):
        text += f"- {l.get('name')}: {l.get('description')}\n"
    text += "\nالمشاهد:\n"
    for s in script_data.get('scenes', []):
        text += f"مشهد {s.get('scene_number')} - {s.get('location')}:\n"
        text += f"  الوصف البصري: {s.get('visual_description')}\n"
        text += f"  الحوار: {s.get('dialogue')}\n\n"
    return text

def create_docx(script_data):
    doc = Document()
    doc.add_heading(script_data.get('title', 'السيناريو'), 0)
    
    doc.add_heading('الشخصيات', level=1)
    for c in script_data.get('characters', []):
        doc.add_paragraph(f"{c.get('name')}: {c.get('description')}", style='List Bullet')
        
    doc.add_heading('المواقع', level=1)
    for l in script_data.get('locations', []):
        doc.add_paragraph(f"{l.get('name')}: {l.get('description')}", style='List Bullet')
        
    doc.add_heading('المشاهد', level=1)
    for s in script_data.get('scenes', []):
        doc.add_heading(f"مشهد {s.get('scene_number')} - {s.get('location')}", level=2)
        doc.add_paragraph(f"الوصف البصري: {s.get('visual_description')}")
        doc.add_paragraph(f"الحوار: {s.get('dialogue')}")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- دوال جلب الفيديوهات ---
def fetch_pixabay_videos(query, api_key, per_page=1):
    url = "https://pixabay.com/api/videos/"
    params = {"key": api_key, "q": query, "per_page": per_page, "video_type": "film", "safesearch": "true"}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        hits = response.json().get('hits', [])
        if hits:
            return hits[0]['videos']['large']['url']
    except Exception:
        return None

def fetch_coverr_videos(query, per_page=1):
    url = "https://api.coverr.co/videos"
    params = {"query": query, "page_size": per_page}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        hits = data.get('hits', [])
        if hits:
            video_urls = hits[0].get('urls', {})
            best_url = video_urls.get('mp4_download') or video_urls.get('mp4_1080') or video_urls.get('mp4_720')
            return best_url
    except Exception as e:
        print(f"خطأ في Coverr: {e}")
        return None

# --- الشريط الجانبي ---
with st.sidebar:
    st.header("⚙️ الإعدادات العامة")
    gemini_api_key = st.text_input("1. Google Gemini API Key (ضروري):", type="password")
    
    pixabay_api_key = st.text_input(
        "2. Pixabay API Key (اختياري - كبديل):", 
        value=DEFAULT_PIXABAY_KEY,
        type="password"
    )
    
    magic_hour_key = st.text_input("3. Magic Hour API Key (اختياري):", type="password")
    
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
    selected_model_name = st.selectbox(
        "اختار نموذج الذكاء الاصطناعي:",
        ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-2.5-flash"]
    )
    max_retries = st.number_input("عدد المحاولات فحالة وقع خطأ:", min_value=1, max_value=10, value=3)

# --- تقسيم الواجهة لـ 4 تابات ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 1. السيناريو والصوت", 
    "🤖 2. توليد فيديو AI", 
    "🎬 3. التوليد الأوتوماتيكي (مكتبة فيديو)", 
    "🧩 4. تجميع الفيديو النهائي"
])

# ==========================================
# التاب 1: كتابة السيناريو وتوليد الصوت
# ==========================================
with tab1:
    st.header("توليد السيناريو المفصل والتعليق الصوتي")
    
    work_mode = st.radio("كيفاش بغيتي تخدم؟", ["توليد سيناريو جديد", "لدي سيناريو جاهز (توليد الصوت فقط)"], horizontal=True)
    st.markdown("---")
    
    if work_mode == "توليد سيناريو جديد":
        topic = st.text_area("فكرة الفيديو:", height=150, placeholder="مثال: قصة شاب بغا يدير رجيم...")
        generate_btn = st.button("🚀 توليد السيناريو والصوت", use_container_width=True)
    else:
        topic = ""
        custom_script = st.text_area("لصق السيناريو ديالك هنا:", height=250, placeholder="مثال:\n(كيهضر مع راسو) علاش أنا هكا؟...")
        generate_btn = st.button("🎙️ توليد الصوت من السيناريو", use_container_width=True)

    st.markdown("---")
    st.subheader("🎙️ إعدادات الصوت")
    
    voice_col1, voice_col2 = st.columns(2)
    available_voices = {
        "Fenrir (Excitable - Male)": "Fenrir", "Puck (Upbeat - Male)": "Puck",
        "Zephyr (Bright - Female)": "Zephyr", "Kore (Firm - Female)": "Kore",
        "Charon (Informative - Male)": "Charon", "Leda (Youthful - Female)": "Leda",
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
                if not topic:
                    st.warning("عافاك كتب شي فكرة.")
                else:
                    try:
                        import google.generativeai as genai
                        with st.spinner(f"جاري كتابة السيناريو..."):
                            genai.configure(api_key=gemini_api_key)
                            model = genai.GenerativeModel(selected_model_name)
                            
                            prompt = f"""
                            أنت كاتب سيناريوهات ومخرج محترف. كتب سيناريو فيديو باللهجة {language}.
                            الموضوع: {topic}
                            الستايل: {tone}
                            
                            خاصك ترجع الجواب على شكل JSON فقط:
                            {{
                                "title": "عنوان الفيديو",
                                "characters": [{{"name": "اسم", "description": "وصف"}}],
                                "locations": [{{"name": "مكان", "description": "وصف"}}],
                                "scenes": [
                                    {{
                                        "scene_number": 1,
                                        "location": "المكان",
                                        "visual_description": "وصف المشهد",
                                        "search_keyword": "English keywords for stock video search (e.g., man eating cake, night kitchen)",
                                        "dialogue": "الحوار الصوتي. وإلا كان كاين شي إحساس حطو بين قوسين (كيهضر مع راسو)."
                                    }}
                                ]
                            }}
                            """
                            
                            response = None
                            for attempt in range(max_retries):
                                try:
                                    response = model.generate_content(prompt)
                                    break
                                except Exception as e:
                                    if attempt < max_retries - 1:
                                        time.sleep(2)
                                    else:
                                        st.error(f"فشلت المحاولات. الخطأ: {e}")

                            if response:
                                script_json_text = response.text.strip()
                                if script_json_text.startswith("```json"): script_json_text = script_json_text[7:]
                                if script_json_text.endswith("```"): script_json_text = script_json_text[:-3]
                                
                                st.session_state.script_data = json.loads(script_json_text)
                                st.success("✅ السيناريو جاهز!")
                                
                                st.subheader(f"🎬 {st.session_state.script_data.get('title')}")
                                for scene in st.session_state.script_data.get('scenes', []):
                                    with st.expander(f"المشهد {scene['scene_number']} - {scene['location']}"):
                                        st.markdown(f"**الوصف البصري:** {scene['visual_description']}")
                                        st.markdown(f"**كلمة البحث (للفيديو):** {scene.get('search_keyword', 'N/A')}")
                                        st.markdown(f"**الحوار:** {scene['dialogue']}")
                                        full_dialogue += scene['dialogue'] + " "
                                
                                col_dl1, col_dl2, col_dl3 = st.columns(3)
                                with col_dl1:
                                    st.download_button("تحميل (JSON)", data=json.dumps(st.session_state.script_data, ensure_ascii=False, indent=4), file_name="script.json", mime="application/json", use_container_width=True)
                                with col_dl2:
                                    st.download_button("تحميل (TXT)", data=script_to_text(st.session_state.script_data).encode('utf-8'), file_name="script.txt", mime="text/plain", use_container_width=True)
                                with col_dl3:
                                    st.download_button("تحميل (Word)", data=create_docx(st.session_state.script_data), file_name="script.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
                                
                    except Exception as e:
                        st.error(f"وقع شي مشكل: {e}")
            
            else:
                if not custom_script:
                    st.warning("عافاك لصق السيناريو.")
                else:
                    full_dialogue = custom_script

            if full_dialogue.strip():
                with st.spinner(f"جاري توليد الصوت..."):
                    darija_phonetics = {"القهوة": "لْقَهْوَة", "المسمن": "لْمَسْمَنْ", "الفريجيدير": "لْفْرِيجِيدِير", "الحلاق": "لْحَلَّاق", "الكيك": "لْكِيك", "ديال": "دْيَال", "واش": "وَاشْ"}
                    for word, phonetic in darija_phonetics.items():
                        full_dialogue = full_dialogue.replace(word, phonetic)

                    try:
                        from google import genai as google_genai
                        from google.genai import types
                        client = google_genai.Client(api_key=gemini_api_key)
                        
                        tts_instruction = f"""
                        أنت ممثل صوتي. اقرأ النص باللهجة {language}.
                        ممنوع تنطق الكلمات التي بين القوسين ( )، طبق الإحساس فقط.
                        النص: {full_dialogue}
                        """
                        
                        response = client.models.generate_content(
                            model="gemini-3.5-flash",  # <-- هنا التعديل
                            contents=tts_instruction,
                            config=types.GenerateContentConfig(
                                response_modalities=["AUDIO"],
                                speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=selected_voice)))
                            )
                        )
                        
                        audio_data = response.candidates[0].content.parts[0].inline_data.data
                        st.session_state.full_audio_bytes = audio_data
                        
                        st.session_state.saved_voices.append({"text": full_dialogue, "voice": selected_voice, "style": style_prompt, "audio": audio_data})
                        
                        st.success(f"✅ الصوت جاهز!")
                        st.audio(audio_data, format="audio/wav")
                        
                    except Exception as e:
                        st.error(f"وقع مشكل فـ توليد الصوت: {e}")

    if st.session_state.saved_voices:
        st.markdown("---")
        st.subheader("💾 سجل الأصوات")
        for i, item in enumerate(reversed(st.session_state.saved_voices)):
            with st.expander(f"🎵 صوت {len(st.session_state.saved_voices) - i}"):
                st.write(f"**النص:** {item['text']}")
                st.audio(item['audio'], format="audio/wav")

# ==========================================
# التاب 2: توليد فيديو بالذكاء الاصطناعي
# ==========================================
with tab2:
    st.header("توليد فيديو بالذكاء الاصطناعي (Text to Video)")
    ai_prompt = st.text_area("وصف المشهد بالتفصيل:", placeholder="A funny Moroccan man looking at a plate of msemen...")
    if st.button("🎥 توليد الفيديو", key="btn_ai_video"):
        if not magic_hour_key:
            st.error("عافاك دخل Magic Hour API Key.")
        else:
            try:
                import magic_hour
                client = magic_hour.Client(api_key=magic_hour_key)
                with st.spinner("جاري التوليد..."):
                    job = client.video.generate(model="wan-2.2", prompt=ai_prompt, duration=5, resolution="480p")
                    while job.status not in ["complete", "error"]:
                        time.sleep(3)
                        job = client.video.get(job.id)
                    if job.status == "complete":
                        st.success("✅ الفيديو جاهز!")
                        st.video(job.video_url)
            except Exception as e:
                st.error(f"خطأ: {e}")

# ==========================================
# التاب 3: التوليد الأوتوماتيكي (القلب والتجميع)
# ==========================================
with tab3:
    st.header("🎬 التوليد الأوتوماتيكي من السيناريو")
    st.write("هاد الخيار كياخد السيناريو اللي ولدتي فـ التاب 1، كيقلب على فيديوهات مناسبة ليه فـ Coverr و Pixabay، وكيقطعهم على حساب مدة الصوت، وكيخرج ليك فيديو جاهز.")
    
    if st.session_state.script_data is None:
        st.warning("⚠️ عافاك سير للتاب 1 وتولد السيناريو والصوت الأول.")
    elif st.session_state.full_audio_bytes is None:
        st.warning("⚠️ عافاك ولد الصوت فـ التاب 1 الأول باش نعرفو المدة ديال الفيديو.")
    else:
        st.subheader("⚙️ إعدادات الفيديو النهائي")
        col1, col2 = st.columns(2)
        with col1:
            aspect_ratio = st.selectbox("أبعاد الفيديو:", ["9:16 (ريلز/تيك توك)", "16:9 (يوتيوب)", "1:1 (مربع)"])
        with col2:
            quality = st.selectbox("الجودة:", ["720p", "1080p", "480p"])

        if st.button("🚀 بدء التوليد الأوتوماتيكي للفيديو", use_container_width=True):
            with st.spinner("جاري البحث وتحميل وتجميع الفيديوهات... هادشي ممكن ياخد شي دقيقة."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                        tmp_audio.write(st.session_state.full_audio_bytes)
                        audio_path = tmp_audio.name
                    
                    full_audio_clip = AudioFileClip(audio_path)
                    total_duration = full_audio_clip.duration
                    
                    scenes = st.session_state.script_data.get('scenes', [])
                    if not scenes:
                        st.error("ما كاينش مشاهد فـ السيناريو.")
                    else:
                        duration_per_scene = total_duration / len(scenes)
                        
                        aspect_map = {"9:16 (ريلز/تيك توك)": (1080, 1920), "16:9 (يوتيوب)": (1920, 1080), "1:1 (مربع)": (1080, 1080)}
                        quality_map = {"480p": 480, "720p": 720, "1080p": 1080}
                        
                        target_h = quality_map[quality]
                        target_w = int(target_h * aspect_map[aspect_ratio][0] / aspect_map[aspect_ratio][1])
                        
                        video_clips = []
                        
                        for i, scene in enumerate(scenes):
                            keyword = scene.get('search_keyword', 'abstract background')
                            st.write(f"🔍 كنقلب على مشهد {i+1}: '{keyword}'...")
                            
                            video_url = None
                            video_url = fetch_coverr_videos(keyword)
                            if not video_url and pixabay_api_key:
                                video_url = fetch_pixabay_videos(keyword, pixabay_api_key)
                            
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
                                    from moviepy import concatenate_videoclips as concat
                                    clip = concat([clip] * loop_count).subclipped(0, duration_per_scene)
                                
                                clip = clip.resized(height=target_h)
                                if clip.w < target_w:
                                    clip = clip.resized(width=target_w)
                                clip = clip.cropped(x_center=clip.w/2, y_center=clip.h/2, width=target_w, height=target_h)
                                
                                video_clips.append(clip)
                                os.remove(vid_path)
                            else:
                                st.warning(f"⚠️ ما لقيتش فيديو لـ '{keyword}'. غادي نستعملو خلفية سوداء.")
                                from moviepy import ColorClip
                                clip = ColorClip(size=(target_w, target_h), color=(0,0,0), duration=duration_per_scene)
                                video_clips.append(clip)
                        
                        st.write("🎬 كنركب الفيديو النهائي...")
                        final_video = concatenate_videoclips(video_clips, method="compose")
                        final_video = final_video.with_audio(full_audio_clip)
                        
                        output_path = "auto_generated_video.mp4"
                        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
                        
                        st.success("✅ الفيديو الأوتوماتيكي جاهز!")
                        st.video(output_path)
                        
                        with open(output_path, "rb") as file:
                            st.download_button("⬇️ تحميل الفيديو", data=file, file_name="auto_generated_video.mp4", mime="video/mp4")
                            
                except Exception as e:
                    st.error(f"وقع مشكل فالتوليد: {e}")

# ==========================================
# التاب 4: تجميع الفيديو النهائي (يدوي)
# ==========================================
with tab4:
    st.header("تجميع الفيديو النهائي (رفع يدوي)")
    
    uploaded_videos = st.file_uploader("تحميل مقاطع الفيديو:", type=["mp4", "mov"], accept_multiple_files=True)
    uploaded_audio = st.file_uploader("تحميل الصوت:", type=["mp3", "wav"])
    
    if st.button("🚀 تجميع ودمج الفيديو"):
        if not uploaded_videos:
            st.warning("عافاك حمل شي فيديوهات.")
        else:
            try:
                with st.spinner("جاري تجميع الفيديو..."):
                    video_clips = []
                    for uploaded_file in uploaded_videos:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_vid:
                            tmp_vid.write(uploaded_file.getvalue())
                            tmp_vid_path = tmp_vid.name
                        video_clips.append(VideoFileClip(tmp_vid_path))
                    
                    final_clip = concatenate_videoclips(video_clips, method="compose")
                    
                    if uploaded_audio:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                            tmp_audio.write(uploaded_audio.getvalue())
                            tmp_audio_path = tmp_audio.name
                        audio_clip = AudioFileClip(tmp_audio_path)
                        if audio_clip.duration > final_clip.duration:
                            final_clip = final_clip.with_duration(audio_clip.duration)
                        final_clip = final_clip.with_audio(audio_clip)
                    
                    output_path = "final_ready_video.mp4"
                    final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
                    
                    st.success("✅ الفيديو النهائي جاهز!")
                    st.video(output_path)
                    
                    with open(output_path, "rb") as file:
                        st.download_button("⬇️ تحميل الفيديو", data=file, file_name="final_ready_video.mp4", mime="video/mp4")
            except Exception as e:
                st.error(f"وقع مشكل: {e}")
