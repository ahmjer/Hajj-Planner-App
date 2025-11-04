import streamlit as st
import math
import pandas as pd

# -------------------------------------------------------------------
# الدالة الرئيسية للحساب (Logic)
# -------------------------------------------------------------------

def calculate_staff_needs_v2(
    num_hajjaj: int,
    service_days: int,
    staff_work_hours_day: int,
    reserve_factor: float,
    logistics_time_per_hajjaj_min: float,
    on_site_ratio: int
):
    """تحسب الاحتياج للقوى العاملة بناءً على التدفق الزمني والتغطية المباشرة."""

    # 1. حساب الإدارة الأولى: اللوجستيات (وصول ومغادرة)
    # نعتبر أن كل حاج لديه حدثان: وصول ومغادرة
    total_logistics_events = num_hajjaj * 2 
    logistics_time_per_hajjaj_hrs = logistics_time_per_hajjaj_min / 60
    total_logistics_hours_needed = total_logistics_events * logistics_time_per_hajjaj_hrs
    total_staff_available_hours = service_days * staff_work_hours_day
    
    if total_staff_available_hours > 0:
        # عدد الموظفين الأساسيين لإنهاء المهام الزمنية
        basic_logistics_staff = math.ceil(total_logistics_hours_needed / total_staff_available_hours)
    else:
        basic_logistics_staff = 0
    
    # إجمالي موظفي اللوجستيات بعد إضافة الاحتياط
    total_logistics_staff = math.ceil(basic_logistics_staff * (1 + reserve_factor))

    # 2. حساب الإدارة الثانية: الإشراف الميداني (تغطية المتواجدين فعلياً)
    # عدد موظفي الإشراف الأساسيين (حسب نسبة التغطية)
    basic_on_site_staff = math.ceil(num_hajjaj / on_site_ratio)
    
    # إجمالي موظفي الإشراف بعد إضافة الاحتياط
    total_on_site_staff = math.ceil(basic_on_site_staff * (1 + reserve_factor))
    
    return {
        "Logistics_Basic": basic_logistics_staff,
        "Logistics_Total": total_logistics_staff,
        "OnSite_Basic": basic_on_site_staff,
        "OnSite_Total": total_on_site_staff
    }

# -------------------------------------------------------------------
# واجهة المستخدم (Streamlit UI)
# -------------------------------------------------------------------

st.set_page_config(page_title="🕋 مخطط القوى العاملة للحج", layout="wide")

st.title("🕋 أداة تخطيط القوى العاملة الذكية")
st.markdown("---")

st.sidebar.header("1. الإعدادات العامة للبعثة")

# المدخلات العامة في الشريط الجانبي (Sidebar)
num_hajjaj = st.sidebar.number_input("عدد الحجاج الإجمالي", min_value=1, value=3000, step=100)
service_days = st.sidebar.number_input("فترة الخدمة الإجمالية (بالأيام)", min_value=1, value=6)
staff_work_hours_day = st.sidebar.number_input("ساعات عمل الموظف اليومية", min_value=1, max_value=16, value=8)
reserve_factor_input = st.sidebar.slider("نسبة الاحتياط / الدعم (%)", min_value=0, max_value=50, value=15)
reserve_factor = reserve_factor_input / 100 # تحويل لكسر عشري

st.sidebar.header("2. معايير الإدارة الأولى (اللوجستيات - التدفق)")
logistics_time_per_hajjaj_min = st.sidebar.number_input("وقت خدمة الحدث الواحد (بالدقيقة)", min_value=0.5, value=3.0, step=0.5, help="الوقت اللازم لإنهاء وصول أو مغادرة حاج واحد.")

st.sidebar.header("3. معايير الإدارة الثانية (الإشراف الميداني - التغطية)")
on_site_ratio = st.sidebar.number_input("معيار تغطية الإشراف (حاج / موظف)", min_value=1, value=40, help="عدد الحجاج الذي يغطيهم موظف إشراف واحد بفعالية.")

st.subheader("نتائج الاحتياج للقوى العاملة")

# تنفيذ الحساب
results = calculate_staff_needs_v2(
    num_hajjaj, service_days, staff_work_hours_day, reserve_factor,
    logistics_time_per_hajjaj_min, on_site_ratio
)

# عرض النتائج في جدول
data = {
    'نوع الإدارة': ['1. اللوجستيات (وصول/مغادرة)', '2. الإشراف الميداني (تغطية المتواجدين)'],
    'الاحتياج الأساسي': [results['Logistics_Basic'], results['OnSite_Basic']],
    'إجمالي الاحتياج (شاملاً الاحتياط)': [results['Logistics_Total'], results['OnSite_Total']],
    'نسبة الاحتياط المطبقة': [f"{reserve_factor*100:.0f}%", f"{reserve_factor*100:.0f}%"]
}

df = pd.DataFrame(data)

st.dataframe(df.style.highlight_max(axis=0), use_container_width=True)

st.markdown("---")
st.metric(
    label="**الإجمالي الكلي للقوى العاملة المطلوبة للخدمات المباشرة**",
    value=f"{results['Logistics_Total'] + results['OnSite_Total']} موظف",
    delta=f"الاحتياج الأساسي (قبل الاحتياط): {results['Logistics_Basic'] + results['OnSite_Basic']} موظف"
)
