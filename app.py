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
DEFAULT_HEAD_ASSISTANT_RATIO = 4 # رئيس / مساعد رئيس (قيمة افتراضية ثابتة)


def calculate_time_based_staff(total_events, time_per_event_min, service_days, staff_work_hours_day, reserve_factor):
    time_per_event_hrs = time_per_event_min / 60
    total_hours_needed = total_events * time_per_event_hrs
    total_staff_available_hours = service_days * staff_work_hours_day
    
    basic_staff = math.ceil(total_hours_needed / total_staff_available_hours) if total_staff_available_hours > 0 else 0
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Time'}

def calculate_ratio_based_staff(num_hajjaj_in_center, ratio, reserve_factor):
    basic_staff = math.ceil(num_hajjaj_in_center / ratio)
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Ratio'}

# 📌 تم حذف ratio_head من معاملات الدالة
def distribute_staff(total_basic_staff, ratio_supervisor, ratio_assistant_head):
    service_provider = total_basic_staff  
    
    field_supervisor_fixed = FIELD_SUPERVISORS_PER_LOCATION 
    admin_supervisor_fixed = 0 
    
    total_hierarchical_supervisors = math.ceil(service_provider / ratio_supervisor)
    
    total_supervisors = max(total_hierarchical_supervisors, field_supervisor_fixed)
    
    assistant_head = math.ceil(total_supervisors / ratio_assistant_head)
    
    # 📌 تم استخدام الثابت الجديد هنا
    head = math.ceil(assistant_head / DEFAULT_HEAD_ASSISTANT_RATIO) 
    admin_staff = 1 
    
    return {
        "Head": head, 
        "Assistant_Head": assistant_head, 
        "Field_Supervisor": field_supervisor_fixed, 
        "Admin_Supervisor": admin_supervisor_fixed, 
        "Service_Provider": service_provider, 
        "Admin_Staff": admin_staff
    } 

# تم استخدام مفاتيح إنجليزية لتجاوز مشكلة قطع السلاسل النصية العربية 
DEPARTMENTS = {
    "Hospitality": [
        {"name": "Hospitality Center", "type": "Ratio", "default_ratio": 75, "default_coverage": 100}, 
    ],
    "Arrival_Departure":
