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
        'مقدم خدمة': مقدم_خدمة, 
        'مشرف ميداني': math.ceil(مشرفون_اجمالي * 0.7), 
        'مشرف اداري': مشرفون_اجمالي - math.ceil(مشرفون_اجمالي * 0.7), 
        'مساعد رئيس': مساعد_رئيس, 
        'رئيس': رئيس,
        'اداري': إداري
    }

# -------------------------------------------------------------------
# تحديد الإدارات وتصنيفها
# -------------------------------------------------------------------

DEPARTMENTS = {
    "مراكز الضيافة": [
        {'name': 'مركز الضيافة', 'type': 'Ratio', 'default_ratio': 75},
        {'name': 'الخدمات الميدانية والإسكان', 'type': 'Ratio', 'default_ratio': 50},
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
