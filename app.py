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
    
    # لا نطبق الاحتياط هنا، بل نطبقه على الإجمالي بعد التوزيع الهرمي
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Time'}

def calculate_ratio_based_staff(num_hajjaj, ratio, reserve_factor):
    """تحسب القوى العاملة للإدارات التي تعتمد على التغطية (حاج/موظف)."""
    
    basic_staff = math.ceil(num_hajjaj / ratio)
    # لا نطبق الاحتياط هنا، بل نطبقه على الإجمالي بعد التوزيع الهرمي
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Ratio'}

def distribute_staff(total_basic_staff, ratio_supervisor, ratio_assistant_head, ratio_head):
    """
    توزيع إجمالي الاحتياج (المقدمين) إلى الهرم الإداري.
    """
    
    # 5. مقدم خدمة (يساوي الاحتياج الأساسي للإدارة)
    مقدم_خدمة = total_basic_staff  
    
    # 3+4. المشرفون (ميداني وإداري)
    مشرفون_اجمالي = math.ceil(مقدم_خدمة / ratio_supervisor)
    
    # 2. مساعد رئيس
    مساعد_رئيس = math.ceil(مشرفون_اجمالي / ratio_assistant_head)
    
    # 1. رئيس
    رئيس = math.ceil(مساعد_رئيس / ratio_head)

    # 6. إداري (وظيفة دعم لكل إدارة)
    إداري = 1 
    
    return {
        'رئيس': رئيس,
        'مساعد رئيس': مساعد_رئيس, 
        'مشرف ميداني
