import streamlit as st 
import math
import pandas as pd

# -------------------------------------------------------------------
# الثوابت والدوال 
# -------------------------------------------------------------------

# ثوابت المشرف الميداني (تم تأكيدها: فترة 8 ساعات)
SHIFT_HOURS = 8 
TOTAL_WORK_HOURS = 24
SUPERVISORS_PER_SHIFT = 1
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

def distribute_staff(total_basic_staff, ratio_supervisor, ratio_assistant_head, ratio_head):
    مقدم_خدمة = total_basic_staff  
    
    مشرف_ميداني_مخصص = FIELD_SUPERVISORS_PER_LOCATION 
    مشرف_اداري_مخصص = 0 
    
    # الإجمالي المشرفين لغرض الهيكل الإداري (رئيس/مساعد رئيس)
    مشرفون_اجمالي_للهرم = math.ceil(مقدم_خدمة / ratio_supervisor)
    
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

# تحديد الإدارات وتصنيفها 
DEPARTMENTS = {
    "مراكز الضيافة": [
        {"name": "مركز الضيافة", "type": "Ratio", "default_ratio": 75, "default_coverage": 100}, 
    ],
    "الاستقبال والمغادرة": [
        {"name": "استقبال الهجرة", "type": "Ratio", "default_ratio": 100, "default_coverage": 30},
        {"name": "استقبال المطار", "type": "Ratio", "default_ratio": 100, "default_coverage": 50},
        {"name": "استقبال
