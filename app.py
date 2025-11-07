import streamlit as st
import math
import pandas as pd
from io import BytesIO

# -------------------------------------------------------------------
# الدوال والثوابت
# -------------------------------------------------------------------

# ثوابت عامة
TOTAL_WORK_HOURS = 24
SUPERVISORS_PER_SHIFT = 1
ASSISTANT_HEADS_PER_SHIFT = 1
DEFAULT_HEAD_ASSISTANT_RATIO = 4


def calculate_time_based_staff(total_events, time_per_event_min, service_days, staff_work_hours_day):
    time_per_event_hrs = time_per_event_min / 60
    total_hours_needed = total_events * time_per_event_hrs
    total_staff_available_hours = service_days * staff_work_hours_day
    
    basic_staff = math.ceil(total_hours_needed / total_staff_available_hours) if total_staff_available_hours > 0 else 0
    return basic_staff

def calculate_ratio_based_staff(num_units, ratio):
    basic_staff = math.ceil(num_units / ratio)
    return basic_staff

def distribute_staff(total_basic_staff, ratio_supervisor, ratio_assistant_head, shifts):
    service_provider = total_basic_staff
    
    field_supervisor_fixed = SUPERVISORS_PER_SHIFT * shifts
    
    total_hierarchical_supervisors = math.ceil(service_provider / ratio_supervisor)
    
    total_supervisors = max(total_hierarchical_supervisors, field_supervisor_fixed)
    
    assistant_head_fixed = ASSISTANT_HEADS_PER_SHIFT * shifts
    assistant_head = max(assistant_head_fixed, math.ceil(total_supervisors / ratio_assistant_head))
    
    head = 1
    
    return {
        "Head": head,
        "Assistant_Head": assistant_head,
        "Field_Supervisor": field_supervisor_fixed,
        "Service_Provider": service_provider,
    }

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=True, sheet_name='احتياج القوى العاملة')
    processed_data = output.getvalue()
    return processed_data

# تعريف الإدارات
DEPARTMENTS = {
    "الضيافة": [
        {"name": "مركز الضيافة", "type": "Ratio", "default_ratio": 200, "default_coverage": 100, "default_criterion": 'Present'},
    ],
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

# تعريف شامل لجميع فروع الإدارات (لشاشة الحساب الموحد)
ALL_DEPARTMENTS_FLAT = {}
for category, depts in DEPARTMENTS.items():
    for dept in depts:
        ALL_DEPARTMENTS_FLAT[dept['name']] = dept.copy()
        ALL_DEPARTMENTS_FLAT[dept['name']]['category'] = category

# خريطة ترجمة الرتب الوظيفية
TRANSLATION_MAP = {
    "Head": "رئيس",
    "Assistant_Head": "مساعد رئيس",
    "Field_Supervisor": "مشرف ميداني",
    "Service_Provider": "مقدم خدمة",
}

# -------------------------------------------------------------------
# وظائف مساعدة للتبديل بين الصفحات
# -------------------------------------------------------------------

def switch_to_main():
    st.session_state['current_page'] = 'main'

def switch_to_all():
    st.session_state['current_page'] = 'all'

# -------------------------------------------------------------------
# منطق الشاشة الموحدة الجديدة (All Departments Page Logic)
# -------------------------------------------------------------------

def all_departments_page():
    """
    شاشة لعرض وحساب احتياج القوى العاملة لجميع الإدارات في جدول واحد، مع إمكانية تعديل المعايير أولاً.
    """
    st.title("📊 تخطيط القوى العاملة الموحد")
    st.markdown("---")
    
    # 1. منطقة إدخال المعايير لجميع الإدارات
    st.subheader("1. ضبط معايير الاحتساب لجميع الإدارات")
    
    # تعريف قواميس لتخزين مدخلات المستخدم
    # يجب تهيئة هذا القاموس في Session State لحفظ القيم بين إعادة تشغيل التطبيق
    if 'user_settings_all' not in st.session_state:
         st.session_state['user_settings_all'] = {}
         
    user_settings = st.session_state['user_settings_all']
    
    with st.container(border=True):
        st.markdown("**يرجى مراجعة المعايير التالية: (الوحدة: النسبة/الوقت/الحافلات)**")

        # استخدام st.form لجمع جميع المدخلات في خطوة واحدة
        with st.form("all_dept_criteria_form"):
            
            # ترتيب عرض الإدارات حسب الأقسام
            for category_name, depts in DEPARTMENTS.items():
                st.markdown(f"#### 🏷️ {category_name}")
                cols = st.columns(3)
                col_index = 0
                
                for i, dept in enumerate(depts):
                    name = dept['name']
                    dept_type = dept['type']
                    col = cols[col_index % 3]
                    col_index += 1
                    
                    # تهيئة الإعدادات الافتراضية إذا لم يتم تهيئتها بعد
                    if name not in user_settings:
                        # تعريف القيم الافتراضية
                        default_crit = dept.get('default_criterion', 'Present')
                        default_cov = dept.get('default_coverage', 100)
                        
                        user_settings[name] = {
                            'criterion': default_crit,
                            'coverage': default_cov / 100,
                            'ratio': dept.get('default_ratio', 1),
                            'time': dept.get('default_time', 1),
                            'bus_count': 20, # قيمة افتراضية للحافلات
                            'events_multiplier': 2 # قيمة افتراضية لمعامل الأحداث
                        }

                    
                    with col:
                        st.markdown(f"***_{name}_***")
                        
                        # --- معيار الاحتساب (المتواجدين/التدفق) ---
                        criterion_options = ['المتواجدين (حجم)', 'التدفق اليومي (حركة)']
                        
                        criterion_choice_text = st.radio(
                            "المعيار", 
                            options=criterion_options,
                            index=0 if user_settings[name]['criterion'] == 'Present' else 1,
                            key=f"all_crit_{name}_{i}"
                        )
                        # يتم تحديث القيمة في user_settings في خطوة لاحقة (submit)
                        
                        # --- نسبة التغطية (لكل ما يعتمد على عدد الحجاج) ---
                        if dept_type in ['Ratio', 'Time']:
                            coverage_val = st.number_input(
                                "نسبة تغطية (%)", 
                                min_value=0, max_value=100, 
                                value=int(user_settings[name]['coverage'] * 100), 
                                step=1, 
                                key=f"all_cov_{name}_{i}"
                            )

                        # --- إدخال معيار الاحتساب (Ratio/Time/Bus) ---
                        if dept_type == 'Ratio':
                            ratio_val = st.number_input("المعيار (وحدة/موظف)", min_value=1, value=user_settings[name]['ratio'], key=f"all_ratio_{name}_{i}")
                            
                        elif dept_type == 'Time':
                            time_val = st.number_input("المعيار (دقيقة/وحدة)", min_value=0.5, value=user_settings[name]['time'], step=0.1, key=f"all_time_{name}_{i}")
                            multiplier_val = st.number_input("معامل أحداث الحاج (x)", min_value=1, value=user_settings[name]['events_multiplier'], key=f"all_mult_{name}_{i}")
                            
                        elif dept_type == 'Bus_Ratio':
                            bus_count_val = st.number_input("عدد الحافلات المتوقع", min_value=1, value=user_settings[name]['bus_count'], key=f"all_bus_count_{name}_{i}")
                            bus_ratio_val = st.number_input("المعيار (حافلة/موظف)", min_value=1, value=user_settings[name]['ratio'], key=f"all_bus_ratio_{name}_{i}")
            
            st.markdown("---")
            calculate_button = st.form_submit_button("🔄 احتساب وعرض النتائج الموحدة", type="primary")

        # 2. التحديث وتخزين إعدادات المستخدم بعد الضغط على Submit
        if calculate_button:
            # تحديث قاموس user_settings في Session State بناءً على مدخلات الفورم
            for category_name, depts in DEPARTMENTS.items():
                for i, dept in enumerate(depts):
                    name = dept['name']
                    dept_type = dept['type']

                    # تحديث المعيار
                    crit_key = f"all_crit_{name}_{i}"
                    user_settings[name]['criterion'] = 'Present' if st.session_state[crit_key] == criterion_options[0] else 'Flow'

                    # تحديث نسبة التغطية والمعايير الأخرى
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
            st.session_state['run_calculation'] = True # مؤشر لبدء الحساب
            st.rerun() # لإعادة تشغيل الكود وبدء الحساب بالقيم الجديدة
            
    # 3. الحساب والعرض (يتم عند استدعاء rerun)
    if st.session_state.get('run_calculation', False):
        
        st.session_state['run_calculation'] = False # إعادة تعيين المؤشر لمنع الحساب المتكرر
        
        st.success("✅ جاري بدء الحساب الموحد بناءً على معاييرك المخصصة...")
        
        # استخراج المدخلات العامة من Session State مباشرة
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

        # عملية الحساب لجميع الإدارات باستخدام مدخلات المستخدم المخزنة
        for dept_name, dept_info in ALL_DEPARTMENTS_FLAT.items():
            
            dept_type = dept_info['type']
            settings = st.session_state['user_settings_all'][dept_name]
            
            res_basic = 0
            
            # أ. حساب الإدارات المعتمدة على النسبة (Ratio)
            if dept_type == 'Ratio':
                ratio = settings['ratio']
                criterion = settings['criterion']
                coverage = settings['coverage']
                
                num_hajjaj_for_dept = hajjaj_data[criterion]
                actual_hajjaj_in_center = num_hajjaj_for_dept * coverage
                res_basic = calculate_ratio_based_staff(actual_hajjaj_in_center, ratio)
                
            # ب. حساب إرشاد الحافلات (Bus_Ratio)
            elif dept_type == 'Bus_Ratio':
                num_units = settings['bus_count']
                bus_ratio = settings['ratio']
                res_basic = calculate_ratio_based_staff(num_units, bus_ratio)
                
            # ج. حساب الإدارات المعتمدة على الزمن (Time-based)
            elif dept_type == 'Time':
                time_min = settings['time']
                criterion = settings['criterion']
                coverage = settings['coverage']
                multiplier = settings['events_multiplier']
                
                num_hajjaj_for_dept = hajjaj_data[criterion]
                actual_hajjaj_in_center = num_hajjaj_for_dept * coverage
                
                res_basic = calculate_time_based_staff(actual_hajjaj_in_center * multiplier, time_min, service_days, staff_work_hours_day)
            
            # تطبيق الهيكل الإداري
            staff_breakdown = distribute_staff(res_basic, ratio_supervisor, ratio_assistant_head, shifts_count)
            
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
        
        # زر تصدير الإكسل
        excel_data = to_excel(df)
        
        st.download_button(
            label="📥 تصدير الجدول الموحد إلى ملف Excel",
            data=excel_data,
            file_name='تخطيط_القوى_العاملة_الموحد.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            type="secondary"
        )

        st.markdown("---")

        # عرض الإجمالي
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label=f"**المجموع الكلي للقوى العاملة المطلوبة في جميع الأقسام**",
                value=f"{total_staff_needed} موظف",
            )
        with col2:
            st.info(f"نسبة الاحتياط الإجمالية المطبقة: {st.session_state['reserve_factor_input']}%")
    else:
        st.info("⬆️ يرجى إدخال أو مراجعة معايير الاحتساب ثم الضغط على زر **'احتساب وعرض النتائج الموحدة'** في نهاية الصفحة.")

# -------------------------------------------------------------------
# الدالة الرئيسية للشاشة الافتراضية (Main Page Logic) - (لا تغيير كبير)
# -------------------------------------------------------------------
def main_page_logic():
    # العنوان الرئيسي
    st.title(" تخطيط القوى العاملة (حساب فردي) ")
    st.markdown("---")

    # إضافة تنبيه للمستخدمين على الجوال
    st.info("⚠️ **لإدخال معايير الحساب:** يرجى فتح **القائمة الجانبية (☰)** في أعلى اليمين/اليسار أولاً.", icon="ℹ️")

    # -------------------------------------------------------------------
    # القسم الثاني: مدخلات الإدارات (في الجزء العلوي من الصفحة الرئيسية)
    # -------------------------------------------------------------------

    st.subheader("4. تحديد الإدارة ومعايير الاحتساب")
    department_type_choice = st.selectbox(
        "اختر نوع الإدارة المراد حسابه:",
        options=list(DEPARTMENTS.keys()),
        key="dept_type_main_select"
    )

    with st.container(border=True):
        st.markdown(f"**معايير فروع إدارة: {department_type_choice}**")
        
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
                st.markdown(f"***_{name}_***")
                
                default_crit = dept.get('default_criterion', 'Present')
                criterion_label = "معيار الاحتساب الرئيسي"
                criterion_key = f"criterion_{department_type_choice}_{name}_{i}"
                
                criterion_options = ['المتواجدين (1)', 'التدفق اليومي (2)']
                
                criterion_choice_text = col.radio(
                    criterion_label,
                    options=criterion_options,
                    index=0 if default_crit == 'Present' else 1,
                    key=criterion_key,
                )
                
                criteria_choices[name] = 'Present' if criterion_choice_text == criterion_options[0] else 'Flow'

                if dept_type in ['Ratio', 'Time']:
                    default_cov = dept.get('default_coverage', 100)
                    coverage_label = f"نسبة تغطية (%)"
                    coverage_key = f"cov_{department_type_choice}_{name}_{i}"
                    
                    coverage_val = st.number_input(
                        coverage_label,
                        min_value=0,
                        max_value=100,
                        value=default_cov,
                        step=1,
                        key=coverage_key
                    )
                    coverage_percentages[name] = coverage_val / 100

                if dept_type == 'Ratio':
                    label = "المعيار (وحدة/موظف)"
                    key_val = f"ratio_{department_type_choice}_{name}_{i}"
                    ratios[name] = st.number_input(label, min_value=1, value=dept['default_ratio'], key=key_val)
                    
                elif dept_type == 'Time':
                    label = "المعيار (دقيقة/وحدة)"
                    key_val = f"time_{department_type_choice}_{name}_{i}"
                    time_based_inputs[name] = st.number_input(label, min_value=0.5, value=dept['default_time'], step=0.1, key=key_val)

                elif dept_type == 'Bus_Ratio':
                    bus_inputs = {'Bus_Count': 0, 'Ratio': 0}
                    bus_inputs['Bus_Count'] = st.number_input("عدد الحافلات المتوقعة", min_value=1, value=20, key=f"bus_count_{name}_{i}")
                    
                    bus_label = "المعيار (حافلة/موظف)"
                    bus_inputs['Ratio'] = st.number_input(bus_label, min_value=1, value=dept['default_ratio'], key=f"bus_ratio_{name}_{i}")
                    bus_ratio_inputs[name] = bus_inputs
    
    # -------------------------------------------------------------------
    # تنفيذ الحسابات والتوزيع
    # -------------------------------------------------------------------

    st.markdown("---")
    calculate_button = st.button(f"🔄 اضغط هنا لحساب وعرض احتياج {department_type_choice}", type="primary", key="calculate_button_main")

    if calculate_button:
        
        st.success("✅ تم الضغط على الزر. جاري بدء الحساب...")

        all_results = []
        total_staff_needed = 0

        # جلب مدخلات الشريط الجانبي من Session State
        num_hajjaj_present = st.session_state["num_hajjaj_present"]
        num_hajjaj_flow = st.session_state["num_hajjaj_flow"]
        service_days = st.session_state["service_days"]
        staff_work_hours_day = st.session_state["staff_hours"]
        reserve_factor_input = st.session_state["reserve_factor_input"]
        reserve_factor = reserve_factor_input / 100
        shifts_count = st.session_state["shifts_count"]
        ratio_supervisor = st.session_state["ratio_supervisor"]
        ratio_assistant_head = st.session_state["ratio_assistant_head"]


        hajjaj_data = {
            'Present': num_hajjaj_present,
            'Flow': num_hajjaj_flow
        }

        # أ. حساب الإدارات المعتمدة على التغطية (حاج / موظف)
        for dept, ratio in ratios.items():
            criterion = criteria_choices[dept]
            num_hajjaj_for_dept = hajjaj_data[criterion]
            
            actual_hajjaj_in_center = num_hajjaj_for_dept * coverage_percentages[dept]
            
            res_basic = calculate_ratio_based_staff(actual_hajjaj_in_center, ratio)
            staff_breakdown = distribute_staff(res_basic, ratio_supervisor, ratio_assistant_head, shifts_count)
            
            total_staff_in_hierarchy = sum(staff_breakdown.values())
            total_needed_with_reserve = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

            translated_breakdown = {TRANSLATION_MAP.get(k, k): v for k, v in staff_breakdown.items()}
            
            result_entry = {"الإدارة": dept}
            result_entry.update(translated_breakdown)
            result_entry["المجموع الإجمالي (بالاحتياط)"] = total_needed_with_reserve

            all_results.append(result_entry)
            total_staff_needed += total_needed_with_reserve


        # ب. حساب إرشاد الحافلات (معيار خاص)
        for dept, bus_inputs in bus_ratio_inputs.items():
            num_units = bus_inputs['Bus_Count']
            bus_ratio = bus_inputs['Ratio']
            
            res_basic_buses = calculate_ratio_based_staff(num_units, bus_ratio)
            staff_breakdown_buses = distribute_staff(res_basic_buses, ratio_supervisor, ratio_assistant_head, shifts_count)
            
            total_staff_in_hierarchy = sum(staff_breakdown_buses.values())
            total_needed_buses = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

            translated_breakdown = {TRANSLATION_MAP.get(k, k): v for k, v in staff_breakdown_buses.items()}
            
            result_entry = {"الإدارة": dept}
            result_entry.update(translated_breakdown)
            result_entry["المجموع الإجمالي (بالاحتياط)"] = total_needed_buses
            
            all_results.append(result_entry)
            total_staff_needed += total_needed_buses


        # ج. حساب الإدارات المعتمدة على الزمن (Time-based)
        for dept, time_min in time_based_inputs.items():
            criterion = criteria_choices[dept]
            num_hajjaj_for_dept = hajjaj_data[criterion]
            
            actual_hajjaj_in_center = num_hajjaj_for_dept * coverage_percentages[dept]
            
            # الضرب في 2 (يفترض لتغطية الوصول والمغادرة)
            res_basic_time = calculate_time_based_staff(actual_hajjaj_in_center * 2, time_min, service_days, staff_work_hours_day)
            
            staff_breakdown_time = distribute_staff(res_basic_time, ratio_supervisor, ratio_assistant_head, shifts_count)
            
            total_staff_in_hierarchy = sum(staff_breakdown_time.values())
            total_needed_time = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

            translated_breakdown = {TRANSLATION_MAP.get(k, k): v for k, v in staff_breakdown_time.items()}
            
            result_entry = {"الإدارة": dept}
            result_entry.update(translated_breakdown)
            result_entry["المجموع الإجمالي (بالاحتياط)"] = total_needed_time
            
            all_results.append(result_entry)
            total_staff_needed += total_needed_time


        st.info("📊 اكتملت الحسابات. جاري عرض النتائج.")

        # -------------------------------------------------------------------
        # عرض النتائج
        # -------------------------------------------------------------------

        st.subheader(f"نتائج الاحتياج للقوى العاملة والتوزيع الوظيفي لـ {department_type_choice}")
        st.markdown("يتم تطبيق نسبة الاحتياط على **المجموع الإجمالي** لكل إدارة.")

        column_order = [
            "رئيس", "مساعد رئيس", "مشرف ميداني",
            "مقدم خدمة", "المجموع الإجمالي (بالاحتياط)"
        ]
        
        df = pd.DataFrame(all_results)
        df = df.set_index("الإدارة")
        df = df[column_order]

        st.dataframe(df, use_container_width=True)
        
        # زر تصدير الإكسل المخصص
        excel_data = to_excel(df)
        
        st.download_button(
            label="📥 تصدير البيانات إلى ملف Excel",
            data=excel_data,
            file_name=f'تخطيط_القوى_العاملة_{department_type_choice}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            type="secondary"
        )

        st.markdown("---")

        # عرض الإجمالي
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label=f"**المجموع الكلي للقوى العاملة المطلوبة لـ {department_type_choice}**",
                value=f"{total_staff_needed} موظف",
            )
        with col2:
            st.info(f"نسبة الاحتياط الإجمالية المطبقة: {reserve_factor_input}%")
    else:
        st.info(f"يرجى اختيار نوع الإدارة من القائمة المنسدلة في الأعلى وتعديل المعايير ثم النقر على زر الحساب لرؤية النتائج لـ {department_type_choice}.")


# -------------------------------------------------------------------
# الواجهة الرئيسية (Streamlit UI Setup)
# -------------------------------------------------------------------

st.set_page_config(page_title="مخطط القوى العاملة للحج", layout="wide", page_icon=None)

# 📌📌📌 كتلة CSS الموحدة والقوية (لا تغيير) 📌📌📌
st.markdown("""
<style>
/* 1. إجبار كامل الصفحة على RTL */
html, body, [class*="st-emotion-"] {
    direction: rtl;
    text-align: right;
}

/* 2. إزاحة المحتوى الرئيسي لترك مساحة للشريط العودي الثابت (20px) */
[data-testid="stAppViewBlockContainer"] {
    padding-top: 30px !important; 
}

/* 3. إنشاء شريط علوي ثابت: الخط العودي */
.custom-header-line {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 20px; 
    background-color: #800020; 
    z-index: 9999; 
}

/* 4. تثبيت الشريط الجانبي وتحسين RTL على الجوال */
section[data-testid="stSidebar"] {
    text-align: right;
    transform: none !important; 
    left: auto;                  
    right: 0;                    
}

/* 5. تعديل محتوى الشريط الجانبي وإخفاء الكلمات العشوائية أثناء التحميل */
[data-testid="stSidebarContent"] {
    direction: rtl;
    text-align: right;
    visibility: hidden; 
}
[data-testid="stSidebarUserContent"] {
    visibility: visible !important; 
}
</style>
""", unsafe_allow_html=True)

# 📌 حقن عنصر الخط العودي في الصفحة
st.markdown('<div class="custom-header-line"></div>', unsafe_allow_html=True)


# تهيئة حالة الجلسة (Session State) لتتبع الصفحة
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'main'
if 'run_calculation' not in st.session_state:
    st.session_state['run_calculation'] = False


# -------------------------------------------------------------------
# الشريط الجانبي (Sidebar)
# -------------------------------------------------------------------

st.sidebar.image("logo.png", width=200)

st.sidebar.header("1. الإعدادات العامة")

# مدخلات عدد الحجاج الجديدة (ضروري استخدام Key لتخزينها في Session State)
st.sidebar.number_input(
    "1. إجمالي عدد الحجاج (المتواجدين)",
    min_value=1, value=5000, step=100,
    key="num_hajjaj_present"
)
st.sidebar.number_input(
    "2. إجمالي حجاج التدفق اليومي (وصول/مغادرة)",
    min_value=1, value=1000, step=100,
    key="num_hajjaj_flow"
)

st.sidebar.number_input("فترة الخدمة الإجمالية (بالأيام)", min_value=1, value=6, key="service_days")
st.sidebar.number_input("ساعات عمل الموظف اليومية", min_value=1, max_value=16, value=8, key="staff_hours")
st.sidebar.slider("نسبة الاحتياط الإجمالي (%)", min_value=0, max_value=50, value=15, key="reserve_factor_input")


# --- المدخلات الخاصة بالهيكل الإداري (التوزيع الهرمي) ---
st.sidebar.header("3. معايير الهيكل الإداري")
st.sidebar.markdown('**نسب الإشراف (للتوزيع الهرمي)**')

st.sidebar.selectbox(
    "عدد فترات العمل اليومية المطلوبة",
    options=[1, 2, 3],
    index=2,
    key="shifts_count"
)

st.sidebar.number_input("مقدم خدمة / مشرف", min_value=1, value=8, key="ratio_supervisor")
st.sidebar.number_input("مشرف / مساعد رئيس (للهرم)", min_value=1, value=4, key="ratio_assistant_head")

# --- أزرار التبديل بين الشاشات ---
st.sidebar.markdown("---")
st.sidebar.header("اختيار وضع الحساب")

st.sidebar.button("1. وضع الحساب الفردي (الإدارة المختارة)", on_click=switch_to_main, type="secondary", key="go_to_main_page")
st.sidebar.button("2. وضع الحساب الموحد (تخصيص الكل)", on_click=switch_to_all, type="primary", key="go_to_all_page")


# -------------------------------------------------------------------
# منطق عرض الشاشات
# -------------------------------------------------------------------

# استدعاء الدالة الخاصة بالشاشة الحالية
if st.session_state['current_page'] == 'main':
    main_page_logic()
elif st.session_state['current_page'] == 'all':
    all_departments_page()
