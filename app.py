import streamlit as st
import math
import pandas as pd

# **يجب أن تكون set_page_config هي أول دالة streamlit تُستدعى.**
st.set_page_config(page_title="🕋 مخطط القوى العاملة للحج (بأنواع الإدارات)", layout="wide")

# -------------------------------------------------------------------
# الدوال المساعدة للحساب (Logic)
# -------------------------------------------------------------------
# (بقية الدوال كما هي)
def calculate_time_based_staff(total_events, time_per_event_min, service_days, staff_work_hours_day, reserve_factor):
    # ... (محتوى الدالة)
    time_per_event_hrs = time_per_event_min / 60
    total_hours_needed = total_events * time_per_event_hrs
    total_staff_available_hours = service_days * staff_work_hours_day
    
    if total_staff_available_hours > 0:
        basic_staff = math.ceil(total_hours_needed / total_staff_available_hours)
    else:
        basic_staff = 0
    
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Time'}

def calculate_ratio_based_staff(num_hajjaj, ratio, reserve_factor):
    # ... (محتوى الدالة)
    basic_staff = math.ceil(num_hajjaj / ratio)
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Ratio'}

def distribute_staff(total_basic_staff, ratio_supervisor, ratio_assistant_head, ratio_head):
    # ... (محتوى الدالة)
    مقدم_خدمة = total_basic_staff  
    مشرفون_اجمالي = math.ceil(مقدم_خدمة / ratio_supervisor)
    مساعد_رئيس = math.ceil(مشرفون_اجمالي / ratio_assistant_head)
    رئيس = math.ceil(مساعد_رئيس / ratio_head)
    إداري = 1 
    
    return {
        'رئيس': رئيس,
        'مساعد رئيس': مساعد_رئيس, 
        'مشرف ميداني': math.ceil(مشرفون_اجمالي * 0.7), 
        'مشرف اداري': مشرفون_اجمالي - math.ceil(مشرفون_اجمالي * 0.7), 
        'مقدم خدمة': مقدم_خدمة, 
        'اداري': إداري
    }

# -------------------------------------------------------------------
# تحديد الإدارات وتصنيفها
# -------------------------------------------------------------------
# (بقية القواميس كما هي)
DEPARTMENTS = {
    "مراكز الضيافة": [
        {'name': 'مركز الضيافة', 'type': 'Ratio', 'default_ratio': 75},
    ],
    "الاستقبال والمغادرة": [
        {'name': 'استقبال الهجرة', 'type': 'Time', 'default_time': 2.0},
        {'name': 'استقبال المطار', 'type': 'Time', 'default_time': 3.0},
        {'name': 'استقبال القطار', 'type': 'Time', 'default_time': 1.5},
        {'name': 'إرشاد الحافلات', 'type': 'Bus_Ratio', 'default_ratio': 2},
    ],
    "الدعم والمساندة": [
        {'name': 'المتابعة الميدانية', 'type': 'Ratio', 'default_ratio': 100},
        {'name': 'الدعم والضيافة', 'type': 'Ratio', 'default_ratio': 80},
        {'name': 'التوجيه', 'type': 'Ratio', 'default_ratio': 90},
        {'name': 'الزيارة وإرشاد التأهيل', 'type': 'Time', 'default_time': 2.5},
        {'name': 'الرعاية الصحية', 'type': 'Ratio', 'default_ratio': 200},
    ]
}

# -------------------------------------------------------------------
# واجهة المستخدم (Streamlit UI)
# -------------------------------------------------------------------

st.title("🕋 أداة تخطيط القوى العاملة الذكية")
st.markdown("---")

# -------------------------------------------------------------------
# القسم الأول: الإعدادات العامة ونوع الإدارة
# -------------------------------------------------------------------

st.sidebar.header("1. الإعدادات العامة")

department_type_choice = st.sidebar.selectbox(
    "اختر نوع الإدارة المراد حسابه:",
    options=list(DEPARTMENTS.keys()),
    key="dept_type"
)

num_hajjaj = st.sidebar.number_input("عدد الحجاج الإجمالي", min_value=1, value=3000, step=100) 
service_days = st.sidebar.number_input("فترة الخدمة الإجمالية (بالأيام)", min_value=1, value=6)
staff_work_hours_day = st.sidebar.number_input("ساعات عمل الموظف اليومية", min_value=1, max_value=16, value=8)
reserve_factor_input = st.sidebar.slider("نسبة الاحتياط الإجمالي (%)", min_value=0, max_value=50, value=15)
reserve_factor = reserve_factor_input / 100 


# --- المدخلات الخاصة بالهيكل الإداري (التوزيع الهرمي) ---
st.sidebar.header("2. معايير الهيكل الإداري")
st.sidebar.markdown('**نسب الإشراف (للتوزيع الهرمي)**')
ratio_supervisor = st.sidebar.number_input("مقدم خدمة / مشرف", min_value=1, value=8)
ratio_assistant_head = st.sidebar.number_input("مشرف / مساعد رئيس", min_value=1, value=4)
ratio_head = st.sidebar.number_input("مساعد
