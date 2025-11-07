import streamlit as st
import math
import pandas as pd
from io import BytesIO
import os

# -------------------------------------------------------------------
# 1. الثوابت العامة (Constants)
# -------------------------------------------------------------------

TOTAL_WORK_HOURS = 24
SUPERVISORS_PER_SHIFT = 1 # مشرف فترة ثابت 1 لكل وردية
ASSISTANT_HEADS_PER_SHIFT = 1
DEFAULT_HEAD_ASSISTANT_RATIO = 1

DEFAULT_SALARY = {
    "رئيس": 37000,
    "مساعد رئيس": 30000,
    "مشرف فترة": 25000, # تم التعديل
    "مقدم خدمة": 8500,
}

# تعريف الإدارات
DEPARTMENTS = {
    "الضيافة": [], # يتم التعامل معها ديناميكياً
    "الوصول والمغادرة": [
        {"name": "استقبال الهجرة", "type": "Ratio", "default_ratio": 100, "default_coverage": 50, "default_criterion": 'Flow'},
        {"name": "استقبال المطار", "type": "Ratio", "default_ratio": 100, "default_coverage": 50, "default_criterion": 'Flow'},
        {"name": "استقبال القطار", "type": "Ratio", "default_ratio": 100, "default_coverage": 20, "default_criterion": 'Flow'},
        {"name": "إرشاد الحافلات", "type": "Bus_Ratio", "default_ratio": 1, "default_criterion": 'Flow'},
    ],
    "الدعم والمساندة": [
        {"name": "متابعة ميدانية", "type": "Ratio", "default_ratio": 200, "default_coverage": 100, "default_criterion": 'Present'},
        {"name": "الخدمات الميدانية والاسكان ", "type": "Ratio", "default_ratio": 200, "default_coverage": 100, "default_criterion": 'Present'},
        {"name": "الزيارة وإرشاد التأهيين ", "type": "Ratio", "default_ratio": 200, "default_coverage": 100, "default_criterion": 'Present'},
        {"name": " الدعم والضيافة", "type": "Time", "default_time": 5.0, "default_coverage": 100, "default_criterion": 'Present'},
        {"name": "الرعاية صحية", "type": "Ratio", "default_ratio": 1500, "default_coverage": 100, "default_criterion": 'Present'},
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
    "Field_Supervisor": "مشرف فترة", # تم التعديل
    "Service_Provider": "مقدم خدمة",
}

# -------------------------------------------------------------------
# 2. الدوال المساعدة 
# -------------------------------------------------------------------

def calculate_time_based_staff(total_events, time_per_event_min, service_days, staff_work_hours_day):
    time_per_event_hrs = time_per_event_min / 60
    total_hours_needed = total_events * time_per_event_hrs
    total_staff_available_hours = service_days * staff_work_hours_day
    basic_staff = math.ceil(total_hours_needed / total_staff_available_hours) if total_staff_available_hours > 0 else 0
    return basic_staff

def calculate_ratio_based_staff(num_units, ratio):
    basic_staff = math.ceil(num_units / ratio)
    return basic_staff

# تم تعديل الدالة لحذف معايير النسبة وإلغاء التوسع في عدد المشرفين
def distribute_staff(total_basic_staff, shifts, required_assistant_heads=0): 
    service_provider = total_basic_staff
    
    if total_basic_staff == 0:
        head = 0
        total_supervisors = 0
        assistant_head = 0
    else:
        head = 1 # رئيس واحد لكل قسم
        # مشرف فترة ثابت: 1 لكل وردية (SUPERVISORS_PER_SHIFT * shifts)
        total_supervisors = SUPERVISORS_PER_SHIFT * shifts 
        # مساعد رئيس بناءً على الإلزام لكل وردية
        assistant_head = required_assistant_heads * shifts
        
    return {
        "Head": head,
        "Assistant_Head": assistant_head,
        "Field_Supervisor": total_supervisors,
        "Service_Provider": service_provider,
    }

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=True, sheet_name='احتياج القوى العاملة')
    processed_data = output.getvalue()
    return processed_data

# الدالة القديمة لصفحة الاحتساب الفردي (تمت إعادة تسميتها)
def generate_budget_data(total_staff_per_role, service_days):
    budget_data = []
    final_total_project_cost = 0 
    
    for role, staff_count in total_staff_per_role.items():
        # التأكد من استخدام المفتاح الصحيح لاستعادة الراتب/المكافأة
        salary_or_reward = st.session_state.get(f'salary_{role}', DEFAULT_SALARY.get(role, 0))
        total_cost_per_role = staff_count * salary_or_reward
        final_total_project_cost += total_cost_per_role
        
        budget_data.append({
            "الرتبة الوظيفية": role,
            "العدد الإجمالي المطلوب": staff_count,
            "متوسط المكافأة  (ريال)": salary_or_reward, 
            "التكلفة الإجمالية  (ريال)": total_cost_per_role 
        })

    total_project_cost = final_total_project_cost
    
    df_budget = pd.DataFrame(budget_data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_budget.to_excel(writer, index=False, sheet_name='تفاصيل_مكافآت_المشروع') 
        summary_data = {
            "البيان": ["إجمالي تكلفة المكافآت (ريال)", "إجمالي الموظفين (بدون احتياط)"],
            "القيمة": [total_project_cost, sum(total_staff_per_role.values())]
        }
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, startrow=1, startcol=1, index=False, sheet_name='ملخص_الميزانية')
        
    return output.getvalue()

# دالة مساعدة للملائمة مع الاستخدام السابق (الاحتساب الفردي)
def to_excel_budget(total_staff_per_role, service_days):
    return generate_budget_data(total_staff_per_role, service_days)


# **الدالة الجديدة: لإنشاء ملف الميزانية الموحد المفصل مع تنسيق الإطارات**
def generate_unified_detailed_budget_excel(detailed_breakdowns, total_staff_per_role):
    
    ROLES = ["رئيس", "مساعد رئيس", "مشرف فترة", "مقدم خدمة"]
    final_data = []

    # 1. بناء البيانات لكل صف (إدارة فرعية)
    for entry in detailed_breakdowns:
        dept_name = entry['الإدارة']
        category = entry['القسم']
        
        dept_row = {
            "القسم الرئيسي": category,
        }
        
        dept_total_staff = 0
        dept_total_cost = 0
        
        for role in ROLES:
            staff_count = entry.get(role, 0)
            
            # جلب قيمة المكافأة
            try:
                # يجب أن تكون st.session_state متاحة في سياق تشغيل Streamlit
                salary_or_reward = st.session_state.get(f'salary_{role}', DEFAULT_SALARY.get(role, 0))
            except NameError:
                # في حال اختبار الكود خارج سياق Streamlit
                salary_or_reward = DEFAULT_SALARY.get(role, 0)

            total_cost_per_role = staff_count * salary_or_reward
            
            # إضافة الأعمدة الثلاثة لكل رتبة
            dept_row[f"{role} (عدد)"] = staff_count
            dept_row[f"{role} (متوسط مكافأة)"] = salary_or_reward
            dept_row[f"{role} (إجمالي التكلفة)"] = total_cost_per_role # هذا العمود سيحصل على الإطار السميك
            
            dept_total_staff += staff_count
            dept_total_cost += total_cost_per_role
        
        # إضافة إجماليات الإدارة
        dept_row["الإجمالي العددي للإدارة"] = dept_total_staff
        dept_row["الإجمالي النقدي للإدارة (ريال)"] = dept_total_cost
        
        dept_row['الإدارة الفرعية'] = dept_name
        
        final_data.append(dept_row)

    df_budget = pd.DataFrame(final_data)

    # 2. تحديد ترتيب الأعمدة
    final_columns_order = ["القسم الرئيسي"]
    for role in ROLES:
        final_columns_order.extend([
            f"{role} (عدد)", 
            f"{role} (متوسط مكافأة)", 
            f"{role} (إجمالي التكلفة)"
        ])
    final_columns_order.extend(["الإجمالي العددي للإدارة", "الإجمالي النقدي للإدارة (ريال)"])
    
    # اختيار وإعادة ترتيب الأعمدة
    df_budget = df_budget[['الإدارة الفرعية'] + final_columns_order]

    # 3. إنشاء صف الإجمالي العام
    grand_total_row_data = {"الإدارة الفرعية": "الإجمالي العام", "القسم الرئيسي": '-'}
    grand_total_staff_count = sum(total_staff_per_role.values())
    grand_total_cost = 0

    for role in ROLES:
        staff_count = total_staff_per_role.get(role, 0)
        try:
            salary_or_reward = st.session_state.get(f'salary_{role}', DEFAULT_SALARY.get(role, 0))
        except NameError:
            salary_or_reward = DEFAULT_SALARY.get(role, 0)
            
        total_cost_per_role = staff_count * salary_or_reward
        grand_total_cost += total_cost_per_role

        grand_total_row_data[f"{role} (عدد)"] = staff_count
        grand_total_row_data[f"{role} (متوسط مكافأة)"] = '-' # القيمة غير ذات معنى في الإجمالي العام
        grand_total_row_data[f"{role} (إجمالي التكلفة)"] = total_cost_per_role
        
    grand_total_row_data["الإجمالي العددي للإدارة"] = grand_total_staff_count
    grand_total_row_data["الإجمالي النقدي للإدارة (ريال)"] = grand_total_cost
    
    df_budget = pd.concat([df_budget, pd.DataFrame([grand_total_row_data])], ignore_index=True)
    
    # 4. إعداد DataFrame النهائي (تعيين الإدارة الفرعية كـ Index)
    df_budget.set_index("الإدارة الفرعية", inplace=True)
    
    # --- 5. التصدير وتطبيق التنسيق (الإطار السميك) ---
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        sheet_name = 'الميزانية_المفصلة_الموحدة'
        # كتابة البيانات إلى ورقة العمل
        # index=True لإظهار عمود الإدارة الفرعية كعمود أول
        df_budget.to_excel(writer, index=True, sheet_name=sheet_name) 
        
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        # تنسيق الإطار السميك (خط سميك على اليمين)
        thick_right_border = workbook.add_format({'right': 5}) 
        # تنسيق صف الإجمالي العام (خط سميك على اليمين وخط عريض)
        grand_total_format = workbook.add_format({'right': 5, 'bold': True})
        
        # متغيرات حساب الفهرس
        # الإدارة الفرعية (الفهرس) = 0
        # القسم الرئيسي = 1
        # بداية بيانات الرتب الوظيفية = 2
        
        num_data_rows = len(df_budget) 
        last_row = num_data_rows # صف الإجمالي العام
        
        # تطبيق الإطار السميك على عمود "إجمالي التكلفة" لكل رتبة وظيفية
        for i, role in enumerate(ROLES):
            # فهرس العمود الخاص بـ "إجمالي التكلفة" (يقع في نهاية كل مجموعة ثلاثية)
            # فهرس البداية (2) + (تكرار الرتبة * 3) + 2
            border_col_index = 2 + (i * 3) + 2
            
            header_text_key = f"{role} (إجمالي التكلفة)"
            
            # 1. تطبيق التنسيق على صف العنوان (Row 0)
            # تنسيق خاص بالعنوان (خط عريض + إطار)
            header_format = workbook.add_format({'right': 5, 'bold': True, 'align': 'center'}) 
            worksheet.write_string(0, border_col_index, header_text_key, header_format) 
            
            # 2. تطبيق التنسيق على صفوف البيانات (Row 1 to last_row - 1)
            for row_num in range(1, last_row):
                # جلب القيمة من DataFrame
                df_col_index = df_budget.columns.get_loc(header_text_key)
                cell_value = df_budget.iloc[row_num - 1, df_col_index]
                
                # إعادة كتابة القيمة بتنسيق الإطار السميك
                worksheet.write(row_num, border_col_index, cell_value, thick_right_border)

            # 3. تطبيق التنسيق على صف الإجمالي العام (Last Row)
            if last_row > 0:
                df_col_index = df_budget.columns.get_loc(header_text_key)
                cell_value = df_budget.iloc[last_row - 1, df_col_index] # القيمة في آخر صف
                worksheet.write(last_row, border_col_index, cell_value, grand_total_format)
                
        
    return output.getvalue()


def add_hospitality_center(is_default=False):
    """تضيف مركز ضيافة جديد (مع خيار لجعله الافتراضي)."""
    new_id = st.session_state.next_center_id
    default_hajjaj_count = st.session_state.get('num_hajjaj_present', 100000)
    
    name = 'مركز ضيافة 1 (افتراضي)' if is_default else f'مركز ضيافة #{new_id}'
    
    new_center = {
        'id': new_id,
        'name': name,
        'hajjaj_count': default_hajjaj_count,
        'active': True
    }
    st.session_state.dynamic_hospitality_centers.append(new_center)
    st.session_state.next_center_id += 1

def remove_hospitality_center(center_id_to_remove):
    st.session_state.dynamic_hospitality_centers = [
        c for c in st.session_state.dynamic_hospitality_centers
        if c['id'] != center_id_to_remove
    ]
    ratio_key = f"Hosp_Ratio_{center_id_to_remove}"
    if 'user_settings_all' in st.session_state and ratio_key in st.session_state['user_settings_all']:
        del st.session_state['user_settings_all'][ratio_key]


def switch_to_main():
    st.session_state['current_page'] = 'main'
    st.session_state['run_calculation_main'] = False

def switch_to_all():
    st.session_state['current_page'] = 'all'
    st.session_state['run_calculation_all'] = False

# -------------------------------------------------------------------
# 3. منطق الصفحة الفردية (Main Page Logic - تم تحديثه)
# -------------------------------------------------------------------
def main_page_logic():
    st.title("🔢 الاحتساب الفردي للإدارات")
    st.markdown("---")
    
    st.warning("⚠️ يتم في هذه الشاشة اختيار إدارة واحدة فقط لتخصيص معاييرها وحساب احتياجها بشكل فردي.")
    
    # جلب الإعدادات العامة (تم حذف ratio_supervisor و ratio_assistant_head)
    hajjaj_present = st.session_state.get('num_hajjaj_present', 15000)
    hajjaj_flow = st.session_state.get('num_hajjaj_flow', 6000)
    service_days = st.session_state.get('service_days', 8)
    staff_work_hours_day = st.session_state.get('staff_hours', 8)
    reserve_factor = st.session_state.get('reserve_factor_input', 0) / 100
    shifts_count = st.session_state.get('shifts_count', 3)
    
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
        st.session_state['user_settings_main'][selected_department_name] = settings
        st.session_state['run_calculation_main'] = True
        st.rerun()

    if st.session_state.get('run_calculation_main', False) and selected_department_name:
        
        st.session_state['run_calculation_main'] = False
        st.success(f"✅ جاري حساب الاحتياج لـ **{selected_department_name}**...")
        
        hajjaj_data = {'Present': hajjaj_present, 'Flow': hajjaj_flow}
        res_basic = 0
        
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
        
        required_assistant_heads = settings['required_assistant_heads']
        
        # استدعاء دالة التوزيع الجديدة
        staff_breakdown = distribute_staff(
            res_basic,
            shifts_count,
            required_assistant_heads=required_assistant_heads
        )
        
        total_staff_in_hierarchy = sum(staff_breakdown.values())
        total_needed_with_reserve = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

        translated_breakdown = {TRANSLATION_MAP.get(k, k): v for k, v in staff_breakdown.items()}
        
        # **حساب الميزانية للإدارة الفردية**
        total_project_cost_main = 0
        for role, staff_count in translated_breakdown.items():
            salary_or_reward = st.session_state.get(f'salary_{role}', DEFAULT_SALARY.get(role, 0))
            total_project_cost_main += staff_count * salary_or_reward
        
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
        # **عرض الميزانية**
        st.metric(
            label="**قيمة الميزانية التقديرية (ريال)**",
            value=f"{total_project_cost_main:,} ريال"
        )
        
        st.info(f"مقدم الخدمة الأساسي (بدون قيادة): **{res_basic}**")

        budget_data_main = translated_breakdown
        
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
                label="💰 **تصدير ميزانية المكافآت (Excel)**",
                data=to_excel_budget(budget_data_main, service_days),
                file_name=f'ميزانية_المكافآت_{selected_department_name}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                type="primary",
                key="download_budget_excel_main"
            )

# -------------------------------------------------------------------
# 4. منطق الشاشة الموحدة (All Departments Page Logic - تم تحديثه)
# -------------------------------------------------------------------

def all_departments_page():
    st.title(" تخطيط القوى العاملة الموحد")
    st.markdown("---")
    
    
    if 'user_settings_all' not in st.session_state:
            st.session_state['user_settings_all'] = {}
            
    user_settings = st.session_state['user_settings_all']
    
    # --- إدارة المراكز الديناميكية (خارج النموذج للتعامل مع RERUN) ---
    
    # القسم الرئيسي الأول: الضيافة (إدارة المراكز والنسبة)
    with st.container(border=True): # الإطار يحيط بكل قسم الضيافة
        
        st.markdown("####  مراكز الضيافة ")
        
        col_btn, col_info = st.columns([1, 2])
        col_btn.button("➕ إضافة مركز ضيافة جديد", on_click=add_hospitality_center, type="secondary", key="add_hosp_center_btn")
        col_info.info("الإزالة والتبديل يؤديان إلى تحديث الصفحة لحفظ الحالة.")

        if st.session_state.dynamic_hospitality_centers:
            
            # إدارة المراكز (خارج النموذج)
            with st.container(border=False): # حاوية داخلية بدون إطار
                st.markdown("---")
                st.markdown("**إدارة المراكز (الإغلاق/الفتح )**")
                
                centers_to_display = st.session_state.dynamic_hospitality_centers[:]
                
                for i, center in enumerate(centers_to_display):
                    
                    center_id = center['id']
                    
                    with st.expander(f"مركز الضيافة #{center_id}: {center['name']}", expanded=True):
                        
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
                            value=center.get('hajjaj_count', st.session_state.get('num_hajjaj_present', 15000)),
                            step=100,
                            key=f"hosp_hajjaj_{center_id}"
                        )
                        st.session_state.dynamic_hospitality_centers[i]['hajjaj_count'] = new_hajjaj_count
                        
                        # 4. زر الإزالة 
                        col_remove.button(
                            "🗑️ إزالة",
                            on_click=remove_hospitality_center,
                            args=(center_id,),
                            key=f"hosp_remove_{center_id}"
                        )
        else:
            st.info("لا توجد مراكز ضيافة مُضافة بعد.")
    
    st.markdown("---")
    
    # --- نموذج الاحتساب الموحد (لجمع مدخلات النسب والمعايير) ---
    with st.form("all_dept_criteria_form"):
        
        # --- 1. نسبة الضيافة (داخل النموذج) ---
        with st.container(border=True):
            st.markdown("####  معيار نسبة مقدمي الخدمة لمراكز الضيافة")
            
            active_centers = [c for c in st.session_state.dynamic_hospitality_centers[:] if c['active']]
            if not active_centers:
                st.warning("يجب تفعيل مركز ضيافة واحد على الأقل لحساب النسبة.")
                
            for center in active_centers:
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
        
        # --- 2. قسم الوصول والمغادرة ---
        with st.container(border=True): # الإطار الثاني
            st.markdown("#### 🏷️ الوصول والمغادرة")
            st.markdown("---")
            
            depts = DEPARTMENTS["الوصول والمغادرة"]
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
                
                # إطار داخلي خفيف للإدارة الفرعية
                with col.container(border=True):
                    st.markdown(f"***_{name}_***") 
                    
                    asst_head_req_val = st.number_input(
                        "مساعد رئيس إلزامي لكل وردية (0 = لا يوجد)",
                        min_value=0,
                        value=user_settings[name]['required_assistant_heads'],
                        step=1,
                        key=f"all_asst_head_req_{name}_{i}"
                    )
                    
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
        
        # --- 3. قسم الدعم والمساندة ---
        with st.container(border=True): # الإطار الثالث
            st.markdown("#### 🏷️ الدعم والمساندة")
            st.markdown("---")
            
            depts = DEPARTMENTS["الدعم والمساندة"]
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
                
                with col.container(border=True):
                    st.markdown(f"***_{name}_***") 
                    
                    asst_head_req_val = st.number_input(
                        "مساعد رئيس إلزامي لكل وردية (0 = لا يوجد)",
                        min_value=0,
                        value=user_settings[name]['required_assistant_heads'],
                        step=1,
                        key=f"all_asst_head_req_{name}_{i}_support"
                    )
                    
                    criterion_options = ['المتواجدين (حجم)', 'التدفق اليومي (حركة)']
                    criterion_choice_text = st.radio(
                        "المعيار",
                        options=criterion_options,
                        index=0 if user_settings[name]['criterion'] == 'Present' else 1,
                        key=f"all_crit_{name}_{i}_support"
                    )
                    
                    if dept_type in ['Ratio', 'Time']:
                        coverage_val = st.number_input(
                            "نسبة تغطية (%)",
                            min_value=0, max_value=100,
                            value=int(user_settings[name]['coverage'] * 100),
                            step=1,
                            key=f"all_cov_{name}_{i}_support"
                        )

                    if dept_type == 'Ratio':
                        ratio_val = st.number_input("المعيار (وحدة/موظف)", min_value=1, value=user_settings[name]['ratio'], key=f"all_ratio_{name}_{i}_support")
                        
                    elif dept_type == 'Time':
                        time_val = st.number_input("المعيار (دقيقة/وحدة)", min_value=0.5, value=user_settings[name]['time'], step=0.1, key=f"all_time_{name}_{i}_support")
                        multiplier_val = st.number_input("معامل أحداث الحاج (x)", min_value=1, value=user_settings[name]['events_multiplier'], key=f"all_mult_{name}_{i}_support")
                        
                    elif dept_type == 'Bus_Ratio':
                        bus_count_val = st.number_input("عدد الحافلات المتوقع", min_value=1, value=user_settings[name]['bus_count'], key=f"all_bus_count_{name}_{i}_support")
                        bus_ratio_val = st.number_input("المعيار (حافلة/موظف)", min_value=1, value=user_settings[name]['ratio'], key=f"all_bus_ratio_{name}_{i}_support")
                            
        st.markdown("---")
        calculate_button = st.form_submit_button("🔄 احتساب وعرض النتائج الموحدة", type="primary")

    # (منطق الحساب والعرض)
    if calculate_button:
        
        for category_name, depts in DEPARTMENTS.items():
            if category_name == "الضيافة": 
                # تحديث إعدادات الضيافة
                active_centers = [c for c in st.session_state.dynamic_hospitality_centers[:] if c['active']]
                for center in active_centers:
                    center_id = center['id']
                    ratio_key = f"Hosp_Ratio_{center_id}"
                    user_settings[ratio_key] = st.session_state[f"hosp_ratio_{center_id}"]
                continue

            for i, dept in enumerate(depts):
                name = dept['name']
                dept_type = dept['type']
                
                suffix = ""
                if category_name == "الدعم والمساندة":
                    suffix = "_support"

                asst_head_key = f"all_asst_head_req_{name}_{i}{suffix}"
                user_settings[name]['required_assistant_heads'] = st.session_state[asst_head_key]

                criterion_options = ['المتواجدين (حجم)', 'التدفق اليومي (حركة)']
                crit_key = f"all_crit_{name}_{i}{suffix}"
                user_settings[name]['criterion'] = 'Present' if st.session_state[crit_key] == criterion_options[0] else 'Flow'

                if dept_type in ['Ratio', 'Time']:
                    cov_key = f"all_cov_{name}_{i}{suffix}"
                    user_settings[name]['coverage'] = st.session_state[cov_key] / 100
                    
                if dept_type == 'Ratio':
                    ratio_key = f"all_ratio_{name}_{i}{suffix}"
                    user_settings[name]['ratio'] = st.session_state[ratio_key]
                    
                elif dept_type == 'Time':
                    time_key = f"all_time_{name}_{i}{suffix}"
                    mult_key = f"all_mult_{name}_{i}{suffix}"
                    user_settings[name]['time'] = st.session_state[time_key]
                    user_settings[name]['events_multiplier'] = st.session_state[mult_key]
                    
                elif dept_type == 'Bus_Ratio':
                    bus_count_key = f"all_bus_count_{name}_{i}{suffix}"
                    bus_ratio_key = f"all_bus_ratio_{name}_{i}{suffix}"
                    user_settings[name]['bus_count'] = st.session_state[bus_count_key]
                    user_settings[name]['ratio'] = st.session_state[bus_ratio_key]
                    
        st.session_state['user_settings_all'] = user_settings
        st.session_state['run_calculation_all'] = True
        st.rerun()

    if st.session_state.get('run_calculation_all', False):
        
        st.session_state['run_calculation_all'] = False
        
        num_hajjaj_present = st.session_state['num_hajjaj_present']
        num_hajjaj_flow = st.session_state['num_hajjaj_flow']
        service_days = st.session_state['service_days']
        staff_work_hours_day = st.session_state.get('staff_hours', 8)
        reserve_factor = st.session_state['reserve_factor_input'] / 100
        shifts_count = st.session_state.get('shifts_count', 3)
        
        hajjaj_data = {'Present': num_hajjaj_present, 'Flow': num_hajjaj_flow}

        all_results = []
        total_staff_needed = 0
        detailed_staff_breakdowns = [] # قائمة جديدة لتفاصيل الميزانية
        
        # مجموع إجمالي الموظفين لكل دور (لحساب الميزانية المجمعة)
        total_staff_per_role = {
            "رئيس": 0,
            "مساعد رئيس": 0,
            "مشرف فترة": 0,
            "مقدم خدمة": 0,
        }

        # 1. عملية الحساب لمراكز الضيافة الديناميكية
        for center in st.session_state.dynamic_hospitality_centers:
            if center['active']:
                center_id = center['id']
                dept_name = center['name']
                hajjaj_count = center['hajjaj_count']
                ratio = st.session_state['user_settings_all'].get(f"Hosp_Ratio_{center_id}", 200)
                
                num_units_to_serve = hajjaj_count / 8
                res_basic = calculate_ratio_based_staff(num_units_to_serve, ratio)
                res_basic = max(1, res_basic)
                
                # استدعاء دالة التوزيع الجديدة
                staff_breakdown = distribute_staff(
                    res_basic,
                    shifts_count,
                    required_assistant_heads=1,
                )
                
                total_staff_in_hierarchy = sum(staff_breakdown.values())
                total_needed_with_reserve = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

                translated_breakdown = {TRANSLATION_MAP.get(k, k): v for k, v in staff_breakdown.items()}
                
                # تجميع إجمالي الموظفين لكل دور (للميزانية المجمعة)
                for role, count in translated_breakdown.items():
                    total_staff_per_role[role] += count

                # **جمع التفاصيل لملف الإكسيل المفصل للميزانية**
                detailed_staff_breakdowns.append({
                    "القسم": "الضيافة",
                    "الإدارة": dept_name,
                    **translated_breakdown
                })

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
            
            required_assistant_heads = settings['required_assistant_heads']
            
            # استدعاء دالة التوزيع الجديدة
            staff_breakdown = distribute_staff(
                res_basic,
                shifts_count,
                required_assistant_heads=required_assistant_heads,
            )
            
            total_staff_in_hierarchy = sum(staff_breakdown.values())
            total_needed_with_reserve = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

            translated_breakdown = {TRANSLATION_MAP.get(k, k): v for k, v in staff_breakdown.items()}
            
            # تجميع إجمالي الموظفين لكل دور (للميزانية المجمعة)
            for role, count in translated_breakdown.items():
                total_staff_per_role[role] += count

            # **جمع التفاصيل لملف الإكسيل المفصل للميزانية**
            detailed_staff_breakdowns.append({
                "القسم": dept_info['category'],
                "الإدارة": dept_name,
                **translated_breakdown
            })
                
            result_entry = {"الإدارة": dept_name, "القسم": dept_info['category']}
            result_entry.update(translated_breakdown)
            result_entry["المجموع الإجمالي (بالاحتياط)"] = total_needed_with_reserve

            all_results.append(result_entry)
            total_staff_needed += total_needed_with_reserve
            
        st.success("✅ اكتمل الحساب. جاري عرض النتائج.")
        
        # 4. عرض النتائج
        st.subheader("2. جدول الاحتياج الموحد والنتائج")
        
        column_order = [
            "القسم", "رئيس", "مساعد رئيس", "مشرف فترة", # تم التعديل
            "مقدم خدمة", "المجموع الإجمالي (بالاحتياط)"
        ]
        
        df = pd.DataFrame(all_results)
        df = df.set_index("الإدارة")
        df = df[column_order]
        
        st.dataframe(df, use_container_width=True)
        
        # 5. تخزين الإجماليات وحساب الميزانية الإجمالية
        
        # **NEW: Calculate and store the total budget**
        total_project_cost = 0
        for role, staff_count in total_staff_per_role.items():
            # Use the translated role name to fetch the salary
            salary_or_reward = st.session_state.get(f'salary_{role}', DEFAULT_SALARY.get(role, 0))
            total_project_cost += staff_count * salary_or_reward
            
        st.session_state['total_staff_per_role'] = total_staff_per_role
        st.session_state['total_budget_needed'] = total_staff_needed # هذا هو العدد الإجمالي مع الاحتياط
        st.session_state['total_budget_value'] = total_project_cost # هذه هي قيمة الميزانية
        
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
            # استخدام الدالة الجديدة التي تطبق تنسيق الإطارات
            st.download_button(
                label="💰 **تصدير ميزانية المكافآت المفصلة (Excel)**",
                data=generate_unified_detailed_budget_excel(detailed_staff_breakdowns, total_staff_per_role), 
                file_name='ميزانية_المكافآت_المفصلة.xlsx',
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
            # **NEW: Display the budget metric**
            st.metric(
                label="**قيمة الميزانية التقديرية الإجمالية (ريال)**",
                # تنسيق الرقم بفاصلة للآلاف
                value=f"{total_project_cost:,} ريال", 
            )
        with col2:
            st.info(f"نسبة الاحتياط الإجمالية المطبقة: {st.session_state['reserve_factor_input']}%")
            
    else:
        st.info("⬆️ يرجى إدخال أو مراجعة معايير الاحتساب ثم الضغط على زر **'احتساب وعرض النتائج الموحدة'** في نهاية الصفحة.")


# -------------------------------------------------------------------
# 5. الدالة الرئيسية للتطبيق (Main App Function)
# -------------------------------------------------------------------

def app():
    st.set_page_config(
        page_title="تخطيط القوى العاملة",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 🌟 حقن CSS لـ RTL وتخصيص الخلفية والإطارات 🌟
    st.markdown("""
        <style>
        /* 1. جعل اتجاه الصفحة بالكامل من اليمين لليسار */
        html, body, .stApp, .block-container, header, .stSidebar {
            direction: rtl;
            text-align: right;
        }
        
        /* 2. تصحيح محاذاة الشريط الجانبي (SideBar) ليصبح في اليمين */
        .stSidebar > div:first-child {
            right: 0;
            left: auto;
        }

        /* 3. تصحيح اتجاه الأزرار والنصوص داخل الحاويات والأعمدة */
        div[data-testid="stForm"] {
            direction: rtl;
        }
        
        /* تصحيح اتجاه حقول الإدخال والـ radio button */
        label {
            width: 100%;
            text-align: right;
        }
        
        /* تصحيح اتجاه الـ radio buttons */
        div[data-testid="stForm"] > div > div > div > div > div {
            flex-direction: row-reverse; /* لعكس ترتيب الـ radio button */
            justify-content: flex-end; /* لمحاذاة العناصر إلى اليمين */
        }
        
        /* تصحيح اتجاه الـ st.columns */
        div[data-testid="stHorizontalBlock"] {
            flex-direction: row-reverse;
        }

        /* 4. تخصيص الخلفية للحاويات ذات الإطار (تم التعديل ليصبح أغمق قليلاً) */
        .stContainer[data-st-container-border="true"] {
            background-color: #eeeeee; /* رمادي أغمق قليلاً */
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 25px;
            border: 1px solid #ccc; /* إطار أغمق قليلاً */
        }
        
        /* تقليل المسافة العلوية لتقليل الفراغات */
        div.block-container{padding-top: 2.5rem;}
        </style>
    """, unsafe_allow_html=True)
    
    # 6. تهيئة الحالة الافتراضية (Session State)
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'all'
    if 'next_center_id' not in st.session_state:
        st.session_state['next_center_id'] = 1
        
    # إضافة مركز الضيافة الافتراضي
    if 'dynamic_hospitality_centers' not in st.session_state:
        st.session_state['dynamic_hospitality_centers'] = []
    if not st.session_state['dynamic_hospitality_centers']:
        add_hospitality_center(is_default=True)
    
    # (نحتفظ ببقية تهيئة الـ session state كما هي...)
    if 'num_hajjaj_present' not in st.session_state:
        st.session_state['num_hajjaj_present'] = 15000
    if 'num_hajjaj_flow' not in st.session_state:
        st.session_state['num_hajjaj_flow'] = 6000
    if 'service_days' not in st.session_state:
        st.session_state['service_days'] = 8
        
    st.session_state['staff_hours'] = 8
    st.session_state['shifts_count'] = 3
    
    if 'reserve_factor_input' not in st.session_state:
        st.session_state['reserve_factor_input'] = 0
    
    for role, default_salary in DEFAULT_SALARY.items():
        if f'salary_{role}' not in st.session_state:
            st.session_state[f'salary_{role}'] = default_salary

    # 7. مدخلات الشريط الجانبي (العامة)
    with st.sidebar:
        # **إضافة الشعار هنا**
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=250)
        else:
            st.warning("⚠️ لم يتم العثور على ملف 'logo.png' في نفس مجلد التطبيق. يرجى التأكد من مساره.")
        
        st.title(" الإعدادات العامة")
        
        # أزرار التبديل بين الصفحات

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
        st.subheader("البيانات الأساسية")
        
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
        st.subheader("معايير الدوام والهيكل الثابت")
        
        st.info(f"**ساعات عمل الموظف اليومية (ثابتة):** {st.session_state['staff_hours']} ساعات")
        st.info(f"**عدد الورديات اليومية المطلوبة (ثابت):** {st.session_state['shifts_count']} ورديات")
        st.info(f"**مشرف فترة (ثابت):** {SUPERVISORS_PER_SHIFT} لكل وردية")
        
        st.slider(
            "نسبة الاحتياط الإجمالية (%)",
            min_value=0, max_value=50, value=st.session_state['reserve_factor_input'], step=1, key="reserve_factor_input"
        )
        
        st.markdown("---")
        
        st.subheader("متوسط المكافآت") # تم التعديل
        
        for role, default_salary in DEFAULT_SALARY.items():
            key = f'salary_{role}'
            # التأكد من استخدام المسمى الجديد للمشرف في العرض
            display_role = "مشرف فترة" if role == "مشرف فترة" else role
            st.number_input(
                f"مكافأة **{display_role}** (ريال)",
                min_value=1,
                value=st.session_state[key],
                step=100,
                key=key
            )
        
    # 8. عرض الصفحة المختارة
    if st.session_state['current_page'] == 'main':
        main_page_logic()
    elif st.session_state['current_page'] == 'all':
        all_departments_page()

if __name__ == "__main__":
    # تشغيل التطبيق
    app()
