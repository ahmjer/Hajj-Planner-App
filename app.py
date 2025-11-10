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

# تم تحديث: إضافة أدوار (مدير) و (اداري)
DEFAULT_SALARY = {
    "رئيس": 37000,
    "مساعد رئيس": 30000,
    "مشرف فترة": 25000, # تم التعديل
    "مقدم خدمة": 8500,
    "مدير": 20000,       # دور جديد
    "اداري": 12000,      # دور جديد
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
        {"name": "متابعة ميدانية", "type": "Ratio", "default_ratio": 200, "default_coverage": 100, "default_criterion": 'Flow'},
        {"name": "الخدمات الميدانية والاسكان ", "type": "Ratio", "default_ratio": 200, "default_coverage": 100, "default_criterion": 'Present'},
        {"name": "الزيارة وإرشاد التأهيين ", "type": "Ratio", "default_ratio": 200, "default_coverage": 100, "default_criterion": 'Flow'},
        {"name": " الدعم والضيافة", "type": "Time", "default_time": 5.0, "default_coverage": 100, "default_criterion": 'Present'},
        {"name": "الرعاية صحية", "type": "Ratio", "default_ratio": 1500, "default_coverage": 100, "default_criterion": 'Present'},
    ],
    # القسم الجديد - الإدارات المساندة (تم التعديل لتصبح جميعها Manual_HR)
    "الإدارات المساندة": [
        {"name": "الصيانة", "type": "Manual_HR", "default_manager_count": 1, "default_admin_count": 1, "default_criterion": 'Present'},
        {"name": "الدعم الفني", "type": "Manual_HR", "default_manager_count": 1, "default_admin_count": 1, "default_criterion": 'Present'},
        {"name": "الموارد البشرية", "type": "Manual_HR", "default_manager_count": 1, "default_admin_count": 2, "default_criterion": 'Present'}, 
        {"name": "الجودة", "type": "Manual_HR", "default_manager_count": 1, "default_admin_count": 1, "default_criterion": 'Present'},
        {"name": "السكرتارية", "type": "Manual_HR", "default_manager_count": 1, "default_admin_count": 1, "default_criterion": 'Present'},
        {"name": "التواصل المؤسسي", "type": "Manual_HR", "default_manager_count": 1, "default_admin_count": 1, "default_criterion": 'Present'},
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
    "Field_Supervisor": "مشرف فترة",
    "Service_Provider": "مقدم خدمة",
}

# -------------------------------------------------------------------
# 2. الدوال المساعدة 
# -------------------------------------------------------------------

def calculate_time_based_staff(total_events, time_per_event_min, service_days, staff_work_hours_day):
    """تحسب الاحتياج بناءً على الوقت الإجمالي اللازم للخدمات مقارنة بالوقت الإجمالي المتاح من الموظفين."""
    time_per_event_hrs = time_per_event_min / 60
    total_hours_needed = total_events * time_per_event_hrs
    total_staff_available_hours = service_days * staff_work_hours_day
    basic_staff = math.ceil(total_hours_needed / total_staff_available_hours) if total_staff_available_hours > 0 else 0
    return basic_staff

def calculate_ratio_based_staff(num_units, ratio):
    """تحسب الاحتياج بناءً على معيار النسبة (وحدة/موظف)."""
    # math.ceil يضمن تقريب العدد لأعلى موظف صحيح
    basic_staff = math.ceil(num_units / ratio)
    return basic_staff

# تم تعديل الدالة لحذف معايير النسبة وإلغاء التوسع في عدد المشرفين
def distribute_staff(total_basic_staff, shifts, required_assistant_heads=0): 
    """توزع القوى العاملة الأساسية على الهيكل القيادي الثابت."""
    # في حالة Manual_HR، سيتم إرسال total_basic_staff = 0، لذا سيتم حساب القيادات فقط
    service_provider = total_basic_staff
    
    if total_basic_staff == 0 and required_assistant_heads == 0:
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
    """تحويل DataFrame إلى ملف Excel في الذاكرة."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=True, sheet_name='احتياج القوى العاملة')
    processed_data = output.getvalue()
    return processed_data

# **تم تحديث الدالة لإنشاء جدول الميزانية التفصيلي حسب الإدارة**
def generate_detailed_budget_excel(all_results, service_days, is_all_page=True, dept_name_single=None): 
    """توليد بيانات الميزانية الإجمالية (تفاصيل الإدارات) أو الفردية."""
    
    detailed_budget_data = []
    final_total_project_cost = 0 
    
    # قائمة الأدوار المرتبة كما في الثوابت
    roles_order = list(DEFAULT_SALARY.keys())

    if is_all_page:
        # 1. تجهيز بيانات التفاصيل (الإدارة في الصفوف) للصفحة الموحدة
        for entry in all_results:
            dept_name = entry["الإدارة"]
            
            # نستخدم الأدوار المرتبة لضمان الترتيب في Excel
            for role in roles_order:
                # استخدام المفتاح المترجم والتحقق من وجوده
                staff_count = entry.get(role, 0)
                
                if staff_count > 0:
                    salary_or_reward = st.session_state.get(f'salary_{role}', DEFAULT_SALARY.get(role, 0))
                    total_cost_per_role = staff_count * salary_or_reward
                    final_total_project_cost += total_cost_per_role
                    
                    detailed_budget_data.append({
                        "الإدارة": dept_name,
                        "الرتبة الوظيفية": role,
                        "العدد المطلوب": staff_count,
                        "متوسط المكافأة (ريال)": salary_or_reward, 
                        "التكلفة الإجمالية (ريال)": total_cost_per_role 
                    })
        
        df_detailed_budget = pd.DataFrame(detailed_budget_data)
        
        # 2. تجهيز ملخص الإجمالي الكلي
        total_staff_per_role = {}
        for entry in detailed_budget_data:
            role = entry["الرتبة الوظيفية"]
            count = entry["العدد المطلوب"]
            total_staff_per_role[role] = total_staff_per_role.get(role, 0) + count
            
        total_staff_count = sum(total_staff_per_role.values())
        
        # 3. كتابة الملف
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # جدول التفاصيل
            df_detailed_budget.to_excel(
                writer, 
                index=False, 
                sheet_name='تفاصيل_ميزانية_الإدارات',
                columns=["الإدارة", "الرتبة الوظيفية", "العدد المطلوب", "متوسط المكافأة (ريال)", "التكلفة الإجمالية (ريال)"]
            ) 
            
            # جدول الملخص 
            summary_data = {
                "البيان": ["إجمالي تكلفة المكافآت (ريال)", "إجمالي الموظفين في الهيكل القيادي"],
                "القيمة": [final_total_project_cost, total_staff_count]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, startrow=1, startcol=1, index=False, sheet_name='ملخص_الميزانية')
            
        return output.getvalue()
    
    else: # الصفحة الفردية
        # 1. تجهيز بيانات التفاصيل (للإدارة الواحدة)
        for role in roles_order:
            staff_count = all_results.get(role, 0) # all_results is actually the translated_breakdown here
            
            if staff_count > 0:
                salary_or_reward = st.session_state.get(f'salary_{role}', DEFAULT_SALARY.get(role, 0))
                total_cost_per_role = staff_count * salary_or_reward
                final_total_project_cost += total_cost_per_role
                
                detailed_budget_data.append({
                    "الرتبة الوظيفية": role,
                    "العدد المطلوب": staff_count,
                    "متوسط المكافأة (ريال)": salary_or_reward, 
                    "التكلفة الإجمالية (ريال)": total_cost_per_role 
                })
        
        df_budget = pd.DataFrame(detailed_budget_data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_budget.to_excel(
                writer, 
                index=False, 
                sheet_name=f'ميزانية_{dept_name_single}',
                columns=["الرتبة الوظيفية", "العدد المطلوب", "متوسط المكافأة (ريال)", "التكلفة الإجمالية (ريال)"]
            ) 
        return output.getvalue()


# تم تحديث الدالة to_excel_budget لتوجيه البيانات بشكل صحيح
def to_excel_budget(data_for_budget, service_days, is_all_page=True, dept_name_single=None):
    """نقطة دخول لتحويل بيانات الميزانية إلى Excel."""
    return generate_detailed_budget_excel(data_for_budget, service_days, is_all_page, dept_name_single)

def add_hospitality_center(is_default=False):
    """تضيف مركز ضيافة جديد (مع خيار لجعله الافتراضي)."""
    new_id = st.session_state.next_center_id
    # يتم سحب القيمة الافتراضية للحجاج من الإعدادات العامة
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
    """إزالة مركز ضيافة ديناميكي."""
    st.session_state.dynamic_hospitality_centers = [
        c for c in st.session_state.dynamic_hospitality_centers
        if c['id'] != center_id_to_remove
    ]
    ratio_key = f"Hosp_Ratio_{center_id_to_remove}"
    if 'user_settings_all' in st.session_state and ratio_key in st.session_state['user_settings_all']:
        del st.session_state['user_settings_all'][ratio_key]


def switch_to_main():
    """التبديل إلى صفحة الاحتساب الفردي."""
    st.session_state['current_page'] = 'main'
    st.session_state['run_calculation_main'] = False

def switch_to_all():
    """التبديل إلى صفحة الاحتساب الموحد."""
    st.session_state['current_page'] = 'all'
    st.session_state['run_calculation_all'] = False

def switch_to_vehicles():
    """التبديل إلى صفحة احتساب المركبات."""
    st.session_state['current_page'] = 'vehicles'
    st.session_state['run_calculation_vehicles'] = False

def switch_to_landing():
    """التبديل إلى صفحة البداية."""
    st.session_state['current_page'] = 'landing'

# -------------------------------------------------------------------
# 3. واجهة البداية (Landing Page Logic - NEW)
# -------------------------------------------------------------------
def landing_page():
    st.title("🏡 نظام تخطيط القوى العاملة")
    st.markdown("---")

    st.header("اختر نوع الاحتساب:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("🔢 **الاحتساب الفردي للإدارات**")
        st.markdown("يسمح لك هذا الوضع بتخصيص معايير وحساب الاحتياج لـ **إدارة فرعية واحدة** بشكل مستقل.")
        st.button(
            "⬅️ الانتقال إلى الاحتساب الفردي",
            on_click=switch_to_main,
            use_container_width=True,
            type="secondary"
        )

    with col2:
        st.success("📊 **تخطيط القوى العاملة الموحد**")
        st.markdown("يسمح لك هذا الوضع بتخصيص معايير وحساب الاحتياج لـ **جميع الإدارات** دفعة واحدة.")
        st.button(
            "⬅️ الانتقال إلى الاحتساب الموحد",
            on_click=switch_to_all,
            use_container_width=True,
            type="primary"
        )
    
    # NEW: إضافة زر صفحة المركبات
    with col3:
        st.warning("🚘 **احتساب حجم أسطول المركبات**")
        st.markdown("يسمح لك هذا الوضع بحساب عدد المركبات المطلوبة لدعم المواقع الميدانية بناءً على معايير تشغيلية.")
        st.button(
            "⬅️ الانتقال إلى احتساب المركبات",
            on_click=switch_to_vehicles,
            use_container_width=True,
            type="secondary"
        )

    st.markdown("---")
    st.subheader("إعدادات النظام العامة (في الشريط الجانبي)")
    st.info("يمكنك تعديل بيانات الحجاج ومدة الخدمة ومتوسط المكافآت من الشريط الجانبي الأيمن.")


# -------------------------------------------------------------------
# 4. منطق الصفحة الفردية (Main Page Logic) - (لم يتغير)
# -------------------------------------------------------------------
def main_page_logic():
    st.title("🔢 الاحتساب الفردي للإدارات")
    st.markdown("---")
    
    st.warning("⚠️ يتم في هذه الشاشة اختيار إدارة واحدة فقط لتخصيص معاييرها وحساب احتياجها بشكل فردي.")
    
    # جلب الإعدادات العامة
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
            'bus_count': 100,
            'events_multiplier': 2,
            # (التعديل 2): القيمة الافتراضية لمساعد رئيس هي 0 للإدارات المساندة
            'required_assistant_heads': 0 if selected_category == "الإدارات المساندة" else 0,
            'manager_count': dept_info.get('default_manager_count', 1), 
            'admin_count': dept_info.get('default_admin_count', 2), 
        }
        
    settings = st.session_state['user_settings_main'][selected_department_name]

    st.markdown("---")
    st.subheader(f"⚙️ معايير الاحتساب لـ **{selected_department_name}**")
    
    with st.form("main_criteria_form"):
        col1, col2, col3 = st.columns(3)

        # مساعد رئيس إلزامي - (التعديل 2): إخفاء هذا الخيار للإدارات المساندة
        if selected_category != "الإدارات المساندة":
            settings['required_assistant_heads'] = col1.number_input(
                "مساعد رئيس إلزامي لكل وردية (0 = لا يوجد)",
                min_value=0,
                value=settings['required_assistant_heads'],
                step=1,
                key=f"main_asst_head_req_{selected_department_name}"
            )
        else:
            settings['required_assistant_heads'] = 0 # إلزامي أن تكون 0
            col1.info("احتساب مساعد رئيس غير متوفر للإدارات المساندة") # رسالة توضيحية

        # المعيار
        if dept_type != 'Manual_HR': # لا حاجة لمعيار وتغطية لـ Manual_HR
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

        # NEW: إدخال يدوي للموارد البشرية (يتم تطبيقه الآن على كل الإدارات المساندة)
        elif dept_type == 'Manual_HR':
            st.markdown("---")
            st.markdown("**إدخال يدوي للقوى العاملة**")
            col_m1, col_m2 = st.columns(2)
            settings['manager_count'] = col_m1.number_input(
                "عدد **مدير** مطلوب",
                min_value=0, 
                value=settings.get('manager_count', dept_info.get('default_manager_count', 1)),
                step=1,
                key=f"main_manager_count_{selected_department_name}"
            )
            settings['admin_count'] = col_m2.number_input(
                "عدد **اداري** مطلوب",
                min_value=0, 
                value=settings.get('admin_count', dept_info.get('default_admin_count', 2)),
                step=1,
                key=f"main_admin_count_{selected_department_name}"
            )


        calculate_button = st.form_submit_button("🔄 احتساب وعرض النتائج الفردية", type="primary")

    if calculate_button:
        st.session_state['user_settings_main'][selected_department_name] = settings
        st.session_state['run_calculation_main'] = True
        # حذف بيانات التحميل القديمة لتجنب التصدير الخاطئ
        if 'last_main_df' in st.session_state: del st.session_state['last_main_df']
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
        
        # NEW: Manual_HR handling (يتم تطبيقه الآن على الإدارات المساندة)
        elif dept_type == 'Manual_HR':
            # نعتبر res_basic = 0 لاحتساب القيادات فقط
            res_basic = 0

        required_assistant_heads = settings['required_assistant_heads']
        
        # استدعاء دالة التوزيع الجديدة
        staff_breakdown = distribute_staff(
            res_basic,
            shifts_count,
            required_assistant_heads=required_assistant_heads
        )
        
        # إضافة الأدوار اليدوية واستبدال مقدم الخدمة (إذا كان Manual_HR)
        if dept_type == 'Manual_HR':
            staff_breakdown["Service_Provider"] = 0 # إلغاء مقدم الخدمة
            staff_breakdown["مدير"] = settings['manager_count']
            staff_breakdown["اداري"] = settings['admin_count']
        
        # إعادة حساب المجموع الكلي بعد إضافة الأدوار اليدوية
        total_staff_in_hierarchy = sum(staff_breakdown.values())
        total_needed_with_reserve = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

        translated_breakdown = {TRANSLATION_MAP.get(k, k): v for k, v in staff_breakdown.items()}
        
        # ضمان وجود الأدوار الجديدة في النتائج المترجمة
        if dept_type == 'Manual_HR':
            translated_breakdown['مدير'] = staff_breakdown['مدير']
            translated_breakdown['اداري'] = staff_breakdown['اداري']
            if 'مقدم خدمة' in translated_breakdown:
                del translated_breakdown['مقدم خدمة']
        
        # **حساب الميزانية للإدارة الفردية**
        total_project_cost_main = 0
        for role, staff_count in translated_breakdown.items():
            salary_or_reward = st.session_state.get(f'salary_{role}', DEFAULT_SALARY.get(role, 0))
            total_project_cost_main += staff_count * salary_or_reward
        
        st.subheader("2. نتائج الاحتياج الفردي")
        
        # Ensure the roles are ordered and displayed correctly
        roles_order = [r for r in DEFAULT_SALARY.keys() if r in translated_breakdown]
        
        results_df = pd.DataFrame([translated_breakdown])
        results_df = results_df.transpose().reset_index()
        results_df.columns = ["الرتبة الوظيفية", "العدد المطلوب"]
        results_df = results_df.set_index("الرتبة الوظيفية")
        
        # إعادة ترتيب الصفوف وفقاً للـ roles_order
        try:
            results_df = results_df.reindex(roles_order).dropna(how='all')
        except:
            # في حال وجود أدوار غير قياسية، يتم ترك الترتيب الافتراضي
            pass
        
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

        # **تخزين البيانات في session_state لتجنب إعادة الاحتساب عند التحميل**
        st.session_state['last_main_df'] = results_df.copy()
        st.session_state['last_main_budget_data'] = translated_breakdown
        st.session_state['last_main_dept_name'] = selected_department_name

    # **منطق التحميل - يستخدم البيانات المخزنة**
    if 'last_main_df' in st.session_state and 'last_main_budget_data' in st.session_state:
        
        def download_main_manpower():
            # دالة مساعدة للحصول على بيانات القوى العاملة
            df_to_excel = st.session_state['last_main_df'].copy()
            df_to_excel.columns.name = "الإدارة"
            return to_excel(df_to_excel)
            
        def download_main_budget():
            # دالة مساعدة للحصول على بيانات الميزانية
            return to_excel_budget(
                st.session_state['last_main_budget_data'], 
                service_days, 
                is_all_page=False, 
                dept_name_single=st.session_state['last_main_dept_name']
            )

        col_download1, col_download2 = st.columns(2)
        
        col_download1.download_button(
            label="⬇️ تحميل جدول الاحتياج (Excel)",
            data=download_main_manpower(), # Call the helper function
            file_name=f"احتياج_القوى_العاملة_فردي_{st.session_state['last_main_dept_name']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        col_download2.download_button(
            label="⬇️ تحميل تفاصيل الميزانية (Excel)",
            data=download_main_budget(), # Call the helper function
            file_name=f"ميزانية_فردي_{st.session_state['last_main_dept_name']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )


# -------------------------------------------------------------------
# 5. منطق الصفحة الموحدة (All Page Logic) - (لم يتغير)
# -------------------------------------------------------------------
def all_page_logic():
    st.title("📊 تخطيط القوى العاملة الموحد")
    st.markdown("---")
    
    # جلب الإعدادات العامة
    hajjaj_present = st.session_state.get('num_hajjaj_present', 15000)
    hajjaj_flow = st.session_state.get('num_hajjaj_flow', 6000)
    service_days = st.session_state.get('service_days', 8)
    staff_work_hours_day = st.session_state.get('staff_hours', 8)
    reserve_factor = st.session_state.get('reserve_factor_input', 0) / 100
    shifts_count = st.session_state.get('shifts_count', 3)
    
    hajjaj_data = {'Present': hajjaj_present, 'Flow': hajjaj_flow}
    
    if 'user_settings_all' not in st.session_state:
        st.session_state['user_settings_all'] = {}
        # تهيئة الإعدادات الافتراضية لجميع الأقسام
        for dept_name, dept_info in ALL_DEPARTMENTS_FLAT.items():
             if dept_info['category'] != "الضيافة":
                # (التعديل 2): إلزامي أن يكون مساعد الرئيس 0 للإدارات المساندة عند التهيئة
                required_assistant_heads = 0 if dept_info['category'] == "الإدارات المساندة" else 0
                
                st.session_state['user_settings_all'][dept_name] = {
                    'criterion': dept_info.get('default_criterion', 'Present'),
                    'coverage': dept_info.get('default_coverage', 100) / 100,
                    'ratio': dept_info.get('default_ratio', 1),
                    'time': dept_info.get('default_time', 1),
                    'bus_count': 100,
                    'events_multiplier': 2,
                    'required_assistant_heads': required_assistant_heads,
                    'manager_count': dept_info.get('default_manager_count', 1), 
                    'admin_count': dept_info.get('default_admin_count', 2), 
                }
    
    user_settings = st.session_state['user_settings_all']
    
    st.subheader("إعداد مراكز الضيافة")
    
    # --- إدارة مراكز الضيافة ---
    col_h1, col_h2 = st.columns([0.8, 0.2])
    col_h2.button("➕ إضافة مركز ضيافة", on_click=add_hospitality_center, use_container_width=True)
    
    active_centers = [c for c in st.session_state.dynamic_hospitality_centers[:] if c['active']]
    
    if active_centers:
        for center in active_centers:
            center_id = center['id']
            center_name_key = f"hosp_name_{center_id}"
            
            with st.container(border=True):
                col_name, col_count, col_remove = st.columns([0.4, 0.4, 0.2])
                
                # إدخال اسم المركز
                new_name = col_name.text_input(
                    "اسم مركز الضيافة",
                    value=center['name'],
                    key=center_name_key
                )
                center['name'] = new_name
                
                # إدخال عدد الحجاج الكلي للمركز
                new_count = col_count.number_input(
                    "عدد الحجاج الكلي (للمركز)",
                    min_value=1,
                    value=center['hajjaj_count'],
                    step=1000,
                    key=f"hosp_count_{center_id}"
                )
                center['hajjaj_count'] = new_count
                
                col_remove.markdown("<br>", unsafe_allow_html=True) # تباعد
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
            st.markdown("#### معيار نسبة مقدمي الخدمة لمراكز الضيافة ")
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
                        'bus_count': 100,
                        'events_multiplier': 2,
                        'required_assistant_heads': 0
                    }
                
                with col.container(border=True):
                    st.markdown(f"***_{name}_***")

                    # مساعد رئيس إلزامي
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
                        events_mult_val = st.number_input("معامل أحداث الحاج (x)", min_value=1, value=user_settings[name]['events_multiplier'], key=f"all_mult_{name}_{i}")
                    elif dept_type == 'Bus_Ratio':
                        bus_count_val = st.number_input("عدد الحافلات المتوقع", min_value=1, value=user_settings[name]['bus_count'], key=f"all_bus_count_{name}_{i}")
                        bus_ratio_val = st.number_input("المعيار (حافلة/موظف)", min_value=1, value=user_settings[name]['ratio'], key=f"all_bus_ratio_{name}_{i}")
                        
                    # تحديث الإعدادات
                    user_settings[name]['required_assistant_heads'] = asst_head_req_val
                    user_settings[name]['criterion'] = 'Present' if criterion_choice_text == criterion_options[0] else 'Flow'
                    if dept_type in ['Ratio', 'Time']:
                        user_settings[name]['coverage'] = coverage_val / 100
                    if dept_type == 'Ratio':
                        user_settings[name]['ratio'] = ratio_val
                    elif dept_type == 'Time':
                        user_settings[name]['time'] = time_val
                        user_settings[name]['events_multiplier'] = events_mult_val
                    elif dept_type == 'Bus_Ratio':
                        user_settings[name]['bus_count'] = bus_count_val
                        user_settings[name]['ratio'] = bus_ratio_val


        # --- 3. قسم الدعم والمساندة ---
        with st.container(border=True):
            st.markdown("#### 🛠️ الدعم والمساندة")
            st.markdown("---")
            depts = DEPARTMENTS["الدعم والمساندة"]
            cols = st.columns(3)
            col_index = 0
            suffix_support = "_support"
            
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
                        'bus_count': 100,
                        'events_multiplier': 2,
                        'required_assistant_heads': 0
                    }
                
                with col.container(border=True):
                    st.markdown(f"***_{name}_***")

                    # مساعد رئيس إلزامي
                    asst_head_req_val = st.number_input(
                        "مساعد رئيس إلزامي لكل وردية (0 = لا يوجد)",
                        min_value=0,
                        value=user_settings[name]['required_assistant_heads'],
                        step=1,
                        key=f"all_asst_head_req_{name}_{i}{suffix_support}"
                    )
                    
                    criterion_options = ['المتواجدين (حجم)', 'التدفق اليومي (حركة)']
                    criterion_choice_text = st.radio(
                        "المعيار",
                        options=criterion_options,
                        index=0 if user_settings[name]['criterion'] == 'Present' else 1,
                        key=f"all_crit_{name}_{i}{suffix_support}"
                    )
                    
                    if dept_type in ['Ratio', 'Time']:
                        coverage_val = st.number_input(
                            "نسبة تغطية (%)",
                            min_value=0, max_value=100,
                            value=int(user_settings[name]['coverage'] * 100),
                            step=1,
                            key=f"all_cov_{name}_{i}{suffix_support}"
                        )
                    
                    if dept_type == 'Ratio':
                        ratio_val = st.number_input("المعيار (وحدة/موظف)", min_value=1, value=user_settings[name]['ratio'], key=f"all_ratio_{name}_{i}{suffix_support}")
                    elif dept_type == 'Time':
                        time_val = st.number_input("المعيار (دقيقة/وحدة)", min_value=0.5, value=user_settings[name]['time'], step=0.1, key=f"all_time_{name}_{i}{suffix_support}")
                        events_mult_val = st.number_input("معامل أحداث الحاج (x)", min_value=1, value=user_settings[name]['events_multiplier'], key=f"all_mult_{name}_{i}{suffix_support}")
                        
                    # تحديث الإعدادات
                    user_settings[name]['required_assistant_heads'] = asst_head_req_val
                    user_settings[name]['criterion'] = 'Present' if criterion_choice_text == criterion_options[0] else 'Flow'
                    if dept_type in ['Ratio', 'Time']:
                        user_settings[name]['coverage'] = coverage_val / 100
                    if dept_type == 'Ratio':
                        user_settings[name]['ratio'] = ratio_val
                    elif dept_type == 'Time':
                        user_settings[name]['time'] = time_val
                        user_settings[name]['events_multiplier'] = events_mult_val


        # --- 4. قسم الإدارات المساندة (Auxiliary) ---
        with st.container(border=True):
            st.markdown("#### 📊 الإدارات المساندة")
            st.markdown("---")
            depts = DEPARTMENTS["الإدارات المساندة"]
            cols = st.columns(3)
            col_index = 0
            suffix_aux = "_aux"
            
            for i, dept in enumerate(depts):
                name = dept['name']
                dept_type = dept['type'] # الآن جميعها Manual_HR
                col = cols[col_index % 3]
                col_index += 1
                
                # تهيئة الإعدادات الافتراضية (بما فيها Manual_HR)
                if name not in user_settings:
                    # هذه التهيئة أصبحت الآن لـ Manual_HR فقط
                    user_settings[name] = {
                        'required_assistant_heads': 0, 
                        'manager_count': dept.get('default_manager_count', 1), 
                        'admin_count': dept.get('default_admin_count', 2), 
                        # إضافة قيم وهمية لتجنب أخطاء المفاتيح غير المستخدمة
                        'criterion': 'Present', 'coverage': 1, 'ratio': 1, 'time': 1, 'bus_count': 100, 'events_multiplier': 2
                    }
                
                with col.container(border=True):
                    st.markdown(f"***_{name}_***")

                    # (التعديل 2): إلغاء احتساب مساعد رئيس وضبط القيمة على 0
                    user_settings[name]['required_assistant_heads'] = 0 
                    
                    # (التعديل 1): تطبيق الإدخال اليدوي
                    if dept_type == 'Manual_HR':
                        st.markdown("**إدخال يدوي للقوى العاملة**")
                        col_m1_hr, col_m2_hr = st.columns(2)
                        manager_count_val = col_m1_hr.number_input(
                            "عدد **مدير** مطلوب",
                            min_value=0, 
                            value=user_settings[name].get('manager_count', dept.get('default_manager_count', 1)),
                            step=1,
                            key=f"all_manager_count_{name}_{i}{suffix_aux}"
                        )
                        admin_count_val = col_m2_hr.number_input(
                            "عدد **اداري** مطلوب",
                            min_value=0, 
                            value=user_settings[name].get('admin_count', dept.get('default_admin_count', 2)),
                            step=1,
                            key=f"all_admin_count_{name}_{i}{suffix_aux}"
                        )
                        # تحديث إعدادات Manual_HR
                        user_settings[name]['manager_count'] = manager_count_val
                        user_settings[name]['admin_count'] = admin_count_val


        calculate_button = st.form_submit_button("🔄 احتساب وعرض النتائج الموحدة", type="primary")

    
    # (منطق الحساب والعرض)
    if calculate_button or st.session_state.get('run_calculation_all', False):
        
        st.session_state['run_calculation_all'] = False
        st.success("✅ جاري حساب الاحتياج الموحد...")
        
        all_results = []
        total_staff_needed = 0 # الإجمالي مع الاحتياط
        # تهيئة إجمالي الموظفين لكل دور بناءً على الأدوار في DEFAULT_SALARY
        total_staff_per_role = {role: 0 for role in DEFAULT_SALARY.keys()} 
        
        # 1. عملية الحساب لمراكز الضيافة الديناميكية
        active_centers = [c for c in st.session_state.dynamic_hospitality_centers[:] if c['active']]
        for center in active_centers:
            center_id = center['id']
            dept_name = center['name']
            
            # جلب النسبة من الإعدادات المحفوظة
            ratio_key = f"Hosp_Ratio_{center_id}"
            ratio = st.session_state['user_settings_all'].get(ratio_key, 200)
            num_units_to_serve = center['hajjaj_count'] # عدد الحجاج الكلي

            # تطبيق المعادلة الجديدة للضيافة (المتوسط اليومي)
            daily_average_hajjaj = num_units_to_serve / service_days
            res_basic = calculate_ratio_based_staff(daily_average_hajjaj, ratio)
            
            res_basic = max(1, res_basic) # التأكد من أن العدد لا يقل عن 1 إذا كان العدد الكلي للحجاج > 0
            
            # استدعاء دالة التوزيع الجديدة (مساعد رئيس ثابت 1 لكل وردية للضيافة)
            staff_breakdown = distribute_staff(
                res_basic,
                shifts_count,
                required_assistant_heads=1,
            )
            
            total_staff_in_hierarchy = sum(staff_breakdown.values())
            total_needed_with_reserve = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

            translated_breakdown = {TRANSLATION_MAP.get(k, k): v for k, v in staff_breakdown.items()}

            # تجميع إجمالي الموظفين لكل دور (للميزانية)
            for role, count in translated_breakdown.items():
                if role in total_staff_per_role:
                    total_staff_per_role[role] += count

            result_entry = {"الإدارة": dept_name, "القسم": "الضيافة"}
            result_entry.update(translated_breakdown)
            result_entry["المجموع الإجمالي (بالاحتياط)"] = total_needed_with_reserve
            all_results.append(result_entry)
            total_staff_needed += total_needed_with_reserve


        # 2. عملية الحساب لباقي الإدارات
        for category_name, depts in DEPARTMENTS.items():
            if category_name == "الضيافة": continue
            
            for dept in depts:
                dept_name = dept['name']
                dept_info = ALL_DEPARTMENTS_FLAT[dept_name]
                settings = st.session_state['user_settings_all'][dept_name]
                
                dept_type = dept_info['type']
                res_basic = 0
                
                # حساب مقدم الخدمة الأساسي
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
                
                # Manual_HR (يتم تطبيقه الآن على الإدارات المساندة)
                elif dept_type == 'Manual_HR':
                    res_basic = 0 # لا يتم حساب مقدم خدمة هنا

                required_assistant_heads = settings['required_assistant_heads']
                
                # توزيع الأدوار
                staff_breakdown = distribute_staff(
                    res_basic,
                    shifts_count,
                    required_assistant_heads=required_assistant_heads
                )
                
                # إضافة الأدوار اليدوية واستبدال مقدم الخدمة (إذا كان Manual_HR)
                if dept_type == 'Manual_HR':
                    staff_breakdown["Service_Provider"] = 0 # إلغاء مقدم الخدمة
                    staff_breakdown["مدير"] = settings['manager_count']
                    staff_breakdown["اداري"] = settings['admin_count']
                
                total_staff_in_hierarchy = sum(staff_breakdown.values())
                total_needed_with_reserve = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

                translated_breakdown = {TRANSLATION_MAP.get(k, k): v for k, v in staff_breakdown.items()}
                
                # ضمان وجود الأدوار الجديدة في النتائج المترجمة
                if dept_type == 'Manual_HR':
                    translated_breakdown['مدير'] = staff_breakdown['مدير']
                    translated_breakdown['اداري'] = staff_breakdown['اداري']
                    if 'مقدم خدمة' in translated_breakdown:
                        del translated_breakdown['مقدم خدمة']

                # تجميع إجمالي الموظفين لكل دور (للميزانية)
                for role, count in translated_breakdown.items():
                    if role in total_staff_per_role:
                        total_staff_per_role[role] += count

                result_entry = {"الإدارة": dept_name, "القسم": dept_info['category']}
                result_entry.update(translated_breakdown)
                result_entry["المجموع الإجمالي (بالاحتياط)"] = total_needed_with_reserve
                all_results.append(result_entry)
                total_staff_needed += total_needed_with_reserve
                
        
        st.subheader("نتائج الاحتياج الموحد لجميع الإدارات")

        # 4. عرض النتائج في جدول
        column_order = [ 
            "القسم", "رئيس", "مساعد رئيس", "مشرف فترة", 
            "مدير", "اداري", "مقدم خدمة", "المجموع الإجمالي (بالاحتياط)" 
        ]
        
        df = pd.DataFrame(all_results)
        df = df.set_index("الإدارة")
        
        # اختيار الأعمدة مع حذف الأعمدة غير الموجودة (مثل مقدم خدمة لـ HR)
        df = df[[col for col in column_order if col in df.columns]] 
        
        st.dataframe(df, use_container_width=True)
        
        # 5. تخزين الإجماليات وحساب الميزانية الإجمالية
        total_project_cost = 0
        # نستخدم total_staff_per_role الذي تم تجميعه بالفعل (بدون احتياط)
        for role, staff_count in total_staff_per_role.items():
            salary_or_reward = st.session_state.get(f'salary_{role}', DEFAULT_SALARY.get(role, 0))
            total_project_cost += staff_count * salary_or_reward
            
        # **تخزين البيانات في session_state لتجنب إعادة الاحتساب عند التحميل**
        st.session_state['last_all_manpower_df'] = df.copy() # جدول القوى العاملة
        st.session_state['last_all_results_data'] = all_results # قائمة النتائج التفصيلية للميزانية
        st.session_state['total_budget_needed'] = total_staff_needed # الإجمالي مع الاحتياط
        st.session_state['total_budget_value'] = total_project_cost # قيمة الميزانية الكلية (تكلفة هيكل القوى العاملة الأساسي)

        st.markdown("---")
        st.subheader("الإجماليات الكلية")
        
        col_total1, col_total2 = st.columns(2)
        col_total1.metric(
            label=f"**إجمالي الموظفين المطلوب (مع الاحتياط {int(reserve_factor*100)}%)**",
            value=f"{total_staff_needed} موظف"
        )
        col_total2.metric(
            label="**قيمة الميزانية الإجمالية التقديرية (ريال)**",
            value=f"{total_project_cost:,} ريال"
        )
        
        st.markdown("---")
        
    # **منطق التحميل - يستخدم البيانات المخزنة**
    if 'last_all_manpower_df' in st.session_state and 'last_all_results_data' in st.session_state:
        
        def download_all_manpower():
            # دالة مساعدة للحصول على بيانات القوى العاملة
            df_to_excel = st.session_state['last_all_manpower_df'].reset_index().rename(columns={"الإدارة": "الإدارة"})
            return to_excel(df_to_excel)
            
        def download_all_budget():
            # دالة مساعدة للحصول على بيانات الميزانية التفصيلية
            return to_excel_budget(st.session_state['last_all_results_data'], service_days, is_all_page=True)


        col_download1, col_download2 = st.columns(2)

        col_download1.download_button(
            label="⬇️ تحميل جدول الاحتياج الموحد (Excel)",
            data=download_all_manpower(), # Call helper
            file_name=f"احتياج_القوى_العاملة_الموحد.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        col_download2.download_button(
            label="⬇️ تحميل تفاصيل الميزانية الكلية (Excel)",
            data=download_all_budget(), # Call helper
            file_name=f"ميزانية_المشروع_الكلية.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# -------------------------------------------------------------------
# 6. منطق صفحة احتساب المركبات (NEW VEHICLE PAGE LOGIC)
# -------------------------------------------------------------------
def vehicle_page_logic():
    st.title("🚘 احتساب حجم أسطول المركبات")
    st.markdown("---")
    
    st.info("ℹ️ يتم احتساب العدد المطلوب من المركبات (السيارات) بناءً على معايير العمليات الميدانية اليومية.")
    
    # تهيئة إعدادات الحالة الخاصة بالمركبات
    if 'vehicle_settings' not in st.session_state:
        st.session_state['vehicle_settings'] = {
            'num_sites': 20,
            'visits_per_site_day': 2,
            'service_time_hr': 0.5,
            'travel_time_hr': 0.5,
            'vehicle_shift_hr': 8,
            'reserve_factor_vehicles': 15, # 15%
        }
    
    settings = st.session_state['vehicle_settings']

    with st.form("vehicle_criteria_form"):
        st.subheader("مدخلات العمليات")
        col_v1, col_v2 = st.columns(2)
        
        settings['num_sites'] = col_v1.number_input(
            "عدد المواقع الميدانية التي تتم خدمتها (N)",
            min_value=1,
            value=settings['num_sites'],
            step=1,
            key='v_num_sites'
        )
        
        settings['visits_per_site_day'] = col_v2.number_input(
            "متوسط عدد الزيارات المطلوبة للموقع الواحد يومياً (V)",
            min_value=1,
            value=settings['visits_per_site_day'],
            step=1,
            key='v_visits_per_site_day'
        )
        
        st.markdown("---")
        st.subheader("مدخلات الوقت")
        col_t1, col_t2, col_t3 = st.columns(3)
        
        settings['service_time_hr'] = col_t1.number_input(
            "متوسط وقت الخدمة في الموقع (بالساعة) ($T_{service}$)",
            min_value=0.1,
            value=settings['service_time_hr'],
            step=0.1,
            key='v_service_time_hr'
        )
        
        settings['travel_time_hr'] = col_t2.number_input(
            "متوسط وقت الرحلة (ذهاب وإياب) بين المركز والموقع (بالساعة) ($T_{travel}$)",
            min_value=0.1,
            value=settings['travel_time_hr'],
            step=0.1,
            key='v_travel_time_hr'
        )
        
        settings['vehicle_shift_hr'] = col_t3.number_input(
            "ساعات عمل المركبة اليومية/الوردية (H)",
            min_value=1,
            value=settings['vehicle_shift_hr'],
            step=1,
            key='v_vehicle_shift_hr'
        )

        st.markdown("---")
        settings['reserve_factor_vehicles'] = st.slider(
            "نسبة احتياط المركبات (للتغطية والصيانة) (%) ($R_{factor}$)",
            min_value=0, max_value=50, value=settings['reserve_factor_vehicles'], step=1, key="v_reserve_factor"
        )
        
        calculate_button = st.form_submit_button("🔄 احتساب حجم أسطول المركبات", type="primary")

    if calculate_button:
        st.session_state['vehicle_settings'] = settings
        st.session_state['run_calculation_vehicles'] = True
        st.rerun()

    if st.session_state.get('run_calculation_vehicles', False):
        st.session_state['run_calculation_vehicles'] = False
        st.success("✅ جاري حساب حجم الأسطول المطلوب...")
        
        # جلب القيم
        N = settings['num_sites']
        V = settings['visits_per_site_day']
        T_service = settings['service_time_hr']
        T_travel = settings['travel_time_hr']
        H_shift = settings['vehicle_shift_hr']
        R_factor = settings['reserve_factor_vehicles'] / 100
        
        # 1. إجمالي عدد الزيارات اليومية
        total_visits = N * V
        
        # 2. إجمالي الوقت اللازم لكل زيارة
        time_per_visit = T_service + T_travel
        
        # 3. إجمالي ساعات العمل المطلوبة يومياً للمنظومة
        total_hours_needed = total_visits * time_per_visit
        
        # 4. عدد السيارات الأساسي المطلوب
        if H_shift > 0:
            cars_basic = total_hours_needed / H_shift
        else:
            cars_basic = 0

        # 5. العدد النهائي مع الاحتياط (تقريب للأعلى)
        cars_final = math.ceil(cars_basic * (1 + R_factor))
        
        # تخزين النتائج للعرض والتحميل
        results = {
            "إجمالي الزيارات اليومية المطلوبة": f"{total_visits} زيارة",
            "الوقت الكلي المطلوب لتغطية الزيارات (بالساعة)": f"{total_hours_needed:,.2f} ساعة",
            "العدد الأساسي المطلوب من المركبات (وظيفياً)": f"{cars_basic:,.2f} مركبة",
            "نسبة الاحتياط المطبقة": f"{R_factor * 100}%",
            "العدد النهائي المطلوب من المركبات (مع الاحتياط)": cars_final,
        }
        
        st.subheader("نتائج احتساب حجم أسطول المركبات")
        
        st.metric(
            label="**العدد النهائي المطلوب من المركبات (مع الاحتياط)**",
            value=f"{cars_final} مركبة",
            delta=f"{cars_final - math.floor(cars_basic)} مركبات احتياط" if cars_final > 0 else None,
            delta_color="off"
        )
        
        # تحويل النتائج لجدول للعرض والتحميل
        df_results = pd.DataFrame(results.items(), columns=["البيان", "القيمة"])
        df_results = df_results.set_index("البيان")
        
        st.dataframe(df_results, use_container_width=True)
        
        st.session_state['last_vehicle_df'] = df_results.copy()
        
    # **منطق التحميل**
    if 'last_vehicle_df' in st.session_state:
        
        def download_vehicle_excel():
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_to_excel = st.session_state['last_vehicle_df'].copy()
                df_to_excel.to_excel(writer, sheet_name='احتياج المركبات')
            processed_data = output.getvalue()
            return processed_data
            
        st.download_button(
            label="⬇️ تحميل نتائج احتساب المركبات (Excel)",
            data=download_vehicle_excel(),
            file_name="احتساب_أسطول_المركبات.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# -------------------------------------------------------------------
# 7. واجهة الشريط الجانبي (Sidebar UI)
# -------------------------------------------------------------------
def sidebar_ui():
    """تجهيز وعرض الشريط الجانبي."""
    
    # 1. تهيئة القيم الافتراضية لأول مرة (لم تتغير)
    if 'num_hajjaj_present' not in st.session_state:
        st.session_state['num_hajjaj_present'] = 100000
    if 'num_hajjaj_flow' not in st.session_state:
        st.session_state['num_hajjaj_flow'] = 25000
    if 'service_days' not in st.session_state:
        st.session_state['service_days'] = 8
    if 'staff_hours' not in st.session_state:
        st.session_state['staff_hours'] = 8
    if 'shifts_count' not in st.session_state:
        st.session_state['shifts_count'] = 3
    if 'reserve_factor_input' not in st.session_state:
        st.session_state['reserve_factor_input'] = 10 # 10%

    # تهيئة قيم المكافآت الافتراضية
    for role, default_salary in DEFAULT_SALARY.items():
        key = f'salary_{role}'
        if key not in st.session_state:
            st.session_state[key] = default_salary

    # 2. عرض الشريط الجانبي
    with st.sidebar:
        
        # 3. عرض اللوغو (اختياري)
        # *************************************************************
        st.image(
            "logo.png", 
            caption="شعار المنشأة", 
            use_column_width=True
        )
        # *************************************************************
        
        st.header("إعدادات النظام العامة ⚙️")
        
        st.button("🏠 العودة لصفحة البداية", on_click=switch_to_landing, use_container_width=True, type="secondary")
        st.markdown("---")
        
        with st.container(border=True): # الإطار الأول
            st.subheader("المعايير الأساسية")
            st.number_input(
                "عدد الحجاج المتواجدين (تقديري)",
                min_value=1,
                value=st.session_state['num_hajjaj_present'],
                step=1000,
                key="num_hajjaj_present"
            )
            st.number_input(
                "عدد الحجاج التدفق اليومي (تقديري)",
                min_value=1,
                value=st.session_state['num_hajjaj_flow'],
                step=1000,
                key="num_hajjaj_flow"
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
            
            # تم التحديث: استخدام جميع الأدوار في DEFAULT_SALARY بما فيها المدير والإداري
            for role, default_salary in DEFAULT_SALARY.items():
                key = f'salary_{role}'
                # التأكد من استخدام المسمى الجديد للمشرف في العرض
                display_role = role
                st.number_input(
                    f"مكافأة **{display_role}** (ريال)",
                    min_value=1,
                    value=st.session_state[key],
                    step=100,
                    key=key
                )
        
# -------------------------------------------------------------------
# 8. الدالة الرئيسية (Main Function)
# -------------------------------------------------------------------
def main():
    # 6. إعدادات الصفحة و التوجيه نحو اليمين (RTL)
    st.set_page_config(
        page_title="نظام تخطيط القوى العاملة",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # تطبيق CSS مخصص للتوجيه من اليمين لليسار
    st.markdown("""
    <style>
        /* 1. توجيه جميع النصوص من اليمين لليسار */
        html, body, [class*="st-"] {
            direction: rtl;
            text-align: right;
        }
        /* 2. توجيه النصوص داخل العناصر لليسار (مثل الـ input) */
        input {
            text-align: right !important;
        }
        /* 3. توجيه العناصر المتجاورة (الأعمدة) لتبدأ من اليمين */
        div[data-testid="stHorizontalBlock"] {
            flex-direction: row-reverse;
        }
        /* 4. تخصيص الخلفية للحاويات ذات الإطار (تم التعديل لتصبح أغمق قليلاً) */
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
    
    # 7. تهيئة الحالة الافتراضية (Session State)
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'landing' # تغيير الصفحة الافتراضية
    if 'next_center_id' not in st.session_state:
        st.session_state['next_center_id'] = 1
    # إضافة مركز الضيافة الافتراضي
    if 'dynamic_hospitality_centers' not in st.session_state:
        st.session_state['dynamic_hospitality_centers'] = []
    if not st.session_state['dynamic_hospitality_centers']:
        add_hospitality_center(is_default=True)

    # 8. إعداد الشريط الجانبي
    sidebar_ui()
        
    # 9. عرض الصفحة المختارة
    if st.session_state['current_page'] == 'landing':
        landing_page()
    elif st.session_state['current_page'] == 'main':
        main_page_logic()
    elif st.session_state['current_page'] == 'all':
        all_page_logic()
    elif st.session_state['current_page'] == 'vehicles':
        vehicle_page_logic()


if __name__ == "__main__":
    main()
