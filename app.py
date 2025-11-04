import streamlit as st 
import math
import pandas as pd

# -------------------------------------------------------------------
# التهيئة والتعريفات (تم التأكد من سلامة جميع سلاسل النصوص والأقواس)
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

# تحديد الإدارات وتصنيفها - تم استخدام علامات اقتباس مزدوجة في الأسماء التي تسببت في المشكلة
DEPARTMENTS = {
    "مراكز الضيافة": [
        {"name": "مركز الضيافة", "type": "Ratio", "default_ratio": 75},
    ],
    "الاستقبال والمغادرة": [
        {"name": "استقبال الهجرة", "type": "Time", "default_time": 2.0},
        {"name": "استقبال المطار", "type": "Time", "default_time": 3.0},
        {"name": "استقبال القطار", "type": "Time", "default_time": 1.5},
        {"name": "إرشاد الحافلات", "type": "Bus_Ratio", "default_ratio": 2},
    ],
    "الدعم والمساندة": [
        {"name": "المتابعة الميدانية", "type": "Ratio", "default_ratio": 100}, # السطر 59 (تم التأكد من سلامته)
        {"name": "الدعم والضيافة", "type": "Ratio", "default_ratio": 80},
        {"name": "التوجيه", "type": "Ratio", "default_ratio": 90},
        {"name": "الزيارة وإرشاد التأهيل", "type": "Time", "default
