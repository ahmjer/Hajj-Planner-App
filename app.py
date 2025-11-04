import streamlit as st 
import math
import pandas as pd

# -------------------------------------------------------------------
# الثوابت والدوال 
# -------------------------------------------------------------------

# ثوابت عامة 
TOTAL_WORK_HOURS = 24
SUPERVISORS_PER_SHIFT = 1
ASSISTANT_HEADS_PER_SHIFT = 1 # 📌 ثابت جديد: مساعد رئيس واحد لكل فترة

# تم إبقاء هذا الثابت للرئيس، بالرغم من أننا سنستخدم 1 ثابتة
DEFAULT_HEAD_ASSISTANT_RATIO = 4 

# 📌 تم حذف FIELD_SUPERVISORS_PER_LOCATION لأنه سيُحتسب ديناميكياً


def calculate_time_based_staff(total_events, time_per_event_min, service_days, staff_work_hours_day, reserve_factor):
    time_per_event_hrs = time_per_event_min / 60
    total_hours_needed = total_events * time_per_event_hrs
    total_staff_available_hours = service_days * staff_work_hours_day
    
    basic_staff = math.ceil(total_hours_needed / total_staff_available_hours) if total_staff_available_hours > 0 else 0
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Time'}

def calculate_ratio_based_staff(num_hajjaj_in_center, ratio, reserve_factor):
    basic_staff = math.ceil(num_hajjaj_in_center / ratio)
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Ratio'}

# 📌 تم إضافة معامل shifts لتلقي عدد الفترات من الواجهة
def distribute_staff(total_basic_staff, ratio_supervisor, ratio_assistant_head, shifts):
    service_provider = total_basic_staff  
    
    # 📌 التعديل الأول: المشرف الميداني يحسب بناءً على عدد الفترات
    field_supervisor_fixed = SUPERVISORS_PER_SHIFT * shifts 
    admin_supervisor_fixed = 0 
    
    total_hierarchical_supervisors = math.ceil(service_provider / ratio_supervisor)
    
    # نأخذ القيمة الأكبر بين الهرم أو التغطية الميدانية الثابتة
    total_supervisors = max(total_hierarchical_supervisors, field_supervisor_fixed)
    
    # 📌 التعديل الثاني: مساعد الرئيس يحسب بناءً على عدد الفترات
    assistant_head_fixed = ASSISTANT_HEADS_PER_SHIFT * shifts
    assistant_head = max(assistant_head_fixed, math.ceil(total_supervisors / ratio_assistant_head))
    
    # تم تثبيت الرئيس بـ 1
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
        {"name": "مركز الضيافة", "type": "Ratio", "default_ratio": 200, "default_coverage": 100}, 
    ],
    "الوصول والمغادرة": [
        {"name": "استقبال الهجرة", "type": "Ratio", "default_ratio": 100, "default_coverage": 30},
        {"name": "استقبال المطار", "type": "Ratio", "default_ratio": 100, "default_coverage": 50},
        {"name": "استقبال القطار", "type": "Ratio", "default_ratio": 100, "default_coverage": 20},
        {"name": "إرشاد الحافلات", "type": "Bus_Ratio", "default_ratio": 2}, 
    ],
    "الدعم والمساندة": [
        {"name": "متابعة ميدانية", "type": "Ratio", "default_ratio": 100, "default_coverage": 100},
        {"name": "الخدمات الميدانية والاسكان ", "type": "Ratio", "default_ratio": 100, "default_coverage": 100},
        {"name": "الزيارة وإرشاد التأهيين ", "type": "Ratio", "default_ratio": 80, "default_coverage": 100},
        {"name": " الدعم والضيافة", "type": "Time", "default_time": 2.5, "default_coverage": 100}, 
        {"name": "الرعاية صحية", "type": "Ratio", "default_ratio": 200, "default_coverage": 100},
    ]
} 

# -------------------------------------------------------------------
# الواجهة الرئيسية (Streamlit UI)
# -------------------------------------------------------------------

st.set_page_config(page_title="🕋 مخطط القوى العاملة للحج", layout="wide") 

st.title("🕋 أداة تخطيط القوى العاملة الذكية")
st.markdown("---")

# -------------------------------------------------------------------
# القسم الأول: الإعدادات العامة ونوع الإدارة (في الشريط الجانبي)
# -------------------------------------------------------------------

st.sidebar.header("1. الإعدادات العامة")

num_hajjaj = st.sidebar.number_input("عدد الحجاج الإجمالي", min_value=1, value=5000, step=100, key="num_hajjaj")
service_days = st.sidebar.number_input("فترة الخدمة الإجمالية (بالأيام)", min_value=1, value=6, key="service_days")
staff_work_hours_day = st.sidebar.number_input("ساعات عمل الموظف اليومية", min_value=1, max_value=16, value=8, key="staff_hours")
reserve_factor_input = st.sidebar.slider("نسبة الاحتياط الإجمالي (%)", min_value=0, max_value=50, value=15, key="reserve_factor_input")
reserve_factor = reserve_factor_input / 100 


# --- المدخلات الخاصة بالهيكل الإداري (التوزيع الهرمي) ---
st.sidebar.header("2. معايير الهيكل الإداري")
st.sidebar.markdown('**نسب الإشراف (للتوزيع الهرمي)**')

# 📌 إضافة مدخل اختيار الفترات هنا
shifts_count = st.sidebar.selectbox(
    "عدد فترات العمل اليومية المطلوبة",
    options=[1, 2, 3],
    index=2, # الافتراض هو 3 فترات عمل يومية
    key="shifts_count"
)
st.sidebar.info(f"مشرف ميداني ومساعد رئيس **سيزيدان** لكل فترة. (1 مشرف / 1 مساعد رئيس لكل فترة)")

ratio_supervisor = st.sidebar.number_input("مقدم خدمة / مشرف", min_value=1, value=8, key="ratio_supervisor")
ratio_assistant_head = st.sidebar.number_input("مشرف / مساعد رئيس (للهرم)", min_value=1, value=4, key="ratio_assistant_head")


# -------------------------------------------------------------------
# 📌 القسم الثاني: مدخلات الإدارات (في الجزء العلوي من الصفحة الرئيسية)
# -------------------------------------------------------------------

st.subheader("3. تحديد الإدارة ومعايير الاحتساب")
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

    cols = st.columns(3)
    col_index = 0

    for i, dept in enumerate(DEPARTMENTS[department_type_choice]):
        name = dept['name']
        dept_type = dept['type']
        
        col = cols[col_index % 3] 
        col_index += 1

        with col:
            st.markdown(f"***_{name}_***") 

            # A. إدخال نسبة التغطية (لكل ما يعتمد على عدد الحجاج)
            if dept_type in ['Ratio', 'Time']:
                default_cov = dept.get('default_coverage', 100)
                coverage_label = f"نسبة تغطية (%)"
                coverage_key = f"cov_{department_type_choice}_{name}_{i}"
                
                coverage_val = st.slider(coverage_label, min_value=0, max_value=100, value=default_cov, key=coverage_key)
                coverage_percentages[name] = coverage_val / 100 

            # B. إدخال معيار الاحتساب (Ratio/Time/Bus)
            if dept_type == 'Ratio':
                label = "المعيار (حاج/موظف)"
                key_val = f"ratio_{department_type_choice}_{name}_{i}" 
                ratios[name] = st.number_input(label, min_value=1, value=dept['default_ratio'], key=key_val)
            
            elif dept_type == 'Time':
                label = "المعيار (دقيقة/حاج)"
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
# زر الاحتساب
calculate_button = st.button(f"🔄 اضغط هنا لحساب وعرض احتياج {department_type_choice}", type="primary", key="calculate_button_main")

if calculate_button: 
    
    st.success("✅ تم الضغط على الزر. جاري بدء الحساب...") 

    all_results = []
    total_staff_needed = 0

    TRANSLATION_MAP = {
        "Head": "رئيس", 
        "Assistant_Head": "مساعد رئيس", 
        "Field_Supervisor": "مشرف ميداني", 
        "Admin_Supervisor": "مشرف اداري", 
        "Service_Provider": "مقدم خدمة", 
        "Admin_Staff": "اداري"
    }

    # أ. حساب الإدارات المعتمدة على التغطية (حاج / موظف)
    for dept, ratio in ratios.items():
        actual_hajjaj_in_center = num_hajjaj * coverage_percentages[dept]
        
        res_basic = calculate_ratio_based_staff(actual_hajjaj_in_center, ratio, 0) 
        # 📌 تم تمرير عدد الفترات
        staff_breakdown = distribute_staff(res_basic['Basic'], ratio_supervisor, ratio_assistant_head, shifts_count)
        
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
        
        res_basic_buses = calculate_ratio_based_staff(num_units, bus_ratio, 0) 
        # 📌 تم تمرير عدد الفترات
        staff_breakdown_buses = distribute_staff(res_basic_buses['Basic'], ratio_supervisor, ratio_assistant_head, shifts_count)
        
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
        actual_hajjaj_in_center = num_hajjaj * coverage_percentages[dept]
        
        res_basic_time = calculate_time_based_staff(actual_hajjaj_in_center * 2, time_min, service_days, staff_work_hours_day, 0)
        
        # 📌 تم تمرير عدد الفترات
        staff_breakdown_time = distribute_staff(res_basic_time['Basic'], ratio_supervisor, ratio_assistant_head, shifts_count)
        
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
        "مقدم خدمة", "المجموع الإجمالي (بالاحتياط)"
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
