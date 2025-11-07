# التعديل المقترح على الدالة (استبدل الدالة الحالية بهذه)

def distribute_staff(total_basic_staff, ratio_supervisor, shifts, required_assistant_heads=0, ratio_assistant_head=DEFAULT_HEAD_ASSISTANT_RATIO):
    """
    توزع موظفي الخدمة على الهيكل الإداري.
    مساعد الرئيس يتم احتسابه بناءً على العدد الإلزامي المُدخَل فقط، مع مراعاة عدد الورديات.
    """
    service_provider = total_basic_staff
    
    # 1. حساب المشرف الميداني (لا تغيير)
    field_supervisor_fixed = SUPERVISORS_PER_SHIFT * shifts
    total_hierarchical_supervisors = math.ceil(service_provider / ratio_supervisor)
    total_supervisors = max(total_hierarchical_supervisors, field_supervisor_fixed)
    
    # 2. حساب مساعد الرئيس (المنطق المعدل)
    if required_assistant_heads > 0:
        # إذا تم إدخال عدد إلزامي (N > 0)، يتم ضربه في عدد الورديات فقط، وإلغاء المنطق الهرمي.
        assistant_head = required_assistant_heads * shifts 
    else:
        # إذا كانت القيمة المُدخلة 0، يكون العدد 0.
        assistant_head = 0
        
    # 3. حساب الرئيس (لا تغيير)
    head = 1
    
    return {
        "Head": head,
        "Assistant_Head": assistant_head,
        "Field_Supervisor": field_supervisor_fixed,
        "Service_Provider": service_provider,
    }
