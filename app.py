import streamlit as st 
import math
import pandas as pd

# -------------------------------------------------------------------
# التهيئة والدوال 
# -------------------------------------------------------------------

st.set_page_config(page_title="🕋 مخطط القوى العاملة للحج", layout="wide") 

st.title("🕋 أداة تخطيط القوى العاملة الذكية")
st.markdown("---")

# 📌 تم تعديل هذه الثوابت لتعكس فترة الـ 8 ساعات
SHIFT_HOURS = 8 
TOTAL_WORK_HOURS = 24
SUPERVISORS_PER_SHIFT = 1
# عدد المشرفين الميدانيين الأساسيين المطلوبين لكل موقع (لتغطية 24 ساعة)
FIELD_SUPERVISORS_PER_LOCATION = math.ceil(TOTAL_WORK_HOURS / SHIFT_HOURS) * SUPERVISORS_PER_SHIFT # 3 مشرفين


def calculate_time_based_staff(total_events, time_per_event_min, service_days, staff_work_hours_day, reserve_factor):
    time_per_event_hrs = time_per_event_min / 60
    total_hours_needed = total_events * time_per_event_hrs
    total_staff_available_hours = service_days * staff_work_hours_day
    
    basic_staff = math.ceil(total_hours_needed / total_staff_available_hours) if total_staff_available_hours > 0 else 0
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Time'}

def calculate_ratio_based_staff(num_hajjaj_in_center, ratio, reserve_factor):
    basic_staff = math.ceil(num_hajjaj_in_center / ratio)
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Ratio'}

# المشرف الميداني الآن هو قيمة ثابتة لكل موقع (3)
def distribute_staff(total_basic_staff, ratio_supervisor, ratio_assistant_head, ratio_head):
    مقدم_خدمة = total_basic_staff  
    
    # 1. المشرفون الميدانيون (محتسبين زمنياً)
    مشرف_ميداني_مخصص = FIELD_SUPERVISORS_PER_LOCATION 
    مشرف_اداري_مخصص = 0 
    
    # 2. الإجمالي المشرفين لغرض الهيكل الإداري (رئيس/مساعد رئيس)
    مشرفون_اجمالي_للهرم = math.ceil(مقدم_خدمة / ratio_supervisor)
    
    # نأخذ أكبر قيمة بين المشرفين الميدانيين الزمنيين ومشرفين الهرم الدنيا (لضمان تغطية كافية للهرم)
    مشرفون_اجمالي = max(مشرفون_اجمالي_للهرم, مشرف_ميداني_مخصص)
    
    مساعد_رئيس = math.ceil(مشرفون_اجمالي / ratio_assistant_head)
    رئيس = math.ceil(مساعد_رئيس / ratio_head)
    إداري = 1 
    
    return {
        "رئيس": رئيس, 
        "مساعد رئيس": مساعد_رئيس, 
        "مشرف ميداني": مشرف_ميداني_مخصص, 
        "مشرف اداري": مشرف_اداري_مخصص, 
        "مقدم خدمة": مقدم_خدمة, 
        "اداري": إداري
    }

# تحديد الإدارات وتصنيفها - بدون تغيير
DEPARTMENTS = {
    "مراكز الضيافة": [
        {"name": "مركز الضيافة", "type": "Ratio", "default_ratio": 75, "default_coverage": 100}, 
    ],
    "الاستقبال والمغادرة": [
        {"name": "استقبال الهجرة", "type": "Ratio", "default_ratio": 100, "default_coverage": 30},
        {"name": "استقبال المطار", "type": "Ratio", "default_ratio": 100, "default_coverage": 50},
        {"name": "استقبال القطار", "type": "Ratio", "default_ratio": 100, "default_coverage": 20},
        {"name": "إرشاد الحافلات", "type": "Bus_Ratio", "default_ratio": 2}, 
    ],
    "الدعم والمساندة": [
        {"name": "المتابعة الميدانية", "type": "Ratio", "default_ratio": 100, "default_coverage": 100},
        {"name": "الدعم والضيافة", "type": "Ratio", "default_ratio": 80, "default_coverage": 100},
        {"name": "التوجيه", "type": "Ratio", "default_ratio": 90, "default_coverage": 100},
        {"name": "الزيارة وإرشاد التأهيل", "type": "Time", "default_time": 2.5, "default_coverage": 100}, 
        {"name": "الرعاية الصحية", "type": "Ratio", "default_ratio": 200, "default_coverage": 100},
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
st.sidebar.header("2. معايير الهيكل الإداري")
st.sidebar.markdown('**نسب الإشراف (للتوزيع الهرمي)**')

ratio_supervisor = st.sidebar.number_input("مقدم خدمة / مشرف", min_value=1, value=8, key="ratio_supervisor")
ratio_assistant_head = st.sidebar.number_input("مشرف / مساعد رئيس", min_value=1, value=4, key="ratio_assistant_head")
ratio_head = st.sidebar.number_input("مساعد رئيس / رئيس", min_value=1, value=3, key="ratio_head")


# -------------------------------------------------------------------
# القسم الثاني: مدخلات الإدارات حسب النوع المختار 
# -------------------------------------------------------------------

st.sidebar.header(f"3. معايير {department_type_choice}")

ratios = {} 
time_based_inputs = {} 
bus_ratio_inputs = {} 
coverage_percentages = {} 

for i, dept in enumerate(DEPARTMENTS[department_type_choice]):
    name = dept['name']
    dept_type = dept['type']
    
    st.sidebar.markdown(f"***_{name}_***") 

    # A. إدخال نسبة التغطية (لكل ما يعتمد على عدد الحجاج)
    if dept_type in ['Ratio', 'Time']:
        default_cov = dept.get('default_coverage', 100)
        coverage_label = f"نسبة تغطية (%)"
        coverage_key = f"cov_{department_type_choice}_{name}_{i}"
        
        coverage_val = st.sidebar.slider(coverage_label, min_value=0, max_value=100, value=default_cov, key=coverage_key)
        coverage_percentages[name] = coverage_val / 100 

    # B. إدخال معيار الاحتساب (Ratio/Time/Bus)
    if dept_type == 'Ratio':
        label = "المعيار (حاج/موظف)"
        key_val = f"ratio_{department_type_choice}_{name}_{i}" 
        ratios[name] = st.sidebar.number_input(label, min_value=1, value=dept['default_ratio'], key=key_val)
    
    elif dept_type == 'Time':
        label = "المعيار (دقيقة/حاج)"
        key_val = f"time_{department_type_choice}_{name}_{i}" 
        time_based_inputs[name] = st.sidebar.number_input(label, min_value=0.5, value=dept['default_time'], step=0.1, key=key_val)

    elif dept_type == 'Bus_Ratio':
        bus_inputs = {'Bus_Count': 0, 'Ratio': 0}
        bus_inputs['Bus_Count']
