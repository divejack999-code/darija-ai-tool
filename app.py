import streamlit as st
import base64
import re
import json
import os
import time
import tempfile
import numpy as np
import io
from PIL import Image
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, VideoFileClip, CompositeVideoClip
from docx import Document

# --- إعدادات الواجهة ---
st.set_page_config(page_title="AI Studio: Darija & Amazigh", page_icon="🎬", layout="wide")
st.title("🎬 استوديو الذكاء الاصطناعي الشامل")

# --- تهيئة الذاكرة ديال الجلسة (Session State) ---
if 'saved_voices' not in st.session_state:
    st.session_state.saved_voices = []

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

# --- الشريط الجانبي (الإعدادات) ---
with st.sidebar:
    st.header("⚙️ الإعدادات العامة")
    gemini_api_key = st.text_input("1. Google Gemini API Key (ضروري):", type="password")
    magic_hour_key = st.text_input("2. Magic Hour API Key (اختياري - للفيديو AI):", type="password")
    
    st.markdown("---")
    # قائمة اللغات واللهجات الموسعة
    language = st.selectbox("اللغة/اللهجة:", [
        "الدارجة المغربية", "الأمازيغية", "العربية الفصحى", 
        "المصرية", "الخليجية", "السورية", "اللبنانية", "العراقية",
        "الإنجليزية (English)", "الفرنسية (Français)", 
        "الإسبانية (Español)", "الألمانية (Deutsch)", "التركية (Türkçe)"
    ])
    tone = st.selectbox("الستايل (Tone):", ["الكوميدية", "الدرامية", "التشويق", "إعلاني (تجاري)"])
    
    st.markdown("---")
    st.subheader("🛡️ إعدادات الحماية")
    selected_model_name = st.selectbox(
        "اختار نموذج الذكاء الاصطناعي:",
        ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash"]
    )
    max_retries = st.number_input("عدد المحاولات فحالة وقع خطأ (Retries):", min_value=1, max_value=10, value=3)

# --- تقسيم الواجهة لـ 4 تابات ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 1. السيناريو والصوت", 
    "🤖 2. توليد فيديو AI", 
    "🖼️ 3. صور + حركة كاميرا", 
    "🎬 4. تجميع الفيديو النهائي"
])

# ==========================================
# التاب 1: كتابة السيناريو وتوليد الصوت
# ==========================================
with tab1:
    st.header("توليد السيناريو المفصل والتعليق الصوتي")
    
    work_mode = st.radio(
        "كيفاش بغيتي تخدم؟",
        ["توليد سيناريو جديد بالذكاء الاصطناعي", "لدي سيناريو جاهز (توليد الصوت فقط)"],
        horizontal=True
    )
    
    st.markdown("---")
    
    if work_mode == "توليد سيناريو جديد بالذكاء الاصطناعي":
        topic = st.text_area("فكرة الفيديو:", height=150, placeholder="مثال: قصة شاب بغا يدير رجيم...")
        generate_btn = st.button("🚀 توليد السيناريو والصوت", use_container_width=True)
    else:
        topic = ""
        custom_script = st.text_area(
            "لصق السيناريو ديالك هنا (الحوار أو التعليق الصوتي فقط):", 
            height=250, 
            placeholder="مثال:\n(أمين كيهضر مع راسو) علاش أنا هكا؟ غادي نبدا الرجيم...\n(يضحك) والله غير غادي ناكل هاد الكيك كامل!"
        )
        generate_btn = st.button("🎙️ توليد الصوت من السيناريو", use_container_width=True)

    st.markdown("---")
    st.subheader("🎙️ إعدادات الصوت")
    
    voice_col1, voice_col2 = st.columns(2)
    
    # قائمة الأصوات الموسعة
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
        selected_voice_label = st.selectbox("اختار الصوت (Voice):", list(available_voices.keys()))
        selected_voice = available_voices[selected_voice_label]
    
    with voice_col2:
        style_prompt = st.text_input(
            "التحكم في الأسلوب (Style Prompt):", 
            placeholder="مثال: هضر بضحك، بنبرة سريعة وحماسية...",
        )

    if generate_btn:
        if not gemini_api_key:
            st.error("عافاك دخل Google Gemini API Key فالشريط الجانبي.")
        else:
            full_dialogue = ""
            
            if work_mode == "توليد سيناريو جديد بالذكاء الاصطناعي":
                if not topic:
                    st.warning("عافاك كتب شي فكرة.")
                else:
                    try:
                        import google.generativeai as genai
                        with st.spinner(f"جاري كتابة السيناريو باستعمال {selected_model_name}..."):
                            genai.configure(api_key=gemini_api_key)
                            model = genai.GenerativeModel(selected_model_name)
                            
                            prompt = f"""
                            أنت كاتب سيناريوهات ومخرج محترف. كتب سيناريو فيديو باللهجة/اللغة {language}.
                            الموضوع: {topic}
                            الستايل: {tone}
                            
                            خاصك ترجع الجواب على شكل JSON فقط، بلا أي كلام آخر:
                            {{
                                "title": "عنوان الفيديو",
                                "characters": [{{"name": "اسم", "description": "وصف"}}],
                                "locations": [{{"name": "مكان", "description": "وصف"}}],
                                "scenes": [
                                    {{
                                        "scene_number": 1,
                                        "location": "المكان",
                                        "visual_description": "وصف المشهد",
                                        "dialogue": "الحوار الصوتي. وإلا كان كاين شي إحساس (بحال الضحك ولا كيهضر مع راسو) حطو بين قوسين بحال هكا: (كيهضر مع راسو) وكتب الكلام من بعدو."
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
                                        st.warning(f"محاولة {attempt + 1} فشلت. كنعاودو المحاولة...")
                                        time.sleep(2)
                                    else:
                                        st.error(f"فشلت جميع المحاولات ({max_retries}). الخطأ: {e}")
                                        response = None

                            if response:
                                script_json_text = response.text.strip()
                                if script_json_text.startswith("```json"):
                                    script_json_text = script_json_text[7:]
                                if script_json_text.endswith("```"):
                                    script_json_text = script_json_text[:-3]
                                
                                script_data = json.loads(script_json_text)
                                st.success("✅ السيناريو جاهز!")
                                
                                st.subheader(f"🎬 {script_data.get('title')}")
                                
                                st.markdown("#### 👥 الشخصيات")
                                for char in script_data.get('characters', []):
                                    st.markdown(f"- **{char['name']}**: {char['description']}")
                                    
                                st.markdown("#### 📍 المواقع")
                                for loc in script_data.get('locations', []):
                                    st.markdown(f"- **{loc['name']}**: {loc['description']}")
                                    
                                st.markdown("#### 🎞️ المشاهد")
                                for scene in script_data.get('scenes', []):
                                    with st.expander(f"المشهد {scene['scene_number']} - {scene['location']}"):
                                        st.markdown(f"**الوصف البصري:** {scene['visual_description']}")
                                        st.markdown(f"**الحوار:** {scene['dialogue']}")
                                        full_dialogue += scene['dialogue'] + " "
                                
                                # --- أزرار التحميل (JSON, TXT, Word) ---
                                st.markdown("### ⬇️ تحميل السيناريو")
                                col_dl1, col_dl2, col_dl3 = st.columns(3)
                                
                                with col_dl1:
                                    st.download_button("تحميل (JSON)", 
                                                       data=json.dumps(script_data, ensure_ascii=False, indent=4),
                                                       file_name="script.json", mime="application/json",
                                                       use_container_width=True)
                                with col_dl2:
                                    st.download_button("تحميل (TXT)", 
                                                       data=script_to_text(script_data).encode('utf-8'),
                                                       file_name="script.txt", mime="text/plain",
                                                       use_container_width=True)
                                with col_dl3:
                                    st.download_button("تحميل (Word)", 
                                                       data=create_docx(script_data),
                                                       file_name="script.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                                       use_container_width=True)
                                
                    except Exception as e:
                        st.error(f"وقع شي مشكل فـ السيناريو: {e}")
            
            else:
                if not custom_script:
                    st.warning("عافاك لصق السيناريو ديالك.")
                else:
                    full_dialogue = custom_script

            if full_dialogue.strip():
                with st.spinner(f"جاري توليد الصوت باستعمال {selected_voice}..."):
                    darija_phonetics = {
                        "القهوة": "لْقَهْوَة", "المسمن": "لْمَسْمَنْ", "الفريجيدير": "لْفْرِيجِيدِير",
                        "الحلاق": "لْحَلَّاق", "الكيك": "لْكِيك", "ديال": "دْيَال", "واش": "وَاشْ"
                    }
                    for word, phonetic in darija_phonetics.items():
                        full_dialogue = full_dialogue.replace(word, phonetic)

                    try:
                        from google import genai as google_genai
                        from google.genai import types
                        
                        client = google_genai.Client(api_key=gemini_api_key)
                        
                        tts_instruction = f"""
                        أنت ممثل صوتي محترف. اقرأ النص التالي باللغة/اللهجة {language} بصوت طبيعي.
                        تحذير مهم: أي كلام بين قوسين ( ) أو [ ] هو تعليمات إخراجية للتمثيل فقط (بحال: كيهضر مع راسو، يضحك). 
                        ممنوع تنطق الكلمات التي بين القوسين. طبق الإحساس فقط وتجاوز القوسين.
                        
                        النص:
                        {full_dialogue}
                        """
                        
                        response = client.models.generate_content(
                            model="gemini-2.0-flash", 
                            contents=tts_instruction,
                            config=types.GenerateContentConfig(
                                response_modalities=["AUDIO"],
                                speech_config=types.SpeechConfig(
                                    voice_config=types.VoiceConfig(
                                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                            voice_name=selected_voice
                                        )
                                    )
                                )
                            )
                        )
                        
                        audio_data = response.candidates[0].content.parts[0].inline_data.data
                        
                        # --- خزن الصوت فـ الذاكرة ---
                        st.session_state.saved_voices.append({
                            "text": full_dialogue,
                            "voice": selected_voice,
                            "style": style_prompt,
                            "audio": audio_data
                        })
                        
                        st.success(f"✅ الصوت جاهز باستعمال {selected_voice}!")
                        st.audio(audio_data, format="audio/wav")
                        
                    except Exception as e:
                        st.error(f"وقع مشكل فـ توليد الصوت: {e}")

    # --- سجل الأصوات المحفوظة ---
    if st.session_state.saved_voices:
        st.markdown("---")
        st.subheader("💾 سجل الأصوات المحفوظة (Voice History)")
        for i, item in enumerate(reversed(st.session_state.saved_voices)):
            with st.expander(f"🎵 صوت {len(st.session_state.saved_voices) - i} - الصوت: {item['voice']}"):
                st.write(f"**النص:** {item['text']}")
                st.write(f"**الستايل:** {item['style']}")
                st.audio(item['audio'], format="audio/wav")
                
                # زر لاسترجاع الإعدادات
                if st.button("🔄 استعمل هاد الإعدادات", key=f"restore_{i}"):
                    st.session_state.restore_voice = item['voice']
                    st.session_state.restore_style = item['style']
                    st.session_state.restore_text = item['text']
                    st.rerun()

# ==========================================
# التاب 2: توليد فيديو بالذكاء الاصطناعي (Magic Hour)
# ==========================================
with tab2:
    st.header("توليد فيديو بالذكاء الاصطناعي (Text to Video)")
    st.info("💡 هاد الخيار كيستعمل Magic Hour API. كيعطيك 100 كريديت مجاني كل نهار.")
    
    ai_prompt = st.text_area("وصف المشهد بالتفصيل:", placeholder="A funny Moroccan man looking at a plate of msemen at 2 AM...")
    
    if st.button("🎥 توليد الفيديو", key="btn_ai_video"):
        if not magic_hour_key:
            st.error("عافاك دخل Magic Hour API Key فالشريط الجانبي.")
        elif not ai_prompt:
            st.warning("عافاك كتب وصف الفيديو.")
        else:
            try:
                import magic_hour
                client = magic_hour.Client(api_key=magic_hour_key)
                with st.spinner("جاري توليد الفيديو... هادشي كياخد شي دقيقة."):
                    job = client.video.generate(
                        model="wan-2.2",
                        prompt=ai_prompt,
                        duration=5,
                        resolution="480p"
                    )
                    while job.status not in ["complete", "error"]:
                        time.sleep(3)
                        job = client.video.get(job.id)
                        
                    if job.status == "complete":
                        st.success("✅ الفيديو جاهز!")
                        st.video(job.video_url)
                        st.markdown(f"[⬇️ تحميل الفيديو]({job.video_url})")
                    else:
                        st.error("وقع خطأ فالتوليد.")
            except Exception as e:
                st.error(f"خطأ فـ Magic Hour: {e}")

# ==========================================
# التاب 3: صور + حركة كاميرا (MoviePy)
# ==========================================
with tab3:
    st.header("تحويل الصور لفيديو مع حركة كاميرا (Ken Burns)")
    
    uploaded_images = st.file_uploader("تحميل الصور (بترتيب المشاهد):", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    duration_per_image = st.slider("مدة كل صورة (بالثواني):", 2, 10, 4)
    
    if st.button("🎬 صناعة الفيديو من الصور"):
        if not uploaded_images:
            st.warning("عافاك حمل شي صور.")
        else:
            try:
                with st.spinner("جاري تحريك الصور..."):
                    clips = []
                    for uploaded_file in uploaded_images:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = tmp_file.name
                        
                        img = Image.open(tmp_path)
                        target_size = (1080, 1920)
                        img = img.resize(target_size)
                        img_array = np.array(img)
                        
                        clip = ImageClip(img_array).with_duration(duration_per_image)
                        clip = clip.resized(lambda t: 1 + 0.05 * t) # Zoom effect
                        clip = clip.with_position('center')
                        
                        clips.append(clip)
                        os.remove(tmp_path)
                    
                    final_video = concatenate_videoclips(clips, method="compose")
                    output_path = "ken_burns_video.mp4"
                    final_video.write_videofile(output_path, fps=24, codec="libx264", audio=False)
                    
                    st.success("✅ الفيديو جاهز!")
                    st.video(output_path)
                    
                    with open(output_path, "rb") as file:
                        st.download_button("⬇️ تحميل الفيديو", data=file, file_name="animated_images.mp4", mime="video/mp4")
            except Exception as e:
                st.error(f"وقع مشكل فالمونتاج: {e}")

# ==========================================
# التاب 4: تجميع الفيديو النهائي
# ==========================================
with tab4:
    st.header("تجميع الفيديو النهائي للرفع")
    
    uploaded_videos = st.file_uploader("تحميل مقاطع الفيديو (بترتيب المشاهد):", type=["mp4", "mov"], accept_multiple_files=True)
    uploaded_audio = st.file_uploader("تحميل الصوت (Voiceover - WAV/MP3):", type=["mp3", "wav"])
    
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
                        
                        clip = VideoFileClip(tmp_vid_path)
                        video_clips.append(clip)
                    
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
                    
                    st.success("✅ الفيديو النهائي جاهز للرفع!")
                    st.video(output_path)
                    
                    with open(output_path, "rb") as file:
                        st.download_button("⬇️ تحميل الفيديو النهائي", data=file, file_name="final_ready_video.mp4", mime="video/mp4")
                        
            except Exception as e:
                st.error(f"وقع مشكل فالتجميع: {e}")
