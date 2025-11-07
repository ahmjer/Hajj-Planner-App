import streamlit as st
import math
import pandas as pd
from io import BytesIO

# -------------------------------------------------------------------
# 1. الثوابت العامة (Constants)
# -------------------------------------------------------------------

TOTAL_WORK_HOURS = 24
SUPERVISORS_PER_SHIFT = 1
ASSISTANT_HEADS_PER_SHIFT = 1
DEFAULT_HEAD_ASSISTANT_RATIO = 4

# متوسطات الرواتب الافتراضية المحدثة
DEFAULT_SALARY = {
    "رئيس": 37000,
    "مساعد رئيس": 30000,
    "مشرف ميداني": 25000,
    "مقدم خدمة": 8500,
}

# تعريف الإدارات
DEPARTMENTS = {
    "الضيافة": [],
    "الوصول والمغادرة": [
        {"name": "استقبال الهجرة", "type": "Ratio", "default_ratio": 100, "default_coverage": 30, "default_criterion": 'Flow'},
        {"name": "استقبال المطار", "type": "Ratio", "default_ratio": 100, "default_coverage": 50, "default_criterion": 'Flow'},
        {"name": "استقبال القطار", "type": "Ratio", "default_ratio": 100, "default_coverage": 20, "default_criterion": 'Flow'},
        {"name": "إرشاد الحافلات", "type": "Bus_Ratio", "default_ratio": 2, "default_criterion": 'Flow'},
    ],
    "الدعم والمساندة": [
        {"name": "متابعة ميدانية", "type": "Ratio", "default_ratio": 100, "default_coverage": 100, "default_criterion": 'Present'},
        {"name": "الخدمات الميدانية والاسكان ", "type": "Ratio", "default_ratio": 100, "default_coverage": 100, "default_criterion": 'Present'},
        {"name": "الزيارة وإرشاد التأهيين ", "type": "Ratio", "default_ratio": 80, "default_coverage": 100, "default_criterion": 'Present'},
        {"name": " الدعم والضيافة", "type": "Time", "default_time": 2.5, "default_coverage": 100, "default_criterion": 'Present'},
        {"name": "الرعاية صحية", "type": "Ratio", "default_ratio": 200, "default_coverage": 100, "default_criterion": 'Present'},
    ]
}

ALL_DEPARTMENTS_FLAT = {}
for category, depts in DEPARTMENTS.items():
    for dept in depts:
        ALL_DEPARTMENTS_FLAT[dept['name']] = dept.copy()
        ALL_DEPARTMENTS_FLAT[dept['name']]['category'] = category

TRANSLATION_MAP = {
    "Head": "رئيس",
    "Assistant_Head": "مساعد رئيس",
    "Field_Supervisor": "مشرف ميداني",
    "Service_Provider": "مقدم خدمة",
}

# -------------------------------------------------------------------
# 2. الدوال المساعدة للحساب والمنطق
# -------------------------------------------------------------------

def calculate_time_based_staff(total_events, time_per_event_min, service_days, staff_work_hours_day):
    """تحسب الاحتياج بناءً على الوقت اللازم للخدمة الكلية."""
    time_per_event_hrs = time_per_event_min / 60
    total_hours_needed = total_events * time_per_event_hrs
    total_staff_available_hours = service_days * staff_work_hours_day
    
    basic_staff = math.ceil(total_hours_needed / total_staff_available_hours) if total_staff_available_hours > 0 else 0
    return basic_staff

def calculate_ratio_based_staff(num_units, ratio):
    """تحسب الاحتياج بناءً على النسبة (وحدة/موظف)."""
    basic_staff = math.ceil(num_units / ratio)
    return basic_staff

def distribute_staff(total_basic_staff, ratio_supervisor, shifts, required_assistant_heads=0, ratio_assistant_head=DEFAULT_HEAD_ASSISTANT_RATIO):
    """
    توزع مقدمي الخدمة على الهيكل الإداري (مشرفين ورؤساء).
    """
    
    service_provider = total_basic_staff
    
    # 1. تعريف الحدود الدنيا الثابتة لكل دور (حسب عدد الورديات)
    head = 1
    field_supervisor_fixed = SUPERVISORS_PER_SHIFT * shifts
    assistant_head_fixed = required_assistant_heads * shifts
    
    # 2. الحد الأدنى الهرمي للقيادة الإجمالية (رئيس، مساعد رئيس، مشرف) 
    # يجب أن يكون هذا المجموع على الأقل ceil(مقدم الخدمة / ratio_supervisor)
    total_leadership_min_hierarchical = math.ceil(service_provider / ratio_supervisor)

    # 3. حساب القيادة الثابتة الأدنى المضمونة (بغض النظر عن الهرمية)
    leadership_fixed_sum = head + assistant_head_fixed + field_supervisor_fixed

    # 4. مقارنة القيادة الثابتة بالقيادة الهرمية المطلوبة
    if total_leadership_min_hierarchical > leadership_fixed_sum:
        # إذا كانت النسبة الهرمية تتطلب قيادة أكثر من الثابت المضمون:
        # يجب زيادة العدد الإضافي في المشرفين لأنهم المستوى الأوسع في الهرم
        
        # عدد القيادات الإضافي المطلوب
        extra_leadership_needed = total_leadership_min_hierarchical - leadership_fixed_sum
        
        # توزيع الأدوار
        total_supervisors = field_supervisor_fixed + extra_leadership_needed
        assistant_head = assistant_head_fixed
        
    else:
        # إذا كانت القيادة الثابتة المضمونة تحقق النسبة الهرمية أو تتجاوزها
        # نكتفي بالحد الأدنى الثابت لكل دور
        total_supervisors = field_supervisor_fixed
        assistant_head = assistant_head_fixed
        
    # نستخدم الآن القيم المحسوبة والنهائية
    return {
        "Head": head,
        "Assistant_Head": assistant_head,
        "Field_Supervisor": total_supervisors, 
        "Service_Provider": service_provider,
    }

def to_excel(df):
    """تجهيز جدول الاحتياج للتصدير."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=True, sheet_name='احتياج القوى العاملة')
    processed_data = output.getvalue()
    return processed_data

def generate_budget_data(total_staff_per_role, service_days):
    """تحسب بيانات الميزانية وتجهزها للتصدير."""
    budget_data = []
    final_total_monthly_cost = 0
    
    # 1. حساب التكاليف لكل رتبة
    for role, staff_count in total_staff_per_role.items():
        # استخدام الراتب المخزن في session_state أو الافتراضي
        salary = st.session_state.get(f'salary_{role}', DEFAULT_SALARY.get(role, 0))
        monthly_cost = staff_count * salary
        final_total_monthly_cost += monthly_cost
        
        budget_data.append({
            "الرتبة الوظيفية": role,
            "العدد الإجمالي المطلوب": staff_count,
            "متوسط الراتب الشهري (ريال)": salary,
            "التكلفة الشهرية الإجمالية (ريال)": monthly_cost
        })

    # تكلفة المشروع هي التكلفة الشهرية مضروبة في مدة الخدمة/30 يوم
    total_project_cost = final_total_monthly_cost / 30 * service_days
    
    df_budget = pd.DataFrame(budget_data)
    
    # 2. إنشاء ملف Excel متعدد الأوراق
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        # الورقة 1: جدول تفاصيل الرتب
        df_budget.to_excel(writer, index=False, sheet_name='تفاصيل_الرواتب_الشهرية')

        # الورقة 2: ملخص الإجماليات
        summary_data = {
            "البيان": ["إجمالي التكلفة الشهرية (ريال)", f"إجمالي تكلفة المشروع ({service_days} يوم) (ريال)", "إجمالي الموظفين (بدون احتياط)"],
            "القيمة": [final_total_monthly_cost, total_project_cost, sum(total_staff_per_role.values())]
        }
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, startrow=1, startcol=1, index=False, sheet_name='ملخص_الميزانية')
        
    return output.getvalue()


def to_excel_budget(total_staff_per_role, service_days):
    """تستدعي دالة إنشاء البيانات وتسترجع بايتات ملف Excel للميزانية."""
    return generate_budget_data(total_staff_per_role, service_days)

def add_hospitality_center():
    """تضيف مركز ضيافة جديد إلى القائمة الديناميكية."""
    new_id = st.session_state.next_center_id
    new_center = {
        'id': new_id, 
        'name': f'مركز ضيافة #{new_id}', 
        'hajjaj_count': st.session_state.get('num_hajjaj_present', 5000), # القيمة الافتراضية
        'active': True
    }
    st.session_state.dynamic_hospitality_centers.append(new_center)
    st.session_state.next_center_id += 1
    st.session_state['run_calculation_all'] = False # لمنع الحساب التلقائي بعد الإضافة

def remove_hospitality_center(center_id_to_remove):
    """تزيل مركز ضيافة بناءً على مُعرفه (ID)."""
    st.session_state.dynamic_hospitality_centers = [
        c for c in st.session_state.dynamic_hospitality_centers 
        if c['id'] != center_id_to_remove
    ]
    # يجب إزالة إعدادات النسبة المخزنة في user_settings_all أيضاً لتجنب استخدام نسبة مركز محذوف
    ratio_key = f"Hosp_Ratio_{center_id_to_remove}"
    if 'user_settings_all' in st.session_state and ratio_key in st.session_state['user_settings_all']:
        del st.session_state['user_settings_all'][ratio_key]
    st.session_state['run_calculation_all'] = False # لمنع الحساب التلقائي بعد الحذف

# -------------------------------------------------------------------
# 3. منطق الشاشة الموحدة الجديدة (All Departments Page Logic)
# -------------------------------------------------------------------

def all_departments_page():
    st.title("📊 تخطيط القوى العاملة الموحد")
    st.markdown("---")
    
    st.subheader("1. ضبط معايير الاحتساب لجميع الإدارات")
    
    if 'user_settings_all' not in st.session_state:
          st.session_state['user_settings_all'] = {}
          
    user_settings = st.session_state['user_settings_all']
    
    # --- إدارة المراكز الديناميكية (خارج النموذج) ---
    st.markdown("#### 🏷️ الضيافة")
    
    # نستخدم حاوية بسيطة بدون حدود لإزالة المربع المحيط
    with st.container(): 
        st.button("➕ إضافة مركز ضيافة جديد", on_click=add_hospitality_center, type="secondary", key="add_hosp_center_btn")
        st.markdown("---") # فاصل واضح للقسم
        
        st.markdown("**مراكز الضيافة الديناميكية (إدارة الإغلاق/الفتح وتحديد الحجاج)**")
        
        # نستخدم نسخة من القائمة لتفادي مشاكل التكرار والحالة أثناء الحذف
        centers_to_display = st.session_state.dynamic_hospitality_centers[:]
        
        # تم إصلاح المسافة البادئة ومشاكل الـ Expander
        for i, center in enumerate(centers_to_display):
            center_id = center['id']
            
            # استخدام expander لعرض تفاصيل كل مركز (تم استخدام التسمية كعنوان فقط لإزالة النص التقني)
            with st.expander(f"مركز الضيافة #{center_id}: {center['name']}", expanded=True):
                
                # استخدام أعمدة لتنظيم المدخلات
                col_status, col_name, col_hajjaj, col_remove = st.columns([1, 2, 2, 1])
                
                # 1. زر الإغلاق/الفتح (Toggle)
                # يجب تحديث القيمة في القائمة الأصلية مباشرة
                new_active = col_status.toggle(
                    "مفعل", 
                    value=center.get('active', True), 
                    key=f"hosp_active_{center_id}"
                )
                
                # ابحث عن المركز في القائمة الأصلية وحدث قيمته
                for idx, c in enumerate(st.session_state.dynamic_hospitality_centers):
                    if c['id'] == center_id:
                        st.session_state.dynamic_hospitality_centers[idx]['active'] = new_active
                        break


                # 2. اسم المركز
                new_name = col_name.text_input(
                    "اسم المركز", 
                    value=center.get('name', f'مركز ضيافة #{center_id}'), 
                    key=f"hosp_name_{center_id}"
                )
                for idx, c in enumerate(st.session_state.dynamic_hospitality_centers):
                    if c['id'] == center_id:
                        st.session_state.dynamic_hospitality_centers[idx]['name'] = new_name
                        break


                # 3. عدد حجاج المركز
                new_hajjaj_count = col_hajjaj.number_input(
                    "عدد الحجاج/الزوار (تقديري)",
                    min_value=1, 
                    value=center.get('hajjaj_count', st.session_state['num_hajjaj_present']), 
                    step=100, 
                    key=f"hosp_hajjaj_{center_id}"
                )
                for idx, c in enumerate(st.session_state.dynamic_hospitality_centers):
                    if c['id'] == center_id:
                        st.session_state.dynamic_hospitality_centers[idx]['hajjaj_count'] = new_hajjaj_count
                        break
                
                # 4. زر الإزالة (خارج النموذج)
                col_remove.button(
                    "🗑️ إزالة", 
                    on_click=remove_hospitality_center, 
                    args=(center_id,), 
                    key=f"hosp_remove_{center_id}"
                )


    st.markdown("---")
    
    # --- ضبط المعايير العامة ونسبة الضيافة (داخل النموذج) ---
    with st.form("all_dept_criteria_form"):
        
        # 1. مدخلات نسبة الضيافة (داخل النموذج)
        st.markdown("#### ⚙️ معيار نسبة مقدمي الخدمة لمراكز الضيافة")
        with st.container(border=True): # مربع لمدخلات الضيافة
            for i, center in enumerate(st.session_state.dynamic_hospitality_centers[:]):
                if center['active']:
                    center_id = center['id']
                    ratio_key = f"Hosp_Ratio_{center_id}"
                    default_ratio = user_settings.get(ratio_key, 200) 
                    
                    new_ratio = st.number_input(
                        f"المعيار (حاج/موظف) لـ **{center['name']}**", 
                        min_value=1, 
                        value=default_ratio,
                        key=f"hosp_ratio_form_{center_id}"
                    )
                    # التخزين المؤقت للإعدادات
                    user_settings[ratio_key] = new_ratio
        
        st.markdown("---")
        
        # 2. مدخلات الإدارات الثابتة الأخرى
        for category_name, depts in DEPARTMENTS.items():
            if category_name == "الضيافة": 
                continue 

            st.markdown(f"#### 🏷️ {category_name}")
            st.markdown("---") # فاصل واضح بين الإدارات الرئيسية
            
            cols = st.columns(3)
            col_index = 0
            
            for i, dept in enumerate(depts):
                name = dept['name']
                dept_type = dept['type']
                col = cols[col_index % 3]
                col_index += 1
                
                # تهيئة الإعدادات الافتراضية
                if name not in user_settings:
                    user_settings[name] = {
                        'criterion': dept.get('default_criterion', 'Present'),
                        'coverage': dept.get('default_coverage', 100) / 100,
                        'ratio': dept.get('default_ratio', 1),
                        'time': dept.get('default_time', 1),
                        'bus_count': 20, 
                        'events_multiplier': 2,
                        'required_assistant_heads': 0 
                    }
                
                with col:
                    # إضافة مربع حول كل قسم فرعي
                    with st.container(border=True): 
                        st.markdown(f"***_{name}_***")
                        
                        # مدخل مساعد الرئيس الإلزامي
                        asst_head_req_val = st.number_input(
                            "مساعد رئيس إلزامي لكل وردية (0 = لا يوجد)", 
                            min_value=0, 
                            value=user_settings[name]['required_assistant_heads'], 
                            step=1, 
                            key=f"all_asst_head_req_{name}_{i}"
                        )
                        
                        # --- بقية المدخلات (معيار، تغطية، نسبة/وقت/حافلات) ---
                        criterion_options = ['المتواجدين (حجم)', 'التدفق اليومي (حركة)']
                        criterion_choice_text = st.radio(
                            "المعيار", 
                            options=criterion_options,
                            index=0 if user_settings[name]['criterion'] == 'Present' else 1,
                            key=f"all_crit_{name}_{i}"
                        )
                        
                        if dept_type in ['Ratio', 'Time']:
                            coverage_val = st.number_input(
                                "نسبة تغطية (%)", 
                                min_value=0, max_value=100, 
                                value=int(user_settings[name]['coverage'] * 100), 
                                step=1, 
                                key=f"all_cov_{name}_{i}"
                            )

                        if dept_type == 'Ratio':
                            ratio_val = st.number_input("المعيار (وحدة/موظف)", min_value=1, value=user_settings[name]['ratio'], key=f"all_ratio_{name}_{i}")
                            
                        elif dept_type == 'Time':
                            time_val = st.number_input("المعيار (دقيقة/وحدة)", min_value=0.5, value=user_settings[name]['time'], step=0.1, key=f"all_time_{name}_{i}")
                            multiplier_val = st.number_input("معامل أحداث الحاج (x)", min_value=1, value=user_settings[name]['events_multiplier'], key=f"all_mult_{name}_{i}")
                            
                        elif dept_type == 'Bus_Ratio':
                            bus_count_val = st.number_input("عدد الحافلات المتوقع", min_value=1, value=user_settings[name]['bus_count'], key=f"all_bus_count_{name}_{i}")
                            bus_ratio_val = st.number_input("المعيار (حافلة/موظف)", min_value=1, value=user_settings[name]['ratio'], key=f"all_bus_ratio_{name}_{i}")
        
        st.markdown("---")
        # زر الإرسال الوحيد المسموح به داخل النموذج
        calculate_button = st.form_submit_button("🔄 احتساب وعرض النتائج الموحدة", type="primary")

    # 2. التحديث وتخزين إعدادات المستخدم بعد الضغط على Submit
    if calculate_button:
        
        # تحديث إعدادات الإدارات الثابتة
        for category_name, depts in DEPARTMENTS.items():
            if category_name == "الضيافة": continue

            for i, dept in enumerate(depts):
                name = dept['name']
                dept_type = dept['type']

                asst_head_key = f"all_asst_head_req_{name}_{i}"
                user_settings[name]['required_assistant_heads'] = st.session_state[asst_head_key]

                criterion_options = ['المتواجدين (حجم)', 'التدفق اليومي (حركة)'] 
                crit_key = f"all_crit_{name}_{i}"
                # هذا الجزء كان مبتوراً، وتم إكماله
                criterion_value = st.session_state.get(crit_key, criterion_options[0])
                user_settings[name]['criterion'] = 'Present' if criterion_value == criterion_options[0] else 'Flow'

                if dept_type in ['Ratio', 'Time']:
                    cov_key = f"all_cov_{name}_{i}"
                    user_settings[name]['coverage'] = st.session_state[cov_key] / 100
                    
                if dept_type == 'Ratio':
                    ratio_key = f"all_ratio_{name}_{i}"
                    user_settings[name]['ratio'] = st.session_state[ratio_key]
                    
                elif dept_type == 'Time':
                    time_key = f"all_time_{name}_{i}"
                    mult_key = f"all_mult_{name}_{i}"
                    user_settings[name]['time'] = st.session_state[time_key]
                    user_settings[name]['events_multiplier'] = st.session_state[mult_key]
                    
                elif dept_type == 'Bus_Ratio':
                    bus_count_key = f"all_bus_count_{name}_{i}"
                    bus_ratio_key = f"all_bus_ratio_{name}_{i}"
                    user_settings[name]['bus_count'] = st.session_state[bus_count_key]
                    user_settings[name]['ratio'] = st.session_state[bus_ratio_key]
                    
        st.session_state['user_settings_all'] = user_settings
        st.session_state['run_calculation_all'] = True 
        st.rerun() 
        
    # 3. الحساب والعرض (يتم عند استدعاء rerun)
    if st.session_state.get('run_calculation_all', False):
        
        st.session_state['run_calculation_all'] = False 
        
        st.success("✅ جاري بدء الحساب الموحد بناءً على معاييرك المخصصة...")
        
        # جلب المدخلات العامة
        num_hajjaj_present = st.session_state['num_hajjaj_present']
        num_hajjaj_flow = st.session_state['num_hajjaj_flow']
        service_days = st.session_state['service_days']
        staff_work_hours_day = st.session_state['staff_hours']
        reserve_factor = st.session_state['reserve_factor_input'] / 100
        shifts_count = st.session_state['shifts_count']
        ratio_supervisor = st.session_state['ratio_supervisor']
        ratio_assistant_head = st.session_state['ratio_assistant_head']

        hajjaj_data = {'Present': num_hajjaj_present, 'Flow': num_hajjaj_flow}

        all_results = []
        total_staff_needed = 0

        # 1. عملية الحساب لمراكز الضيافة الديناميكية
        for center in st.session_state.dynamic_hospitality_centers:
            if center['active']:
                center_id = center['id']
                dept_name = center['name']
                hajjaj_count = center['hajjaj_count']
                ratio = st.session_state['user_settings_all'].get(f"Hosp_Ratio_{center_id}", 200) 
                
                # المعيار هنا: حاج/10 وحدات مقابل موظف
                num_units_to_serve = hajjaj_count / 10 
                res_basic = calculate_ratio_based_staff(num_units_to_serve, ratio)
                res_basic = max(1, res_basic)
                
                # تطبيق الهيكل الإداري: 1 مساعد رئيس إلزامي لكل وردية (فرض ثابت للضيافة)
                staff_breakdown = distribute_staff(
                    res_basic, 
                    ratio_supervisor, 
                    shifts_count, 
                    required_assistant_heads=1, 
                    ratio_assistant_head=ratio_assistant_head
                )
                
                total_staff_in_hierarchy = sum(staff_breakdown.values())
                total_needed_with_reserve = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

                translated_breakdown = {TRANSLATION_MAP.get(k, k): v for k, v in staff_breakdown.items()}
                
                result_entry = {"الإدارة": dept_name, "القسم": "الضيافة"}
                result_entry.update(translated_breakdown)
                result_entry["المجموع الإجمالي (بالاحتياط)"] = total_needed_with_reserve

                all_results.append(result_entry)
                total_staff_needed += total_needed_with_reserve


        # 2. عملية الحساب للإدارات الثابتة الأخرى
        
        fixed_depts_flat = {k: v for k, v in ALL_DEPARTMENTS_FLAT.items() if v['category'] != 'الضيافة'}
        
        for dept_name, dept_info in fixed_depts_flat.items():
            
            dept_type = dept_info['type']
            settings = st.session_state['user_settings_all'][dept_name]
            
            res_basic = 0
            
            # منطق حساب res_basic (Ratio, Bus_Ratio, Time)
            if dept_type == 'Ratio':
                ratio = settings['ratio']
                criterion = settings['criterion']
                coverage = settings['coverage']
                num_hajjaj_for_dept = hajjaj_data[criterion]
                actual_hajjaj_in_center = num_hajjaj_for_dept * coverage
                res_basic = calculate_ratio_based_staff(actual_hajjaj_in_center, ratio)
                
            elif dept_type == 'Bus_Ratio':
                num_units = settings['bus_count']
                bus_ratio = settings['ratio']
                res_basic = calculate_ratio_based_staff(num_units, bus_ratio)
                
            elif dept_type == 'Time':
                time_min = settings['time']
                criterion = settings['criterion']
                coverage = settings['coverage']
                multiplier = settings['events_multiplier']
                num_hajjaj_for_dept = hajjaj_data[criterion]
                actual_hajjaj_in_center = num_hajjaj_for_dept * coverage
                res_basic = calculate_time_based_staff(actual_hajjaj_in_center * multiplier, time_min, service_days, staff_work_hours_day)
            
            # ضمان أن الاحتياج الأساسي لا يقل عن 1 إذا كانت الإدارة موجودة
            if res_basic == 0 and dept_type != 'Bus_Ratio':
                 res_basic = max(1, res_basic)
                
            # تطبيق الهيكل الإداري (يستخدم قيمة الإدخال من النموذج)
            required_assistant_heads = settings['required_assistant_heads'] 
            
            staff_breakdown = distribute_staff(
                res_basic, 
                ratio_supervisor, 
                shifts_count, 
                required_assistant_heads=required_assistant_heads, 
                ratio_assistant_head=ratio_assistant_head
            )
            
            total_staff_in_hierarchy = sum(staff_breakdown.values())
            total_needed_with_reserve = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

            translated_breakdown = {TRANSLATION_MAP.get(k, k): v for k, v in staff_breakdown.items()}
            
            result_entry = {"الإدارة": dept_name, "القسم": dept_info['category']}
            result_entry.update(translated_breakdown)
            result_entry["المجموع الإجمالي (بالاحتياط)"] = total_needed_with_reserve

            all_results.append(result_entry)
            total_staff_needed += total_needed_with_reserve
            
        st.success("✅ اكتمل الحساب. جاري عرض النتائج.")
        
        # 4. عرض النتائج
        st.subheader("2. جدول الاحتياج الموحد والنتائج")
        
        column_order = [
            "القسم", "رئيس", "مساعد رئيس", "مشرف ميداني",
            "مقدم خدمة", "المجموع الإجمالي (بالاحتياط)"
        ]
        
        df = pd.DataFrame(all_results)
        df = df.set_index("الإدارة")
        df = df[column_order]
        
        st.dataframe(df, use_container_width=True)
        
        # 5. تخزين الإجماليات
        total_staff_per_role = {}
        for role_arabic in [TRANSLATION_MAP[k] for k in TRANSLATION_MAP.keys()]:
            if role_arabic in df.columns:
                total_staff_per_role[role_arabic] = df[role_arabic].sum()
        
        st.session_state['total_staff_per_role'] = total_staff_per_role
        st.session_state['total_budget_needed'] = total_staff_needed 
        
        # 6. التصدير
        service_days = st.session_state['service_days']
        for role, default_salary in DEFAULT_SALARY.items():
            if f'salary_{role}' not in st.session_state:
                 st.session_state[f'salary_{role}'] = default_salary

        col_download, col_budget_btn = st.columns(2)
        
        with col_download:
            excel_data = to_excel(df)
            st.download_button(
                label="📥 تصدير الجدول الموحد إلى ملف Excel",
                data=excel_data,
                file_name='تخطيط_القوى_العاملة_الموحد.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                type="secondary"
            )
            
        with col_budget_btn:
            st.download_button(
                label="💰 **تصدير ميزانية الرواتب (Excel)**",
                data=to_excel_budget(total_staff_per_role, service_days),
                file_name='ميزانية_الرواتب_التقديرية.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                type="primary",
                key="download_budget_excel"
            )

        st.markdown("---")

        # 7. عرض الإجمالي
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label=f"**المجموع الكلي للقوى العاملة المطلوبة في جميع الأقسام (مع الاحتياط)**",
                value=f"{total_staff_needed} موظف",
            )
        with col2:
            st.info(f"نسبة الاحتياط الإجمالية المطبقة: {st.session_state['reserve_factor_input']}%")
            
    else:
        st.info("⬆️ يرجى إدخال أو مراجعة معايير الاحتساب ثم الضغط على زر **'احتساب وعرض النتائج الموحدة'** في نهاية الصفحة.")


# -------------------------------------------------------------------
# 4. الواجهة الرئيسية (Streamlit UI Setup) وبداية التطبيق
# -------------------------------------------------------------------

def main():
    
    # 1. تهيئة صفحة Streamlit
    st.set_page_config(page_title="مخطط القوى العاملة الموحد", layout="wide", page_icon=None)

    # 2. تهيئة مفاتيح session_state (تم حذف 'current_page' و 'main')
    if 'run_calculation_all' not in st.session_state:
        st.session_state['run_calculation_all'] = False
    if 'dynamic_hospitality_centers' not in st.session_state:
        st.session_state['dynamic_hospitality_centers'] = [
            {'id': 1, 'name': 'مركز ضيافة #1', 'hajjaj_count': st.session_state.get('num_hajjaj_present', 5000), 'active': True}
        ]
    if 'next_center_id' not in st.session_state:
        st.session_state['next_center_id'] = 2
    if 'user_settings_all' not in st.session_state:
         st.session_state['user_settings_all'] = {}
    
    # تهيئة الرواتب الافتراضية
    for role, default_salary in DEFAULT_SALARY.items():
        if f'salary_{role}' not in st.session_state:
             st.session_state[f'salary_{role}'] = default_salary


    # 3. كود CSS للتنسيق (تم تحديث الخط إلى Cairo)
    st.markdown("""
    <style>
    /* 1. استيراد خط Cairo من Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;700&display=swap');

    /* 2. تطبيق الخط Cairo على جميع العناصر (معزز) */
    html, body, 
    [class*="st-emotion-"], 
    [data-testid*="st"], 
    h1, h2, h3, h4, h5, h6, 
    p, div, label, span, button, input, textarea, select { 
        font-family: 'Cairo', sans-serif !important; 
        direction: rtl !important; 
    }

    /* 3. تطبيق التنسيق على عناوين st.expander لتكون في المنتصف وخط غامق */
    /* يستهدف العنوان الرئيسي لـ expander */
    .st-emotion-cache-p2n4nh { 
        text-align: center !important; 
    }

    /* يستهدف النص الفعلي داخل العنوان (للتأثير على الغمق والتوسيط) */
    .st-emotion-cache-p2n4nh > div > div > span { 
        font-weight: 700 !important;
    }

    /* 4. تنسيق المربعات الداخلية للإدارات (خلفية أغمق) */
    /* تستهدف الحاويات ذات الحدود داخل الأعمدة */
    div[data-testid*="stVerticalBlock"] > div[data-testid*="stVerticalBlock"] > div[data-testid*="stVerticalBlock"] > div[data-testid*="stContainer"] {
        background-color: #f0f0f0 !important; 
        border-radius: 5px; 
        padding: 10px;
    }

    /* 5. إعدادات تنسيقية سابقة */
    [data-testid="stAppViewBlockContainer"] { padding-top: 30px !important; }
    .custom-header-line { position: fixed; top: 0; left: 0; width: 100%; height: 20px; background-color: #800020; z-index: 9999; }
    section[data-testid="stSidebar"] { text-align: right; transform: none !important; left: auto; right: 0; }
    [data-testid="stSidebarContent"] { direction: rtl; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="custom-header-line"></div>', unsafe_allow_html=True)


    # 4. الشريط الجانبي (Sidebar)
    with st.sidebar:
        st.title("إعدادات مخطط القوى العاملة") 
        st.markdown("---")

        st.header("1. الإعدادات العامة")
        st.number_input(
            "1. إجمالي عدد الحجاج (المتواجدين)",
            min_value=1, value=st.session_state.get("num_hajjaj_present", 5000), step=100, key="num_hajjaj_present"
        )
        st.number_input(
            "2. إجمالي حجاج التدفق اليومي (وصول/مغادرة)",
            min_value=1, value=st.session_state.get("num_hajjaj_flow", 1000), step=100, key="num_hajjaj_flow"
        )
        st.number_input("فترة الخدمة الإجمالية (بالأيام)", min_value=1, value=st.session_state.get("service_days", 6), key="service_days")
        st.number_input("ساعات عمل الموظف اليومية", min_value=1, max_value=16, value=st.session_state.get("staff_hours", 8), key="staff_hours")
        st.slider("نسبة الاحتياط الإجمالي (%)", min_value=0, max_value=50, value=st.session_state.get("reserve_factor_input", 15), key="reserve_factor_input")

        st.header("2. معايير الهيكل الإداري")
        st.markdown('**نسب الإشراف (للتوزيع الهرمي)**')
        st.selectbox(
            "عدد فترات العمل اليومية المطلوبة",
            options=[1, 2, 3], index=2, key="shifts_count"
        )
        st.number_input("مقدم خدمة / مشرف", min_value=1, value=st.session_state.get("ratio_supervisor", 8), key="ratio_supervisor")
        st.number_input("مشرف / مساعد رئيس (للهرم)", min_value=1, value=st.session_state.get("ratio_assistant_head", 4), key="ratio_assistant_head")
        
        st.markdown("---")
        
        st.header("3. إعدادات الميزانية")
        st.markdown("تعديل متوسطات الرواتب الشهرية (ريال):")
        for role, default_salary in DEFAULT_SALARY.items():
            st.number_input(
                f"راتب **{role}**", 
                min_value=1000, 
                value=st.session_state.get(f'salary_{role}', default_salary),
                step=500,
                key=f'salary_{role}'
            )


    # 5. عرض الشاشة الوحيدة المتبقية
    all_departments_page()


# نقطة الدخول الرئيسية للتطبيق
if __name__ == '__main__':
    main()
