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
    يطبق التعديل الجديد: الحد الأدنى للقيادة الإجمالية (رئيس+مساعد رئيس+مشرف) يُحسب مقابل مقدمي الخدمة.
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
        'hajjaj_count': st.session_state['num_hajjaj_present'], # القيمة الافتراضية
        'active': True
    }
    st.session_state.dynamic_hospitality_centers.append(new_center)
    st.session_state.next_center_id += 1

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


# -------------------------------------------------------------------
# 3. وظائف مساعدة للتبديل بين الصفحات
# -------------------------------------------------------------------

def switch_to_main():
    st.session_state['current_page'] = 'main'
    st.session_state['run_calculation_all'] = False

def switch_to_all():
    st.session_state['current_page'] = 'all'

# -------------------------------------------------------------------
# 4. منطق الشاشة الموحدة الجديدة (All Departments Page Logic)
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
    st.button("➕ إضافة مركز ضيافة جديد", on_click=add_hospitality_center, type="secondary", key="add_hosp_center_btn")
    st.markdown("---") # فاصل واضح للقسم
    
    # نستخدم حاوية لعرض المراكز التي يمكن إدارتها خارج النموذج
    with st.container(border=True):
        st.markdown("**مراكز الضيافة الديناميكية (إدارة الإغلاق/الفتح وتحديد الحجاج)**")
        
        # نستخدم نسخة من القائمة لتفادي مشاكل التكرار والحالة أثناء الحذف
        centers_to_display = st.session_state.dynamic_hospitality_centers[:]
        
        for i, center in enumerate(centers_to_display):
            if i >= len(st.session_state.dynamic_hospitality_centers): # فحص إضافي
                 continue
                 
            center_id = center['id']
            
            with st.expander(f"مركز الضيافة #{center_id}: {center['name']}", expanded=True):
                
                # استخدام أعمدة لتنظيم المدخلات
                col_status, col_name, col_hajjaj, col_remove = st.columns([1, 2, 2, 1])
                
                # 1. زر الإغلاق/الفتح (Toggle)
                new_active = col_status.toggle(
                    "مفعل",
                    value=center.get('active', True),
                    key=f"hosp_active_{center_id}"
                )
                st.session_state.dynamic_hospitality_centers[i]['active'] = new_active

                # 2. اسم المركز
                new_name = col_name.text_input(
                    "اسم المركز",
                    value=center.get('name', f'مركز ضيافة #{center_id}'),
                    key=f"hosp_name_{center_id}"
                )
                st.session_state.dynamic_hospitality_centers[i]['name'] = new_name

                # 3. عدد حجاج المركز
                new_hajjaj_count = col_hajjaj.number_input(
                    "عدد الحجاج/الزوار (تقديري)",
                    min_value=1,
                    value=center.get('hajjaj_count', st.session_state['num_hajjaj_present']),
                    step=100,
                    key=f"hosp_hajjaj_{center_id}"
                )
                st.session_state.dynamic_hospitality_centers[i]['hajjaj_count'] = new_hajjaj_count
                
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
                        key=f"hosp_ratio_{center_id}"
                    )
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
                    # تم إضافة كلاس CSS مخصص هنا لتغيير اللون
                    st.markdown(f"""
                        <style>
                            .darker-container {{
                                background-color: #f0f2f6; /* لون خلفية أغمق قليلاً من الأبيض */
                                padding: 10px;
                                border-radius: 5px;
                                border: 1px solid rgba(49, 51, 63, 0.2);
                                margin-bottom: 10px;
                            }}
                        </style>
                        <div class="darker-container">
                            ***_{name}_***
                        </div>
                    """, unsafe_allow_html=True)
                    
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
        
        # ... (منطق تحديث الإعدادات ... )
        for category_name, depts in DEPARTMENTS.items():
            if category_name == "الضيافة": continue

            for i, dept in enumerate(depts):
                name = dept['name']
                dept_type = dept['type']

                asst_head_key = f"all_asst_head_req_{name}_{i}"
                user_settings[name]['required_assistant_heads'] = st.session_state[asst_head_key]

                criterion_options = ['المتواجدين (حجم)', 'التدفق اليومي (حركة)']
                crit_key = f"all_crit_{name}_{i}"
                user_settings[name]['criterion'] = 'Present' if st.session_state[crit_key] == criterion_options[0] else 'Flow'

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
                
                num_units_to_serve = hajjaj_count / 10
                res_basic = calculate_ratio_based_staff(num_units_to_serve, ratio)
                res_basic = max(1, res_basic)
                
                # تطبيق الهيكل الإداري: 1 مساعد رئيس إلزامي لكل وردية
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
# 5. الدالة الرئيسية للشاشة الافتراضية (Main Page Logic)
# -------------------------------------------------------------------

def main_page_logic():
    st.title(" تخطيط القوى العاملة (حساب فردي) ")
    st.markdown("---")

    st.info("⚠️ **لإدخال معايير الحساب:** يرجى فتح **القائمة الجانبية (☰)** في أعلى اليمين/اليسار أولاً.", icon="ℹ️")

    st.subheader("5. معايير الهيكل الإداري الإضافية للإدارة المحددة")
    
    required_assistant_heads_per_shift = st.number_input(
        "عدد مساعدي الرئيس المطلوبين إلزاميًا لكل وردية في الإدارة (0 = لا يوجد)",
        min_value=0,
        value=0,
        step=1,
        key="required_assistant_heads_main"
    )
    
    st.subheader("4. تحديد الإدارة ومعايير الاحتساب")
    department_type_choice = st.selectbox(
        "اختر نوع الإدارة المراد حسابه:",
        options=list(DEPARTMENTS.keys()),
        key="dept_type_main_select"
    )
    
    # تحذير: لن يتم عرض الضيافة في الوضع الفردي لعدم وجود إدارات ثابتة
    if department_type_choice == "الضيافة" and not DEPARTMENTS[department_type_choice]:
           st.warning("⚠️ لا توجد إدارات ثابتة لـ 'الضيافة' في هذا الوضع. يرجى استخدام 'وضع الحساب الموحد' لإضافة مراكز ضيافة ديناميكياً.")
           st.session_state['run_calculation_main'] = False
           return

    with st.container(border=True):
        st.markdown(f"**معايير فروع إدارة: {department_type_choice}**")
        st.markdown("---") # فاصل واضح داخل الإدارة الرئيسية
        
        ratios = {}
        time_based_inputs = {}
        bus_ratio_inputs = {}
        coverage_percentages = {}
        criteria_choices = {}

        cols = st.columns(3)
        col_index = 0

        for i, dept in enumerate(DEPARTMENTS[department_type_choice]):
            name = dept['name']
            dept_type = dept['type']
            
            col = cols[col_index % 3]
            col_index += 1

            with col:
                # إضافة مربع حول كل قسم فرعي
                # تم إضافة كلاس CSS مخصص هنا لتغيير اللون
                st.markdown(f"""
                    <style>
                        .darker-container {{
                            background-color: #f0f2f6; /* لون خلفية أغمق قليلاً من الأبيض */
                            padding: 10px;
                            border-radius: 5px;
                            border: 1px solid rgba(49, 51, 63, 0.2);
                            margin-bottom: 10px;
                        }}
                    </style>
                    <div class="darker-container">
                        ***_{name}_***
                    </div>
                """, unsafe_allow_html=True)
                
                default_crit = dept.get('default_criterion', 'Present')
                criterion_options = ['المتواجدين (1)', 'التدفق اليومي (2)']
                
                criterion_choice_text = col.radio(
                    "معيار الاحتساب الرئيسي",
                    options=criterion_options,
                    index=0 if default_crit == 'Present' else 1,
                    key=f"criterion_{department_type_choice}_{name}_{i}",
                )
                
                criteria_choices[name] = 'Present' if criterion_choice_text == criterion_options[0] else 'Flow'

                if dept_type in ['Ratio', 'Time']:
                    default_cov = dept.get('default_coverage', 100)
                    coverage_val = st.number_input(
                        "نسبة تغطية (%)",
                        min_value=0, max_value=100,
                        value=default_cov, step=1,
                        key=f"cov_{department_type_choice}_{name}_{i}"
                    )
                    coverage_percentages[name] = coverage_val / 100

                if dept_type == 'Ratio':
                    ratios[name] = st.number_input("المعيار (وحدة/موظف)", min_value=1, value=dept['default_ratio'], key=f"ratio_{department_type_choice}_{name}_{i}")
                    
                elif dept_type == 'Time':
                    time_based_inputs[name] = st.number_input("المعيار (دقيقة/وحدة)", min_value=0.5, value=dept['default_time'], step=0.1, key=f"time_{department_type_choice}_{name}_{i}")

                elif dept_type == 'Bus_Ratio':
                    bus_inputs = {'Bus_Count': 0, 'Ratio': 0}
                    bus_inputs['Bus_Count'] = st.number_input("عدد الحافلات المتوقعة", min_value=1, value=20, key=f"bus_count_{name}_{i}")
                    bus_inputs['Ratio'] = st.number_input("المعيار (حافلة/موظف)", min_value=1, value=dept['default_ratio'], key=f"bus_ratio_{name}_{i}")
                    bus_ratio_inputs[name] = bus_inputs
    
    st.markdown("---")
    calculate_button = st.button(f"🔄 اضغط هنا لحساب وعرض احتياج {department_type_choice}", type="primary", key="calculate_button_main")

    # ... (بقية منطق الحساب والعرض) ...
    if calculate_button:
        
        st.success("✅ تم الضغط على الزر. جاري بدء الحساب...")

        all_results = []
        total_staff_needed = 0

        num_hajjaj_present = st.session_state["num_hajjaj_present"]
        num_hajjaj_flow = st.session_state["num_hajjaj_flow"]
        service_days = st.session_state["service_days"]
        staff_work_hours_day = st.session_state["staff_hours"]
        reserve_factor_input = st.session_state["reserve_factor_input"]
        reserve_factor = reserve_factor_input / 100
        shifts_count = st.session_state["shifts_count"]
        ratio_supervisor = st.session_state["ratio_supervisor"]
        ratio_assistant_head = st.session_state["ratio_assistant_head"]
        required_assistant_heads_per_shift = st.session_state["required_assistant_heads_main"]

        hajjaj_data = {'Present': num_hajjaj_present, 'Flow': num_hajjaj_flow}

        for dept in DEPARTMENTS[department_type_choice]:
            name = dept['name']
            dept_type = dept['type']
            
            res_basic = 0

            # منطق حساب res_basic (Ratio, Bus_Ratio, Time)
            if dept_type == 'Ratio':
                ratio = ratios[name]
                criterion = criteria_choices[name]
                coverage = coverage_percentages.get(name, 1) # افتراضي 1 إذا لم يتم تعيينه
                num_hajjaj_for_dept = hajjaj_data[criterion]
                actual_hajjaj_in_center = num_hajjaj_for_dept * coverage
                res_basic = calculate_ratio_based_staff(actual_hajjaj_in_center, ratio)
                
            elif dept_type == 'Bus_Ratio':
                num_units = bus_ratio_inputs[name]['Bus_Count']
                bus_ratio = bus_ratio_inputs[name]['Ratio']
                res_basic = calculate_ratio_based_staff(num_units, bus_ratio)
                
            elif dept_type == 'Time':
                time_min = time_based_inputs[name]
                criterion = criteria_choices[name]
                coverage = coverage_percentages.get(name, 1)
                # الافتراضي لمعامل أحداث الحاج في الوضع الفردي هو 2 كما في الثابتة
                multiplier = 2 
                num_hajjaj_for_dept = hajjaj_data[criterion]
                actual_hajjaj_in_center = num_hajjaj_for_dept * coverage
                res_basic = calculate_time_based_staff(actual_hajjaj_in_center * multiplier, time_min, service_days, staff_work_hours_day)
            
            # تطبيق الهيكل الإداري
            staff_breakdown = distribute_staff(
                res_basic,
                ratio_supervisor,
                shifts_count,
                required_assistant_heads=required_assistant_heads_per_shift,
                ratio_assistant_head=ratio_assistant_head
            )
            
            total_staff_in_hierarchy = sum(staff_breakdown.values())
            total_needed_with_reserve = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

            translated_breakdown = {TRANSLATION_MAP.get(k, k): v for k, v in staff_breakdown.items()}
            
            result_entry = {"الإدارة": name, "القسم": department_type_choice}
            result_entry.update(translated_breakdown)
            result_entry["المجموع الإجمالي (بالاحتياط)"] = total_needed_with_reserve

            all_results.append(result_entry)
            total_staff_needed += total_needed_with_reserve
            
        st.success("✅ اكتمل الحساب. جاري عرض النتائج.")
        
        # 4. عرض النتائج
        st.subheader("6. جدول الاحتياج والنتائج")
        
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
                label="📥 تصدير الجدول إلى ملف Excel",
                data=excel_data,
                file_name=f'تخطيط_القوى_العاملة_{department_type_choice}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                type="secondary"
            )
            
        with col_budget_btn:
            st.download_button(
                label="💰 **تصدير ميزانية الرواتب (Excel)**",
                data=to_excel_budget(total_staff_per_role, service_days),
                file_name=f'ميزانية_الرواتب_التقديرية_{department_type_choice}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                type="primary",
                key="download_budget_excel_main"
            )

        st.markdown("---")

        # 7. عرض الإجمالي
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label=f"**المجموع الكلي للقوى العاملة المطلوبة في {department_type_choice} (مع الاحتياط)**",
                value=f"{total_staff_needed} موظف",
            )
        with col2:
            st.info(f"نسبة الاحتياط الإجمالية المطبقة: {st.session_state['reserve_factor_input']}%")
            
    else:
        st.info(f"⬆️ يرجى إدخال أو مراجعة معايير الاحتساب ثم الضغط على زر **'احتساب وعرض احتياج {department_type_choice}'**.")


# -------------------------------------------------------------------
# 6. إعدادات الحالة الابتدائية ومنطق عرض الصفحة
# -------------------------------------------------------------------

def setup_initial_state():
    """تهيئة متغيرات Session State الافتراضية إذا لم تكن موجودة."""
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'all' # نبدأ بوضع التخطيط الموحد
    
    # الإعدادات العامة للمشروع (يمكن تعديلها في القائمة الجانبية)
    if 'num_hajjaj_present' not in st.session_state:
        st.session_state['num_hajjaj_present'] = 20000
    if 'num_hajjaj_flow' not in st.session_state:
        st.session_state['num_hajjaj_flow'] = 5000
    if 'service_days' not in st.session_state:
        st.session_state['service_days'] = 7
    if 'staff_hours' not in st.session_state:
        st.session_state['staff_hours'] = 12
    if 'reserve_factor_input' not in st.session_state:
        st.session_state['reserve_factor_input'] = 20
    if 'shifts_count' not in st.session_state:
        st.session_state['shifts_count'] = 2
    if 'ratio_supervisor' not in st.session_state:
        st.session_state['ratio_supervisor'] = 8
    if 'ratio_assistant_head' not in st.session_state:
        st.session_state['ratio_assistant_head'] = 4
        
    # إعدادات الضيافة الديناميكية
    if 'dynamic_hospitality_centers' not in st.session_state:
        # نبدأ بمركزين افتراضيين
        st.session_state.dynamic_hospitality_centers = [
            {'id': 1, 'name': 'مركز ضيافة رئيسي أ', 'hajjaj_count': 15000, 'active': True},
            {'id': 2, 'name': 'مركز ضيافة فرعي ب', 'hajjaj_count': 5000, 'active': True}
        ]
    if 'next_center_id' not in st.session_state:
        st.session_state.next_center_id = 3 # يبدأ بالرقم التالي للمراكز الافتراضية

    # تهيئة إعدادات الرواتب الافتراضية
    for role, default_salary in DEFAULT_SALARY.items():
        if f'salary_{role}' not in st.session_state:
            st.session_state[f'salary_{role}'] = default_salary

def inject_rtl_css():
    """حقن كود CSS لتعيين اتجاه النص من اليمين لليسار (RTL) وتحسين الشريط الجانبي."""
    st.markdown("""
        <style>
        /* إجبار التطبيق على العرض من اليمين لليسار */
        html {
            direction: rtl;
        }
        
        /* ضبط محاذاة النص الافتراضية للعناصر الرئيسية */
        .stApp {
            text-align: right;
        }
        
        /* تطبيق الاتجاه على محتوى الصفحة الرئيسية بالكامل */
        [data-testid="stAppViewBlockContainer"] {
            direction: rtl;
        }

        /* ------------------ تحسين الشريط الجانبي (Sidebar) ------------------ */
        
        /* محاذاة محتوى الشريط الجانبي لليمين */
        [data-testid="stSidebarContent"] {
            text-align: right;
            direction: rtl; 
        }
        
        /* محاذاة عناوين الشريط الجانبي (Header/Expander) لليمين */
        [data-testid="stSidebarContent"] .st-emotion-cache-1cypcdb h3,
        [data-testid="stSidebarContent"] .st-emotion-cache-1cypcdb h2,
        [data-testid="stSidebarContent"] .st-emotion-cache-1cypcdb h1 {
            text-align: right;
            width: 100%;
        }
        
        /* محاذاة التسميات (Labels) لليمين */
        .st-emotion-cache-10qj61q { /* Selectbox label */
            text-align: right;
        }
        
        /* محاذاة مدخلات الأرقام والنصوص والأزرار داخل الشريط الجانبي */
        [data-testid="stSidebarContent"] .stNumberInput,
        [data-testid="stSidebarContent"] .stTextInput,
        [data-testid="stSidebarContent"] .stButton {
            text-align: right;
        }
        
        /* محاذاة محتوى الـ Expander لليمين داخل الشريط الجانبي */
        [data-testid="stSidebarContent"] [data-testid="stExpander"] .st-emotion-cache-p2x0l5 {
            text-align: right;
        }

        /* ------------------ تحسين المحتوى الداخلي (Widgets) ------------------ */
        
        /* إجبار جميع التسميات (Labels) في التطبيق على محاذاة اليمين */
        label {
            text-align: right !important;
        }
        
        /* محاذاة الراديو (Radio buttons) والتوجل (Toggle) لليمين */
        .stRadio > label, .stCheckbox > label, .stToggle > label {
            text-align: right;
            direction: rtl;
        }
        
        /* عكس ترتيب أيقونة التوجل (Toggle switch) لـ RTL */
        [data-testid="stSidebarContent"] .stToggle label > div > div:nth-child(1) {
            order: 2; /* وضع الأيقونة/المفتاح على اليسار */
        }
        [data-testid="stSidebarContent"] .stToggle label > div > div:nth-child(2) {
            order: 1; /* وضع النص على اليمين */
            margin-left: 10px;
        }
        
        /* محاذاة عناوين الأقسام الفرعية */
        .darker-container {
            text-align: right;
        }
        
        </style>
        """, unsafe_allow_html=True)

def sidebar_config():
    """إعداد القائمة الجانبية لإدخال البيانات العامة."""
    
    # إضافة الشعار في أعلى الشريط الجانبي
    # يجب أن يكون ملف logo.png موجوداً في نفس مجلد ملف app.py
    # يمكن تعديل "size" إلى "small" أو "medium" حسب الحاجة
    st.logo("logo.png", size="large")

    st.sidebar.header("⚙️ الإعدادات العامة للمشروع")
    
    # قسم المدخلات الرئيسية
    with st.sidebar.expander("بيانات الحجاج والخدمة", expanded=True):
        st.number_input("عدد الحجاج المتواجدين (للحجم)", min_value=1, value=st.session_state['num_hajjaj_present'], step=1000, key="num_hajjaj_present")
        st.number_input("التدفق اليومي للحجاج (للحركة)", min_value=1, value=st.session_state['num_hajjaj_flow'], step=500, key="num_hajjaj_flow")
        st.number_input("عدد أيام الخدمة الإجمالية", min_value=1, value=st.session_state['service_days'], step=1, key="service_days")
        st.number_input("ساعات عمل الموظف اليومية", min_value=1, max_value=12, value=st.session_state['staff_hours'], step=1, key="staff_hours")

    # قسم الهيكل الإداري
    with st.sidebar.expander("معايير الهيكل الإداري والاحتياط", expanded=True):
        st.number_input("عدد الورديات اليومية", min_value=1, max_value=3, value=st.session_state['shifts_count'], step=1, key="shifts_count")
        st.number_input("نسبة الاحتياط الإجمالية (%)", min_value=0, max_value=100, value=st.session_state['reserve_factor_input'], step=5, key="reserve_factor_input")
        st.number_input("معيار المشرف/مقدم الخدمة (موظف/مشرف)", min_value=1, value=st.session_state['ratio_supervisor'], step=1, key="ratio_supervisor")
        st.number_input("معيار مساعد الرئيس/مشرف (مشرف/مساعد)", min_value=1, value=st.session_state['ratio_assistant_head'], step=1, key="ratio_assistant_head")

    # قسم الرواتب
    with st.sidebar.expander("متوسطات الرواتب الشهرية (ريال)", expanded=False):
        for role_arabic in DEFAULT_SALARY.keys():
            st.number_input(f"راتب {role_arabic}", min_value=1, value=st.session_state[f'salary_{role_arabic}'], step=500, key=f"salary_{role_arabic}")

    st.sidebar.markdown("---")
    
    # أزرار التبديل بين الصفحات
    st.sidebar.header("🗺️ التنقل بين الصفحات")
    
    if st.session_state['current_page'] == 'main':
        st.sidebar.button("📊 التخطيط الموحد لكل الإدارات", on_click=switch_to_all, type="primary")
        st.sidebar.info("أنت في صفحة الحساب الفردي.")
    else:
        st.sidebar.info("أنت في صفحة التخطيط الموحد.")
        st.sidebar.button("⚙️ الحساب الفردي لإدارة معينة", on_click=switch_to_main, type="secondary")

def main():
    """الدالة الرئيسية لتشغيل التطبيق."""
    # يجب أن تكون st.set_page_config هي أول أمر Streamlit يتم تنفيذه
    st.set_page_config(layout="wide", page_title="تخطيط القوى العاملة", page_icon=":chart_with_upwards_trend:")
    
    # ملاحظة: inject_rtl_css يجب أن يتم استدعاؤها بعد set_page_config
    inject_rtl_css()
    setup_initial_state()
    sidebar_config()

    if st.session_state['current_page'] == 'all':
        all_departments_page()
    elif st.session_state['current_page'] == 'main':
        main_page_logic()

if __name__ == '__main__':
    main()
