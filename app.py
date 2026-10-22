import time
from google.api_core import retry

@retry.Retry(initial=2.0, maximum=60.0, multiplier=2.0, retry_codes=["RESOURCE_EXHAUSTED"])
def generate_with_retry(model, prompt):
    return model.generate_content(prompt)
import streamlit as st
import base64
import google.generativeai as genai
import asyncio
import edge_tts
import json
import os
import time
import tempfile
import numpy as np
from PIL import Image
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, VideoFileClip, CompositeVideoClip, vfx, afx

# --- إعدادات الواجهة ---
st.set_page_config(page_title="AI Studio: Darija & Amazigh", page_icon="🎬", layout="wide")
st.title("🎬 استوديو الذكاء الاصطناعي الشامل")

# --- الشريط الجانبي (الإعدادات) ---
with st.sidebar:
    st.header("⚙️ الإعدادات العامة")
    gemini_api_key = st.text_input("1. Google Gemini API Key (ضروري):", type="password")
    magic_hour_key = st.text_input("2. Magic Hour API Key (اختياري - للفيديو AI):", type="password")
    
    st.markdown("---")
    language = st.selectbox("اللغة/اللهجة:", ["الدارجة المغربية", "الأمازيغية", "العربية الفصحى"])
    tone = st.selectbox("الستايل (Tone):", ["الكوميدية", "الدرامية", "التشويق", "إعلاني (تجاري)"])

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
    
    col1, col2 = st.columns([2, 1])
    with col1:
        topic = st.text_area("فكرة الفيديو:", height=150, placeholder="مثال: قصة شاب بغا يدير رجيم...")
    with col2:
        st.write("")
        st.write("")
        generate_script_btn = st.button("🚀 توليد السيناريو والصوت", use_container_width=True)

    st.markdown("---")
    st.subheader("🎙️ إعدادات الصوت")
    
    voice_col1, voice_col2 = st.columns(2)
    
    # قائمة الأصوات الـ 30 الرسمية من Google
    available_voices = {
        "Zephyr (Bright - Female)": "Zephyr",
        "Puck (Upbeat - Male)": "Puck",
        "Charon (Informative - Male)": "Charon",
        "Kore (Firm - Female)": "Kore",
        "Fenrir (Excitable - Male)": "Fenrir",
        "Leda (Youthful - Female)": "Leda",
        "Orus (Firm - Male)": "Orus",
        "Aoede (Breezy - Female)": "Aoede",
        "Callirrhoe (Easy-going - Female)": "Callirrhoe",
        "Autonoe (Bright - Female)": "Autonoe",
        "Enceladus (Breathy - Male)": "Enceladus",
        "Iapetus (Clear - Male)": "Iapetus",
        "Umbriel (Easy-going - Male)": "Umbriel",
        "Algieba (Smooth - Male)": "Algieba",
        "Despina (Smooth - Female)": "Despina",
        "Erinome (Clear - Female)": "Erinome",
        "Algenib (Gravelly - Male)": "Algenib",
        "Rasalgethi (Informative - Male)": "Rasalgethi",
        "Laomedeia (Upbeat - Female)": "Laomedeia",
        "Achernar (Soft - Female)": "Achernar",
        "Alnilam (Firm - Male)": "Alnilam",
        "Schedar (Even - Male)": "Schedar",
        "Gacrux (Mature - Female)": "Gacrux",
        "Pulcherrima (Forward - Female)": "Pulcherrima",
        "Achird (Friendly - Male)": "Achird",
        "Zubenelgenubi (Casual - Male)": "Zubenelgenubi",
        "Vindemiatrix (Gentle - Female)": "Vindemiatrix",
        "Sadachbia (Lively - Male)": "Sadachbia",
        "Sadaltager (Knowledgeable - Male)": "Sadaltager",
        "Sulafat (Warm - Female)": "Sulafat"
    }
    
    with voice_col1:
        selected_voice_label = st.selectbox("اختار الصوت (Voice):", list(available_voices.keys()))
        selected_voice = available_voices[selected_voice_label]
    
    with voice_col2:
        style_prompt = st.text_input(
            "التحكم في الأسلوب (Style Prompt):", 
            placeholder="مثال: هضر بضحك، بنبرة سريعة وحماسية، بحال شي واحد كيهضر مع صحابو",
            help="كتب هنا كيفاش بغيتي الصوت يهضر. هاد النص كيتزاد مع الحوار باش يتحكم فـ النبرة."
        )

    if generate_script_btn:
        if not gemini_api_key:
            st.error("عافاك دخل Google Gemini API Key فالشريط الجانبي.")
        elif not topic:
            st.warning("عافاك كتب شي فكرة.")
        else:
            try:
                with st.spinner("جاري كتابة السيناريو..."):
                    genai.configure(api_key=gemini_api_key)
                    model = genai.GenerativeModel('gemini-3.1-flash-lite')
                    
                    prompt = f"""
                    أنت كاتب سيناريوهات ومخرج محترف. كتب سيناريو فيديو باللهجة {language}.
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
                                "dialogue": "الحوار الصوتي، وإلا كان كاين شي حركة ولا إحساس، حطو بين قوسين بحال (كيهضر مع راسو) ولا (كيبكي)، ولكن كتب الكلام العادي من بعدو."
                            }}
                        ]
                    }}
                    """
                    
                    response = generate_with_retry(model, prompt)
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
                    full_dialogue = ""
                    for scene in script_data.get('scenes', []):
                        with st.expander(f"المشهد {scene['scene_number']} - {scene['location']}"):
                            st.markdown(f"**الوصف البصري:** {scene['visual_description']}")
                            st.markdown(f"**الحوار:** {scene['dialogue']}")
                            full_dialogue += scene['dialogue'] + " "
                    
                    st.download_button("⬇️ تحميل السيناريو (JSON)", 
                                       data=json.dumps(script_data, ensure_ascii=False, indent=4),
                                       file_name="script.json", mime="application/json")
                
                with st.spinner(f"جاري توليد الصوت باستعمال {selected_voice}..."):
                    if full_dialogue.strip():
                                                # --- قاموس النطق المغربي (باش يصحح الكلمات) ---
                        darija_phonetics = {
                            "القهوة": "لْقَهْوَة",
                            "المسمن": "لْمَسْمَنْ",
                            "الفريجيدير": "لْفْرِيجِيدِير",
                            "الحلاق": "لْحَلَّاق",
                            "الكيك": "لْكِيك",
                            "ديال": "دْيَال",
                            "واش": "وَاشْ"
                        }
                        for word, phonetic in darija_phonetics.items():
                            full_dialogue = full_dialogue.replace(word, phonetic)
                        # ------------------------------------------------

                        try:
                            from google import genai as google_genai
                            
                            client = google_genai.Client(api_key=gemini_api_key)
                            
                            # هنا كنستعملو speech_metadata.style باش نتحكمو فـ الأسلوب
                            style = style_prompt if style_prompt else "Read the following text naturally and expressively."
                            
                            # هنا كنعطيو تعليمات صارمة للنموذج باش يمثل الأقواس وميقراهاش
                            tts_instruction = f"""
                            أنت ممثل صوتي محترف.
                            اقرأ النص التالي بصوت طبيعي.
                            تحذير مهم جداً: أي كلام بين قوسين ( ) أو [ ] هو تعليمات إخراجية للتمثيل فقط (بحال: كيهضر مع راسو، يضحك، كيبكي). 
                            ممنوع منعاً باتاً تنطق الكلمات التي بين القوسين. طبق الإحساس فقط وتجاوز القوسين.
                            
                            النص:
                            {full_dialogue}
                            """
                            
                            interaction = client.interactions.create(
                                model="gemini-3.8-flash-tts",
                                input=[{
                                    "type": "user_input",
                                    "content": [{
                                        "type": "text",
                                        "text": tts_instruction,
                                        "annotations": [{
                                            "type": "speech_metadata",
                                            "style": style
                                        }]
                                    }]
                                }],
                                response_format={"type": "audio"},
                                generation_config={
                                    "speech_config": [{"voice": selected_voice}]
                                }
                            )
                            
                            audio_data = base64.b64decode(interaction.output_audio.data)
                            with open("voiceover.wav", "wb") as f:
                                f.write(audio_data)
                            
                            st.success(f"✅ الصوت جاهز باستعمال {selected_voice}!")
                            st.audio("voiceover.wav", format="audio/wav")
                            
                        except Exception as e:
                            st.error(f"وقع مشكل فـ توليد الصوت: {e}")
            except Exception as e:
                st.error(f"وقع شي مشكل: {e}")
                
# ==========================================
# التاب 2: توليد فيديو بالذكاء الاصطناعي (Magic Hour)
# ==========================================
with tab2:
    st.header("توليد فيديو بالذكاء الاصطناعي (Text to Video)")
    st.info("💡 هاد الخيار كيستعمل Magic Hour API. كيعطيك 100 كريديت مجاني كل نهار. الفيديو كيكون قصير (5 ثواني).")
    
    ai_prompt = st.text_area("وصف المشهد بالتفصيل (بالعربية أو الإنجليزية):", placeholder="A funny Moroccan man looking at a plate of msemen at 2 AM...")
    
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
                        model="wan-2.2", # نموذج رخيص
                        prompt=ai_prompt,
                        duration=5,
                        resolution="480p"
                    )
                    # الانتظار حتى يكتمل
                    while job.status not in ["complete", "error"]:
                        time.sleep(3)
                        job = client.video.get(job.id)
                        
                    if job.status == "complete":
                        st.success("✅ الفيديو جاهز!")
                        st.video(job.video_url)
                        st.markdown(f"[⬇️ تحميل الفيديو]({job.video_url})")
                    else:
                        st.error("وقع خطأ فالتوليد. جرب وصف آخر.")
            except Exception as e:
                st.error(f"خطأ فـ Magic Hour: {e}")

# ==========================================
# التاب 3: صور + حركة كاميرا (MoviePy)
# ==========================================
with tab3:
    st.header("تحويل الصور لفيديو مع حركة كاميرا (Ken Burns)")
    st.write("توليد الصور كديرو فـ Google Flow أو أي أداة، ومن بعد تحملوهم هنا وهاد الخيار غادي يعطيهم حركة زوينة.")
    
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
                        # نحفظو الصورة مؤقتاً
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = tmp_file.name
                        
                        # صايبو كليب ونطبقو عليه الزوم (Ken Burns)
                        img = Image.open(tmp_path)
                        # نصلحو الأبعاد باش تكون متساوية
                        target_size = (1080, 1920) # مقاس الريلز
                        img = img.resize(target_size)
                        img_array = np.array(img)
                        
                        clip = ImageClip(img_array).set_duration(duration_per_image)
                        # تأثير الزوم البطيء
                        clip = clip.resized(lambda t: 1 + 0.05 * t)
                        # باش نبقاو فوسط الشاشة
                        clip = clip.with_position('center')
                        
                        clips.append(clip)
                        os.remove(tmp_path) # نمسحو الملف المؤقت
                    
                    # تجميع المقاطع
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
    st.write("حمل هنا الفيديوهات اللي ولدتي (من التاب 2 أو 3) والصوت اللي ولدتي (من التاب 1) باش تجمعهم ففيديو واحد.")
    
    uploaded_videos = st.file_uploader("تحميل مقاطع الفيديو (بترتيب المشاهد):", type=["mp4", "mov"], accept_multiple_files=True)
    uploaded_audio = st.file_uploader("تحميل الصوت (Voiceover - MP3):", type=["mp3", "wav"])
    
    if st.button("🚀 تجميع ودمج الفيديو"):
        if not uploaded_videos:
            st.warning("عافاك حمل شي فيديوهات.")
        else:
            try:
                with st.spinner("جاري تجميع الفيديو..."):
                    video_clips = []
                    
                    # 1. تحميل المقاطع
                    for uploaded_file in uploaded_videos:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_vid:
                            tmp_vid.write(uploaded_file.getvalue())
                            tmp_vid_path = tmp_vid.name
                        
                        clip = VideoFileClip(tmp_vid_path)
                        video_clips.append(clip)
                    
                    # 2. تجميع الفيديوهات
                    final_clip = concatenate_videoclips(video_clips, method="compose")
                    
                    # 3. إضافة الصوت إلا كان كاين
                    if uploaded_audio:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
                            tmp_audio.write(uploaded_audio.getvalue())
                            tmp_audio_path = tmp_audio.name
                        
                        audio_clip = AudioFileClip(tmp_audio_path)
                        # تأكد أن الصوت ماشي أطول من الفيديو بزاف
                        if audio_clip.duration > final_clip.duration:
                            final_clip = final_clip.with_duration(audio_clip.duration)
                        
                        final_clip = final_clip.with_audio(audio_clip)
                    
                    # 4. تصدير الفيديو
                    output_path = "final_ready_video.mp4"
                    final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
                    
                    st.success("✅ الفيديو النهائي جاهز للرفع على فيسبوك ريلز!")
                    st.video(output_path)
                    
                    with open(output_path, "rb") as file:
                        st.download_button("⬇️ تحميل الفيديو النهائي", data=file, file_name="final_ready_video.mp4", mime="video/mp4")
                        
            except Exception as e:
                st.error(f"وقع مشكل فالتجميع: {e}")
