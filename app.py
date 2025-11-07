import streamlit as st
import math
import pandas as pd
from io import BytesIO
import os

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
    default_hajjaj_count = st.session_state.get('num_hajjaj_present', 100000)
    
    new_center = {
        'id': new_id,
        'name': f'مركز ضيافة #{new_id}',
        'hajjaj_count': default_hajjaj_count,
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
    ratio_key = f"Hosp_Ratio_{center_id_to_remove}"
    if 'user_settings_all' in st.session_state and ratio_key in st.session_state['user_settings_all']:
        del st.session_state['user_settings_all'][ratio_key]


# -------------------------------------------------------------------
# 3. وظائف مساعدة للتبديل بين الصفحات
# -------------------------------------------------------------------

def switch_to_main():
    """التبديل إلى صفحة الاحتساب الفردي."""
    st.session_state['current_page'] = 'main'
    st.session_state['run_calculation_main'] = False

def switch_to_all():
    """التبديل إلى صفحة الاحتساب الموحد."""
    st.session_state['current_page'] = 'all'
    st.session_state['run_calculation_all'] = False

# -------------------------------------------------------------------
# 4. منطق الشاشة الرئيسية (الاحتساب الفردي - Main Page Logic)
# -------------------------------------------------------------------

def main_page_logic():
    st.title("🔢 الاحتساب الفردي للإدارات")
    st.markdown("---")
    
    st.warning("⚠️ يتم في هذه الشاشة اختيار إدارة واحدة فقط لتخصيص معاييرها وحساب احتياجها بشكل فردي.")
    
    # جلب الإعدادات العامة
    hajjaj_present = st.session_state.get('num_hajjaj_present', 100000)
    hajjaj_flow = st.session_state.get('num_hajjaj_flow', 50000)
    service_days = st.session_state.get('service_days', 30)
    staff_work_hours_day = st.session_state.get('staff_hours', 8) # استخدام القيمة الثابتة 8
    reserve_factor = st.session_state.get('reserve_factor_input', 15) / 100
    shifts_count = st.session_state.get('shifts_count', 3) # استخدام القيمة الثابتة 3
    ratio_supervisor = st.session_state.get('ratio_supervisor', 20)
    ratio_assistant_head = st.session_state.get('ratio_assistant_head', DEFAULT_HEAD_ASSISTANT_RATIO)
    
    # تحديد القسم والإدارة الفرعية
    department_categories = list(DEPARTMENTS.keys())
    
    selected_category = st.selectbox(
        "اختر القسم الرئيسي",
        options=department_categories,
        key='main_category_select'
    )
    
    department_list = DEPARTMENTS.get(selected_category, [])
    department_names = [d['name'] for d in department_list]
    
    if selected_category == "الضيافة":
        st.error("الضيافة يتم احتسابها فقط ضمن نموذج الاحتساب الموحد نظراً لطبيعتها الديناميكية.")
        return

    if not department_names:
        st.info("لا توجد إدارات فرعية معرفة في هذا القسم بعد.")
        return

    selected_department_name = st.selectbox(
        "اختر الإدارة الفرعية للحساب",
        options=department_names,
        key='main_department_select'
    )

    # جلب الإعدادات الافتراضية
    dept_info = next(d for d in department_list if d['name'] == selected_department_name)
    dept_type = dept_info['type']
    
    # تهيئة إعدادات الحالة الخاصة بالصفحة الفردية
    if 'user_settings_main' not in st.session_state:
        st.session_state['user_settings_main'] = {}

    if selected_department_name not in st.session_state['user_settings_main']:
        st.session_state['user_settings_main'][selected_department_name] = {
            'criterion': dept_info.get('default_criterion', 'Present'),
            'coverage': dept_info.get('default_coverage', 100) / 100,
            'ratio': dept_info.get('default_ratio', 1),
            'time': dept_info.get('default_time', 1),
            'bus_count': 20,
            'events_multiplier': 2,
            'required_assistant_heads': 0
        }
        
    settings = st.session_state['user_settings_main'][selected_department_name]

    st.markdown("---")
    st.subheader(f"⚙️ معايير الاحتساب لـ **{selected_department_name}**")
    
    with st.form("main_criteria_form"):
        col1, col2, col3 = st.columns(3)

        # مساعد رئيس إلزامي
        settings['required_assistant_heads'] = col1.number_input(
            "مساعد رئيس إلزامي لكل وردية (0 = لا يوجد)",
            min_value=0,
            value=settings['required_assistant_heads'],
            step=1,
            key=f"main_asst_head_req_{selected_department_name}"
        )

        # المعيار
        criterion_options = ['المتواجدين (حجم)', 'التدفق اليومي (حركة)']
        default_index = 0 if settings['criterion'] == 'Present' else 1
        criterion_choice_text = col2.radio(
            "المعيار",
            options=criterion_options,
            index=default_index,
            key=f"main_crit_{selected_department_name}"
        )
        settings['criterion'] = 'Present' if criterion_choice_text == criterion_options[0] else 'Flow'
        
        # التغطية
        if dept_type in ['Ratio', 'Time']:
            coverage_percent = int(settings['coverage'] * 100)
            coverage_val = col3.number_input(
                "نسبة تغطية (%)",
                min_value=0, max_value=100,
                value=coverage_percent,
                step=1,
                key=f"main_cov_{selected_department_name}"
            )
            settings['coverage'] = coverage_val / 100
        
        # النسبة أو الوقت أو الحافلات
        if dept_type == 'Ratio':
            settings['ratio'] = st.number_input("المعيار (وحدة/موظف)", min_value=1, value=settings['ratio'], key=f"main_ratio_{selected_department_name}")
            
        elif dept_type == 'Time':
            col_t1, col_t2 = st.columns(2)
            settings['time'] = col_t1.number_input("المعيار (دقيقة/وحدة)", min_value=0.5, value=settings['time'], step=0.1, key=f"main_time_{selected_department_name}")
            settings['events_multiplier'] = col_t2.number_input("معامل أحداث الحاج (x)", min_value=1, value=settings['events_multiplier'], key=f"main_mult_{selected_department_name}")
            
        elif dept_type == 'Bus_Ratio':
            col_b1, col_b2 = st.columns(2)
            settings['bus_count'] = col_b1.number_input("عدد الحافلات المتوقع", min_value=1, value=settings['bus_count'], key=f"main_bus_count_{selected_department_name}")
            settings['ratio'] = col_b2.number_input("المعيار (حافلة/موظف)", min_value=1, value=settings['ratio'], key=f"main_bus_ratio_{selected_department_name}")

        calculate_button = st.form_submit_button("🔄 احتساب وعرض النتائج الفردية", type="primary")

    if calculate_button:
        # تحديث الحالة وتشغيل الحساب
        st.session_state['user_settings_main'][selected_department_name] = settings
        st.session_state['run_calculation_main'] = True
        st.rerun()

    # 5. الحساب والعرض
    if st.session_state.get('run_calculation_main', False) and selected_department_name:
        
        st.session_state['run_calculation_main'] = False
        st.success(f"✅ جاري حساب الاحتياج لـ **{selected_department_name}**...")
        
        hajjaj_data = {'Present': hajjaj_present, 'Flow': hajjaj_flow}
        
        res_basic = 0
        
        # 5.1 منطق حساب res_basic
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
        
        # 5.2 تطبيق الهيكل الإداري
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
        
        # 5.3 عرض النتائج
        st.subheader("2. نتائج الاحتياج الفردي")
        
        results_df = pd.DataFrame([translated_breakdown])
        results_df = results_df.transpose().reset_index()
        results_df.columns = ["الرتبة الوظيفية", "العدد المطلوب"]
        results_df = results_df.set_index("الرتبة الوظيفية")

        st.dataframe(results_df, use_container_width=True)

        st.metric(
            label=f"**المجموع الكلي للإدارة ({selected_department_name}) (مع الاحتياط {int(reserve_factor*100)}%)**",
            value=f"{total_needed_with_reserve} موظف"
        )
        st.info(f"مقدم الخدمة الأساسي (بدون قيادة): **{res_basic}**")

        # تجهيز بيانات الميزانية للتصدير (لإدارة واحدة فقط)
        budget_data_main = {
            TRANSLATION_MAP[k]: v for k, v in staff_breakdown.items()
        }
        
        col_download, col_budget_btn = st.columns(2)
        
        with col_download:
            excel_data = to_excel(results_df)
            st.download_button(
                label="📥 تصدير الجدول الفردي إلى ملف Excel",
                data=excel_data,
                file_name=f'تخطيط_القوى_العاملة_{selected_department_name}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                type="secondary"
            )
        
        with col_budget_btn:
             st.download_button(
                label="💰 **تصدير ميزانية الرواتب (Excel)**",
                data=to_excel_budget(budget_data_main, service_days),
                file_name=f'ميزانية_الرواتب_{selected_department_name}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                type="primary",
                key="download_budget_excel_main"
            )

# -------------------------------------------------------------------
# 5. منطق الشاشة الموحدة (All Departments Page Logic)
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
            if i >= len(st.session_state.dynamic_hospitality_centers):
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
                    value=center.get('hajjaj_count', st.session_state.get('num_hajjaj_present', 100000)),
                    step=100,
                    key=f"hosp_hajjaj_{center_id}"
                )
                st.session_state.dynamic_hospitality_centers[i]['hajjaj_count'] = new_hajjaj_count
                
                # 4. زر الإزالة (خارج النموذج)
                col_remove.button(
                    "🗑️ إزالة",
                    on_on_click=remove_hospitality_center,
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
                    st.markdown(f"""
                        <style>
                            .darker-container {{
                                background-color: #f0f2f6;
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
        staff_work_hours_day = st.session_state.get('staff_hours', 8) # استخدام القيمة الثابتة 8
        reserve_factor = st.session_state['reserve_factor_input'] / 100
        shifts_count = st.session_state.get('shifts_count', 3) # استخدام القيمة الثابتة 3
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
# 6. الدالة الرئيسية للتطبيق (Main App Function)
# -------------------------------------------------------------------

def app():
    st.set_page_config(
        page_title="تخطيط القوى العاملة",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)
    
    # 1. تهيئة الحالة الافتراضية (Session State)
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'all' # ابدأ بالشاشة الموحدة
    if 'next_center_id' not in st.session_state:
        st.session_state['next_center_id'] = 1
    if 'dynamic_hospitality_centers' not in st.session_state:
        st.session_state['dynamic_hospitality_centers'] = []
    
    # تهيئة جميع قيم المدخلات في الشريط الجانبي (التعديل للقيم الثابتة)
    if 'num_hajjaj_present' not in st.session_state:
        st.session_state['num_hajjaj_present'] = 100000
    if 'num_hajjaj_flow' not in st.session_state:
        st.session_state['num_hajjaj_flow'] = 50000
    if 'service_days' not in st.session_state:
        st.session_state['service_days'] = 30
        
    # **تثبيت قيم ساعات العمل والورديات**
    st.session_state['staff_hours'] = 8 # ثابت
    st.session_state['shifts_count'] = 3 # ثابت
    
    if 'reserve_factor_input' not in st.session_state:
        st.session_state['reserve_factor_input'] = 15
    if 'ratio_supervisor' not in st.session_state:
        st.session_state['ratio_supervisor'] = 20
    if 'ratio_assistant_head' not in st.session_state:
        st.session_state['ratio_assistant_head'] = DEFAULT_HEAD_ASSISTANT_RATIO
    
    for role, default_salary in DEFAULT_SALARY.items():
        if f'salary_{role}' not in st.session_state:
            st.session_state[f'salary_{role}'] = default_salary

    # 2. مدخلات الشريط الجانبي (العامة)
    with st.sidebar:
        # **إضافة الشعار هنا**
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=250) # تم ضبط العرض ليتناسب مع الشريط الجانبي
        else:
            st.warning("⚠️ لم يتم العثور على ملف 'logo.png' في نفس مجلد التطبيق. يرجى التأكد من مساره.")
        
        st.title("⚙️ الإعدادات العامة")
        
        # أزرار التبديل بين الصفحات
        st.subheader("نافذة العرض")
        col_main, col_all = st.columns(2)
        
        col_main.button(
            "حساب فردي",
            on_click=switch_to_main,
            disabled=st.session_state['current_page'] == 'main',
            use_container_width=True
        )
        col_all.button(
            "حساب موحد",
            on_click=switch_to_all,
            disabled=st.session_state['current_page'] == 'all',
            type="primary" if st.session_state['current_page'] == 'all' else "secondary",
            use_container_width=True
        )
        
        st.markdown("---")
        st.subheader("بيانات المدخلات الأساسية")
        
        st.number_input(
            "إجمالي الحجاج/الزوار (المتواجدين)",
            min_value=1, value=st.session_state['num_hajjaj_present'], step=1000, key="num_hajjaj_present"
        )
        st.number_input(
            "إجمالي الحجاج/الزوار (التدفق اليومي)",
            min_value=1, value=st.session_state['num_hajjaj_flow'], step=1000, key="num_hajjaj_flow"
        )
        st.number_input(
            "مدة الخدمة (يوم)",
            min_value=1, value=st.session_state['service_days'], step=1, key="service_days"
        )

        st.markdown("---")
        st.subheader("معايير الدوام والهيكل")
        
        # **عرض القيم الثابتة بدلاً من مدخلات**
        st.info(f"**ساعات عمل الموظف اليومية (ثابتة):** {st.session_state['staff_hours']} ساعات")
        st.info(f"**عدد الورديات اليومية المطلوبة (ثابت):** {st.session_state['shifts_count']} ورديات")
        
        st.slider(
            "نسبة الاحتياط الإجمالية (%)",
            min_value=0, max_value=50, value=st.session_state['reserve_factor_input'], step=1, key="reserve_factor_input"
        )
        
        st.markdown("---")
        st.subheader("معايير الهيكل القيادي")
        
        st.number_input(
            "معيار الهيكل القيادي (مقدم خدمة / قيادي إجمالي)",
            min_value=1, value=st.session_state['ratio_supervisor'], step=1, key="ratio_supervisor"
        )
        st.number_input(
            "معيار عدد الرؤساء / مساعدي الرؤساء",
            min_value=1, value=st.session_state['ratio_assistant_head'], step=1, key="ratio_assistant_head"
        )
        
        st.markdown("---")
        
        st.subheader("💰 تعديل الرواتب الشهرية")
        
        for role, default_salary in DEFAULT_SALARY.items():
            key = f'salary_{role}'
            st.number_input(
                f"راتب **{role}** (ريال)",
                min_value=1,
                value=st.session_state[key],
                step=100,
                key=key
            )
        
    # 3. عرض الصفحة المختارة
    if st.session_state['current_page'] == 'main':
        main_page_logic()
    elif st.session_state['current_page'] == 'all':
        all_departments_page()

if __name__ == "__main__":
    app()
