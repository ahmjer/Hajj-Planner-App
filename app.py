import streamlit as st 
import math
import pandas as pd

# -------------------------------------------------------------------
# التهيئة والدوال (بدون تغيير)
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

def calculate_ratio_based_staff(num_hajjaj_in_center, ratio, reserve_factor):
    basic_staff = math.ceil(num_hajjaj_in_center / ratio)
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
