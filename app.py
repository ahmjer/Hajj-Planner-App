import streamlit as st 
import math
import pandas as pd

# -------------------------------------------------------------------
# التهيئة والدوال 
# -------------------------------------------------------------------

st.set_page_config(page_title="🕋 مخطط القوى العاملة للحج", layout="wide") 

st.title("🕋 أداة تخطيط القوى العاملة الذكية")
st.markdown("---")

# 📌 ثوابت المشرف الميداني (تم تأكيدها: فترة 8 ساعات)
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
    
    # 2. الإجمالي المشرفين ل
