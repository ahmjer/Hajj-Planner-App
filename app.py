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
    
    # لا نطبق الاحتياط هنا، بل نطبقه على الإجمالي بعد التوزيع الهرمي
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Time'}

def calculate_ratio_based_staff(num_hajjaj, ratio, reserve_factor):
    """تحسب القوى العاملة للإدارات التي تعتمد على التغطية (حاج/موظف)."""
    
    basic_staff = math.ceil(num_hajjaj / ratio)
    # لا نطبق الاحتياط هنا، بل نطبقه على الإجمالي بعد التوزيع الهرمي
    return {'Basic': basic_staff, 'Total': basic_staff, 'CalcType': 'Ratio'}

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
    
    # ****** تم التأكد من إغلاق جميع علامات التنصيص هنا ******
    return {
        'رئيس': رئيس,
        'مساعد رئيس': مساعد_رئيس, 
        'مشرف ميداني': math.ceil(مشرفون_اجمالي * 0.7), 
        'مشرف اداري': مشرفون_اجمالي - math.ceil(مشرفون_اجمالي * 0.7), 
        'مقدم خدمة': مقدم_خدمة, 
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
# -------------------------------------------------------------------

st.set_page_config(page_title="🕋 مخطط القوى العاملة للحج (بأنواع الإدارات)", layout="wide")

st.title("🕋 أداة تخطيط القوى العاملة الذكية")
st.markdown("---")

# -------------------------------------------------------------------
# القسم الأول: الإعدادات العامة ونوع الإدارة
# -------------------------------------------------------------------

st.sidebar.header("1. الإعدادات العامة")

department_type_choice = st.sidebar.selectbox(
    "اختر نوع الإدارة المراد حسابه:",
    options=list(DEPARTMENTS.keys()),
    key="dept_type"
)

num_hajjaj = st.sidebar.number_input("عدد الحجاج الإجمالي", min_value=1, value=3000, step=100)
service_days = st.sidebar.number_input("فترة الخدمة الإجمالية (بالأيام)", min_value=1, value=6)
staff_work_hours_day = st.sidebar.number_input("ساعات عمل الموظف اليومية", min_value=1, max_value=16, value=8)
reserve_factor_input = st.sidebar.slider("نسبة الاحتياط الإجمالي (%)", min_value=0, max_value=50, value=15)
reserve_factor = reserve_factor_input / 100 


# --- المدخلات الخاصة بالهيكل الإداري (التوزيع الهرمي) ---
st.sidebar.header("2. معايير الهيكل الإداري")
st.sidebar.markdown('**نسب الإشراف (للتوزيع الهرمي)**')
ratio_supervisor = st.sidebar.number_input("مقدم خدمة / مشرف", min_value=1, value=8)
ratio_assistant_head = st.sidebar.number_input("مشرف / مساعد رئيس", min_value=1, value=4)
ratio_head = st.sidebar.number_input("مساعد رئيس / رئيس", min_value=1, value=3)


# -------------------------------------------------------------------
# القسم الثاني: مدخلات الإدارات حسب النوع المختار
# -------------------------------------------------------------------

st.sidebar.header(f"3. معايير {department_type_choice}")

# تجميع المدخلات ديناميكياً
ratios = {} 
time_based_inputs = {} 
bus_ratio_inputs = {} 

for dept in DEPARTMENTS[department_type_choice]:
    name = dept['name']
    
    if dept['type'] == 'Ratio':
        ratios[name] = st.sidebar.number_input(f"{name} (حاج / موظف)", min_value=1, value=dept['default_ratio'])
    
    elif dept['type'] == 'Time':
        time_based_inputs[name] = st.sidebar.number_input(f"{name} (دقيقة/حاج)", min_value=0.5, value=dept['default_time'], step=0.1)

    elif dept['type'] == 'Bus_Ratio':
        st.sidebar.markdown(f"**مدخلات {name}**")
        num_buses = st.sidebar.number_input("عدد الحافلات المتوقعة", min_value=1, value=20)
        bus_ratio_inputs['Bus_Count'] = num_buses
        bus_ratio_inputs['Ratio'] = st.sidebar.number_input(f"{name} (حافلة / موظف إرشاد)", min_value=1, value=dept['default_ratio'])


# -------------------------------------------------------------------
# تنفيذ الحسابات والتوزيع
# -------------------------------------------------------------------

st.markdown("---")
calculate_button = st.button(f"🔄 اضغط هنا لحساب وعرض احتياج {department_type_choice}", type="primary")

if calculate_button: 
    
    all_results = []
    total_staff_needed = 0

    # أ. حساب الإدارات المعتمدة على التغطية (حاج / موظف)
    for dept, ratio in ratios.items():
        res_basic = calculate_ratio_based_staff(num_hajjaj, ratio, 0) 
        staff_breakdown = distribute_staff(res_basic['Basic'], ratio_supervisor, ratio_assistant_head, ratio_head)
        
        # نجمع كل الموظفين في الهيكل الهرمي ثم نطبق الاحتياط
        total_staff_in_hierarchy = sum(staff_breakdown.values())
        total_needed_with_reserve = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))
        
        all_results.append({
            'الإدارة': dept, 
            'رئيس': staff_breakdown['رئيس'], 
            'مساعد رئيس': staff_breakdown['مساعد رئيس'],
            'مشرف اداري': staff_breakdown['مشرف اداري'],
            'مشرف ميداني': staff_breakdown['مشرف ميداني'],
            'مقدم خدمة': staff_breakdown['مقدم خدمة'],
            'اداري': staff_breakdown['اداري'],
            'المجموع الإجمالي (بالاحتياط)': total_needed_with_reserve
        })
        total_staff_needed += total_needed_with_reserve


    # ب. حساب إرشاد الحافلات (معيار خاص) 
    if 'Bus_Count' in bus_ratio_inputs:
        num_units = bus_ratio_inputs['Bus_Count']
        bus_ratio = bus_ratio_inputs['Ratio']
        
        res_basic_buses = calculate_ratio_based_staff(num_units, bus_ratio, 0) 
        staff_breakdown_buses = distribute_staff(res_basic_buses['Basic'], ratio_supervisor, ratio_assistant_head, ratio_head)
        
        total_staff_in_hierarchy = sum(staff_breakdown_buses.values())
        total_needed_buses = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

        all_results.append({
            'الإدارة': 'إرشاد الحافلات', 
            'رئيس': staff_breakdown_buses['رئيس'], 
            'مساعد رئيس': staff_breakdown_buses['مساعد رئيس'],
            'مشرف اداري': staff_breakdown_buses['مشرف اداري'],
            'مشرف ميداني': staff_breakdown_buses['مشرف ميداني'],
            'مقدم خدمة': staff_breakdown_buses['مقدم خدمة'],
            'اداري': staff_breakdown_buses['اداري'],
            'المجموع الإجمالي (بالاحتياط)': total_needed_buses
        })
        total_staff_needed += total_needed_buses


    # ج. حساب الإدارات المعتمدة على الزمن (Time-based)
    for dept, time_min in time_based_inputs.items():
        res_basic_time = calculate_time_based_staff(num_hajjaj * 2, time_min, service_days, staff_work_hours_day, 0)
        staff_breakdown_time = distribute_staff(res_basic_time['Basic'], ratio_supervisor, ratio_assistant_head, ratio_head)
        
        total_staff_in_hierarchy = sum(staff_breakdown_time.values())
        total_needed_time = math.ceil(total_staff_in_hierarchy * (1 + reserve_factor))

        all_results.append({
            'الإدارة': dept, 
            'رئيس': staff_breakdown_time['رئيس'], 
            'مساعد رئيس': staff_breakdown_time['مساعد رئيس'],
            'مشرف اداري': staff_breakdown_time['مشرف اداري'],
            'مشرف ميداني': staff_breakdown_time['مشرف ميداني'],
            'مقدم خدمة': staff_breakdown_time['مقدم خدمة'],
            'اداري': staff_breakdown_time['اداري'],
            'المجموع الإجمالي (بالاحتياط)': total_needed_time
        })
        total_staff_needed += total_needed_time


    # -------------------------------------------------------------------
    # عرض النتائج
    # -------------------------------------------------------------------

    st.subheader(f"نتائج الاحتياج للقوى العاملة والتوزيع الوظيفي لـ {department_type_choice}")
    st.markdown("يتم تطبيق نسبة الاحتياط على **المجموع الإجمالي** لكل إدارة.")

    # نحدد ترتيب الأعمدة ليكون منطقياً (من الهرم إلى القاعدة)
    column_order = [
        'رئيس', 'مساعد رئيس', 'مشرف اداري', 'مشرف ميداني', 
        'مقدم خدمة', 'اداري', 'المجموع الإجمالي (بالاحتياط)'
    ]
    
    df = pd.DataFrame(all_results)
    df = df.set_index('الإدارة') 
    df = df[column_order] # ترتيب الأعمدة

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
    # رسالة ترحيبية أو إرشادية عند أول تحميل
    st.info(f"يرجى اختيار نوع الإدارة وتعديل المعايير في الشريط الجانبي ثم النقر على زر الحساب لرؤية النتائج لـ {department_type_choice}.")
