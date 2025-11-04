import streamlit as st 
import math
import pandas as pd

# -------------------------------------------------------------------
# التهيئة والدوال 
# -------------------------------------------------------------------

st.set_page_config(page_title="🕋 مخطط القوى العاملة للحج", layout="wide") 

st.title("🕋 أداة تخطيط القوى العاملة الذكية")
st.markdown("---")

# الدوال المساعدة للحساب 
def calculate_time_based_staff(total_events, time_per_event_min, service_days, staff_work_hours_day, reserve_factor):
    time_per_event_hrs = time_per_event_min / 60
    total_hours_needed = total_events * time_per_event_hrs
    total_staff_available_hours = service_days * staff_work_hours_day
    
    basic_staff = math.ceil(total_hours_needed / total_staff_available_hours) if total_staff_available_hours > 0 else 0
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Time'}

def calculate_ratio_based_staff(num_hajjaj, ratio, reserve_factor):
    basic_staff = math.ceil(num_hajjaj / ratio)
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Ratio'}

def distribute_staff(total_basic_staff, ratio_supervisor, ratio_assistant_head, ratio_head):
    مقدم_خدمة = total_basic_staff  
    مشرفون_اجمالي = math.ceil(مقدم_خدمة / ratio_supervisor)
    مساعد_رئيس = math.ceil(مشرفون_اجمالي / ratio_assistant_head)
    رئيس = math.ceil(مساعد_رئيس / ratio_head)
    إداري = 1 
    
    return {
        "رئيس": رئيس, 
        "مساعد رئيس": مساعد_رئيس, 
        "مشرف ميداني": math.ceil(مشرفون_اجمالي * 0.7), 
        "مشرف اداري": مشرفون_اجمالي - math.ceil(مشرفون_اجمالي * 0.7), 
        "مقدم خدمة": مقدم_خدمة, 
        "اداري": إداري
    }

# تحديد الإدارات وتصنيفها - تم تعديل استقبال الهجرة والمطار والقطار
DEPARTMENTS = {
    "مراكز الضيافة": [
        {"name": "مركز الضيافة", "type": "Ratio", "default_ratio": 75},
    ],
    "الاستقبال والمغادرة": [
        # تم التعديل إلى Ratio: موظف لكل 100 حاج
        {"name": "استقبال الهجرة", "type": "Ratio", "default_ratio": 100},
        {"name": "استقبال المطار", "type": "Ratio", "default_ratio": 100},
        {"name": "استقبال القطار", "type": "Ratio", "default_ratio": 100},
        {"name": "إرشاد الحافلات", "type": "Bus_Ratio", "default_ratio": 2},
    ],
    "الدعم والمساندة": [
        {"name": "المتابعة الميدانية", "type": "Ratio", "default_ratio": 100},
        {"name": "الدعم والضيافة", "type": "Ratio", "default_ratio": 80},
        {"name": "التوجيه", "type": "Ratio", "default_ratio": 90},
        {"name": "الزيارة وإرشاد التأهيل", "type": "Time", "default_time": 2.5},
        {"name": "الرعاية الصحية", "type": "Ratio", "default_ratio": 200},
    ]
}

# -------------------------------------------------------------------
# القسم الأول: الإعدادات العامة ونوع الإدارة
# -------------------------------------------------------------------

st.sidebar.header("1. الإعدادات العامة")

department_type_choice = st.sidebar.selectbox(
    "اختر نوع الإدارة المراد حسابه:",
    options=list(DEPARTMENTS.keys()),
    key="dept_type" 
)

num_hajjaj = st.sidebar.number_input("عدد الحجاج الإجمالي", min_value=1, value=3000, step=100, key="num_hajjaj")
service_days = st.sidebar.number_input("فترة الخدمة الإجمالية (بالأيام)", min_value=1, value=6, key="service_days")
staff_work_hours_day = st.sidebar.number_input("ساعات عمل الموظف اليومية", min_value=1, max_value=16, value=8, key="staff_hours")
reserve_factor_input = st.sidebar.slider("نسبة الاحتياط الإجمالي (%)", min_value=0, max_value=50, value=15, key="reserve_factor_input")
reserve_factor = reserve_factor_input / 100 


# --- المدخلات الخاصة بالهيكل الإداري (التوزيع الهرمي) ---
