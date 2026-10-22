import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os

# --- إعدادات الواجهة ---
st.set_page_config(page_title="AI Darija & Amazigh Studio", page_icon="🎬", layout="wide")
st.title("🎬 استوديو الذكاء الاصطناعي: الدارجة والأمازيغية")
st.write("مرحبا بيك! هاد الأداة كتكتب ليك السيناريو وكتولد ليك الصوت (Voiceover) جاهز للفيديو ديالك.")

# --- الشريط الجانبي (Sidebar) ---
with st.sidebar:
    st.header("⚙️ الإعدادات")
    api_key = st.text_input("دخل Google Gemini API Key ديالك:", type="password")
    st.markdown("[كيفاش تاخد API Key؟](https://aistudio.google.com/app/apikey)")
    
    format_type = st.selectbox("نوع الفيديو:", ["ريلز (قصير - 30 ثانية)", "فيديو طويل (دقيقة أو أكثر)"])
    language = st.selectbox(
        "اللغة/اللهجة:",
        [
            "الدارجة المغربية",
            "الأمازيغية",
            "العربية الفصحى",
            "المصرية",
            "الخليجية",
            "السورية",
            "الأردنية",
            "العراقية",
            "اللبنانية",
            "الإماراتية",
            "السعودية",
            "التونسية",
            "الجزائرية",
            "التركية"
        ]
    )

    tone = st.selectbox(
        "الستايل (Tone):",
        [
            "الكوميدية",
            "الأكشن والرسوم المتحركة",
            "الأفلام الموسيقية والرقص",
            "ما بعد الكارثة / النجاة المستقبلية",
            "الفانتازيا والأسطوريات",
            "الجريمة والسرقة",
            "التشويق",
            "الرعب",
            "الإثارة",
            "الدراما",
            "إعلاني (تجاري)"
        ]
    )
# --- الواجهة الرئيسية ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("1. فكرة الفيديو أو الموضوع")
    topic = st.text_area("كتب هنا شنو بغيتي تهضر عليه فالفيديو...", height=150, placeholder="مثال: نصائح للنجاح فالتجارة الإلكترونية...")

with col2:
    st.subheader("2. توليد المحتوى")
    generate_btn = st.button("🚀 توليد السيناريو والصوت", use_container_width=True)
    
    # مكان للصورة أو الفيديو (بحال اللي فالتصويرة ديالك)
    st.info("📸 هنا غادي يبان الفيديو المولد (محتاج API ديال Veo أو Kling)")

# --- لوجيك الأداة ---
if generate_btn:
    if not api_key:
        st.error("عافاك دخل الـ API Key ديال Google فالشريط الجانبي باش تخدم الأداة.")
    elif not topic:
        st.warning("عافاك كتب شي فكرة فالفيديو.")
    else:
        try:
            # 1. توليد السيناريو بـ Gemini
            with st.spinner("جاري كتابة السيناريو بالذكاء الاصطناعي..."):
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-pro')
                
                prompt = f"""
                أنت كاتب سيناريوهات محترف لمواقع التواصل الاجتماعي (فيسبوك ريلز وتيك توك).
                كتب ليا سيناريو فيديو باللهجة {language}.
                الموضوع: {topic}
                نوع الفيديو: {format_type}
                الستايل: {tone}
                
                الشروط:
                - إلا كان ريلز، خليه قصير ومباشر (بين 50 و 80 كلمة).
                - قسم السيناريو لـ (مشهد بصري) و (تعليق صوتي).
                - فـالتعليق الصوتي، استعمل كلمات طبيعية ومفهومة.
                """
                
                response = model.generate_content(prompt)
                script = response.text
                
                st.success("✅ السيناريو جاهز!")
                st.text_area("📝 السيناريو ديالك:", script, height=300)

            # 2. توليد الصوت (TTS)
            with st.spinner("جاري توليد الصوت..."):
                # نقاءو النص من علامات السيناريو باش يقرا غير الكلام
                if "تعليق صوتي:" in script:
                    voice_text = script.split("تعليق صوتي:")[-1].strip()
                else:
                    voice_text = script
                
                # اختيار الصوت حسب اللغة
                if language == "الدارجة المغربية":
                    voice = "ar-MA-JamalNeural" # صوت راجل مغربي (كاين حتى ar-MA-MounaNeural لمرا)
                else:
                    # ملاحظة: الأمازيغية مازال ما كاينة فـ Edge TTS، هنا كنستعملو صوت عربي مؤقت
                    # باش تخدم الأمازيغية 100%، خاصك تربط مع HuggingFace TTS API
                    voice = "ar-SA-HamedNeural" 
                    st.warning("⚠️ تنبيه: الصوت ديال الأمازيغية مازال ما مدعومش 100% فهاد الأداة، ولكن السيناريو مكتوب مزيان.")

                async def generate_audio():
                    communicate = edge_tts.Communicate(voice_text, voice)
                    await communicate.save("voiceover.mp3")

                asyncio.run(generate_audio())
                
                st.success("✅ الصوت جاهز!")
                st.audio("voiceover.mp3", format="audio/mp3")
                
                st.info("💡 دابا تقدر تحمل هاد الصوت، وتمشي لأي أداة بحال CapCut، وتحطو فوق الفيديو اللي صورتي بيدك أو ولدتي بالـ AI.")

        except Exception as e:
            st.error(f"وقع شي مشكل: {e}")
