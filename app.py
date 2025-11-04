import streamlit as st
import math
import pandas as pd

# -------------------------------------------------------------------
# الدوال المساعدة للحساب (Logic)
# -------------------------------------------------------------------

def calculate_time_based_staff(total_events, time_per_event_min, service_days, staff_work_hours_day, reserve_factor):
    """تحسب القوى العاملة للإدارات التي تعتمد على الزمن (مثل الاستقبال)."""
    
    time_per_event_hrs = time_per_event_min / 60
    total_hours_needed = total_events * time_per_event_hrs
    total_staff_available_hours = service_days * staff_work_hours_day
    
    if total_staff_available_hours > 0:
        basic_staff = math.ceil(total_hours_needed / total_staff_available_hours)
    else:
        basic_staff = 0
    
    total_staff = math.ceil(basic_staff * (1 + reserve_factor))
    return {'Basic': basic_staff, 'Total': total_staff, 'CalcType': 'Time'}

def calculate_ratio_based_staff(num_hajjaj, ratio, reserve_factor):
    """تحسب القوى العاملة للإدارات التي تعتمد على التغطية (حاج/موظف)."""
    
    basic_staff = math.ceil(num_hajjaj / ratio)
    total_staff = math.ceil(basic_staff * (1 + reserve_factor))
    return {'Basic': basic_staff, 'Total': total_staff, 'CalcType': 'Ratio'}

# ******** تم تصحيح المسافات البادئة في هذه الدالة *********
def distribute_staff(total_basic_staff, ratio_supervisor, ratio_assistant_head, ratio_head):
    """
    توزيع إجمالي الاحتياج (المقدمين) إلى الهرم الإداري.
    """
    
    # 1. مقدم الخدمة هو الاحتياج الأساسي 
    مقدم_خدمة = total_basic_staff  # <--- هذا السطر تم تعديل مسافته البادئة
    
    # 2. المشرفون (ميداني وإداري)
    مشرفون = math.ceil(مقدم_خدمة / ratio_supervisor)
    
    # 3. مساعدو الرؤساء
    مساعد_رئيس = math.ceil(مشرفون / ratio_assistant_head)
    
    # 4. الرؤساء
    رئيس = math.ceil(مساعد_رئيس / ratio_head)

    # 5. الإداريون (وظائف الدعم غير المباشر): 1 إداري لكل إدارة كحد أدنى
    إداري = 1 
    
    return {
        'مقدم_خدمة': مقدم_خدمة, 
        'مشرف_ميداني': math.ceil(مشرفون * 0.7), # توزيع المشرفين بنسبة 70% ميداني
        'مشرف_إداري': مشرفون - math.ceil(مشرفون * 0.7), # و 30% إداري
        'مساعد_رئيس': مساعد_رئيس,
        'رئيس': رئيس,
        'إداري': إداري
    }

# -------------------------------------------------------------------
# واجهة المستخدم (Streamlit UI)
# -------------------------------------------------------------------

st.set_page_config(page_title="🕋 مخطط القوى العاملة للحج (بالهيكلة الوظيفية)", layout="wide")

st.title("🕋 أداة تخطيط القوى العاملة الذكية (بالهيكلة الوظيفية)")
st.markdown("---")

st.sidebar.header("1. الإعدادات العامة للبعثة")

# المدخلات العامة في الشريط الجانبي (Sidebar)
num_hajjaj = st.sidebar.number_input("عدد الحجاج الإجمالي", min_value=1, value=3000, step=100)
service_days = st.sidebar.number_input("فترة الخدمة الإجمالية (بالأيام)", min_value=1, value=6)
staff_work_hours_day = st.sidebar.number_input("ساعات عمل الموظف اليومية", min_value=1, max_value=16, value=8)
reserve_factor_input = st.sidebar.slider("نسبة الاحتياط الإجمالي (%)", min_value=0, max_value=50, value=15)
reserve_factor = reserve_factor_input / 100 # تحويل لكسر عشري


# --- المدخلات الخاصة بالهيكل الإداري (التوزيع الهرمي) ---
st.sidebar.header("2. معايير الهيكل الإداري")
st.sidebar.markdown('**نسب الإشراف (للتوزيع الهرمي)**')
ratio_supervisor = st.sidebar.number_input("مقدم خدمة / مشرف", min_value=1, value=8)
ratio_assistant_head = st.sidebar.number_input("مشرف / مساعد رئيس", min_value=1, value=4)
ratio_head = st.sidebar.number_input
