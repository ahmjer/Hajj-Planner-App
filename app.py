import streamlit as st 
import math
import pandas as pd

# -------------------------------------------------------------------
# الثوابت والدوال 
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
    admin_supervisor_fixed = 0 
    
    total_hierarchical_supervisors = math.ceil(service_provider / ratio_supervisor)
    
    total_supervisors = max(total_hierarchical_supervisors, field_supervisor_fixed)
    
    assistant_head_fixed = ASSISTANT_HEADS_PER_SHIFT * shifts
    assistant_head = max(assistant_head_fixed, math.ceil(total_supervisors / ratio_assistant_head))
    
    head = 1  
    admin_staff = 1 
    
    return {
        "Head": head, 
        "Assistant_Head": assistant_head, 
        "Field_Supervisor": field_supervisor_fixed, 
        "Admin_Supervisor": admin_supervisor_fixed, 
        "Service_Provider": service_provider, 
        "Admin_Staff": admin_staff
    } 

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

# -------------------------------------------------------------------
# الواجهة الرئيسية (Streamlit UI)
# -------------------------------------------------------------------

st.set_page_config(page_title="مخطط القوى العاملة للحج", layout="wide", page_icon=None) 

# 📌📌📌 كود CSS لحقن دعم RTL القوي 
st.markdown("""
<style>
/* تفعيل RTL على جميع النصوص والمكونات */
html, body, [class*="st-emotion-"] {
    direction: rtl;
    text-align: right;
}

/* تعديل عرض الشريط الجانبي (Sidebar) لضمان محتواه RTL */
section[data-testid="stSidebar"] {
    text-align: right;
}
</style>
""", unsafe_allow_html=True)
# 📌📌📌 نهاية كود CSS

# العنوان الرئيسي
st.title("أداة تخطيط القوى العاملة الذكية")
st.markdown("---")


# -------------------------------------------------------------------
# القسم الأول: الإعدادات العامة ونوع الإدارة (في الشريط الجانبي)
# -------------------------------------------------------------------

st.sidebar.image("logo.png", use_column_width=True) 

st.sidebar.header("1. الإعدادات العامة")

# 📌 مدخلات عدد الحجاج الجديدة
num_hajjaj_present = st.sidebar.number_input(
    "1. إجمالي عدد الحجاج (المتواجدين)", 
    min_value=1, value=5000, step=100, 
    key="num_hajjaj_present"
)
num_hajjaj_flow = st.sidebar.number_input(
    "2. إجمالي حجاج التدفق اليومي (وصول/مغادرة)", 
    min_value=1, value=1000, step=100, 
    key="num_hajjaj_flow"
)

service_days = st.sidebar.number_input("فترة الخدمة الإجمالية (بالأيام)", min_value=1, value=6, key="service_days")
staff_work_hours_day = st.sidebar.number_input("ساعات عمل الموظف اليومية", min_value=1, max_value=16, value=8, key="staff_hours")
reserve_factor_input = st.sidebar.slider("نسبة الاحتياط الإجمالي (%)", min_value=0, max_value=50, value=15, key="reserve_factor_input")
reserve_factor = reserve_factor_input / 100 


# --- المدخلات الخاصة بالهيكل الإداري (التوزيع الهرمي) ---
st.sidebar.header("3. معايير الهيكل الإداري")
st.sidebar.markdown('**نسب الإشراف (للتوزيع الهرمي)**')

shifts_count = st.sidebar.selectbox(
    "عدد فترات العمل اليومية المطلوبة",
    options=[1, 2, 3],
    index=2,
    key="shifts_count"
)
st.sidebar.info(f"مشرف ميداني ومساعد رئيس سيزيدان لكل {shifts_count} فترة.")

ratio_supervisor = st.sidebar.number_input("مقدم خدمة / مشرف", min_value=1, value=8, key="ratio_supervisor")
ratio_assistant_head = st.sidebar.number_input("مشرف / مساعد رئيس (للهرم)", min_value=1, value=4, key="ratio_assistant_head")


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
            
            # 📌 إضافة خيار تحديد المعيار: تواجد أو تدفق
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

            # A. إدخال نسبة التغطية (لكل ما يعتمد على عدد الحجاج)
            if dept_type in ['Ratio', 'Time']:
                default_cov = dept.get('default_coverage', 100)
                coverage_label = f"نسبة تغطية (%)"
                coverage_key = f"cov_{department_type_choice}_{name}_{i}"
                
                coverage_val = st.slider(coverage_label, min_value=0, max_value=100, value=default_cov, key=coverage_key)
                coverage_percentages[name] = coverage_val / 100 

            # B. إدخال معيار الاحتساب (Ratio/Time/Bus)
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

    TRANSLATION_MAP = {
        "Head": "رئيس", 
        "Assistant_Head": "مساعد رئيس", 
        "Field_Supervisor": "مشرف ميداني", 
        "Service_Provider": "مقدم خدمة", 
    }

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
        "رئيس", "مساعد رئيس", "مشرف اداري", "مشرف ميداني", 
        "مقدم خدمة", "اداري", "المجموع الإجمالي (بالاحتياط)" 
    ]
    
    df = pd.DataFrame(all_results)
    df = df.set_index("الإدارة") 
    df = df[column_order]

    st.dataframe(df, use_container_width=True)

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
