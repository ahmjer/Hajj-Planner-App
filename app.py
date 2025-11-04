# ... (بعد st.set_page_config) ...

# 📌📌📌 كتلة CSS الموحدة والقوية (بما في ذلك الشريط العودي الثابت) 📌📌📌
st.markdown("""
<style>
/* 1. إجبار كامل الصفحة على RTL */
html, body, [class*="st-emotion-"] {
    direction: rtl;
    text-align: right;
}

/* 2. إزاحة المحتوى الرئيسي لترك مساحة للشريط العودي الثابت (20px) */
/* نستخدم عنصر stApp الرئيسي الذي يغلف المحتوى */
[data-testid="stAppViewBlockContainer"] {
    padding-top: 30px !important; /* إزاحة المحتوى لأسفل > ارتفاع الخط 20px */
}

/* 3. إنشاء شريط علوي ثابت: الخط العودي (2 سم / 20px) */
.custom-header-line {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 20px; /* تقريباً 2 سم */
    background-color: #800020; /* لون عودي/مارون */
    z-index: 9999; /* لضمان ظهوره فوق كل شيء */
}

/* 4. تثبيت الشريط الجانبي وتحسين RTL على الجوال */
section[data-testid="stSidebar"] {
    text-align: right;
    transform: none !important; 
    left: auto;                  
    right: 0;                    
}

/* 5. تعديل محتوى الشريط الجانبي وإخفاء الكلمات العشوائية أثناء التحميل */
[data-testid="stSidebarContent"] {
    direction: rtl;
    text-align: right;
    visibility: hidden; 
}
[data-testid="stSidebarUserContent"] {
    visibility: visible !important; 
}
</style>
""", unsafe_allow_html=True)

# 📌 حقن عنصر الخط العودي في الصفحة
st.markdown('<div class="custom-header-line"></div>', unsafe_allow_html=True)

# ... (باقي الكود) ...
