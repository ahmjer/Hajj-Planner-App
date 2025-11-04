import streamlit as st
import math
import pandas as pd

# -------------------------------------------------------------------
# الدوال المساعدة للحساب (Logic)
# -------------------------------------------------------------------

def calculate_time_based_staff(total_events, time_per_event_min, service_days, staff_work_hours_day, reserve_factor):
    time_per_event_hrs = time_per_event_min / 60
    total_hours_needed = total_events * time_per_event_hrs
    total_staff_available_hours = service_days * staff_work_hours_day
    
    if total_staff_available_hours > 0:
        basic_staff = math.ceil(total_hours_needed / total_staff_available_hours)
    else:
        basic_staff = 0
    
    total_staff = math.ceil(basic_staff * (1 + reserve_factor))
    return {'Basic': basic_staff, 'Total': total_staff, 'CalcType': 'Time'}

def calculate_ratio_based_staff(num_hajjaj, ratio, reserve_factor):
    basic_staff = math.ceil(num_hajjaj / ratio)
    total_staff = math.ceil(basic_staff * (1 + reserve_factor))
    return {'Basic': basic_staff, 'Total': total_staff, 'CalcType': 'Ratio'}

def distribute_staff(total_basic_staff, ratio_supervisor, ratio_assistant_head, ratio_head):
    """
    توزيع إجمالي الاحتياج (المقدمين) إلى الهرم الإداري.
    """
    
    مقدم_خدمة = total_basic_staff
    مشرفون = math.ceil(مقدم_خدمة / ratio_supervisor)
    مساعد_رئيس = math.ceil(مشرفون / ratio_assistant_head)
    رئيس = math.ceil(مساعد_رئيس / ratio_head)
    إداري = 1 
    
    return {
        'مقدم_خدمة': مقدم_خدمة, 
        'مشرف_ميداني': math.ceil(مشرفون * 0.7), 
        'مشرف_إداري': مشرفون - math.ceil(مشرفون * 0.7), 
        'مساعد_رئيس': مساعد_رئيس,
        'رئيس': رئيس,
        'إداري': إداري
    }

# -------------------------------------------------------------------
# واجهة المستخدم (Streamlit UI)
# -------------------------------------------------------------------

st.set_page_config(page_title="🕋 مخطط القوى العاملة للحج (بالهيكلية الوظيفية)", layout="wide")

st.title("🕋 أداة تخطيط القوى العاملة الذكية (بالهيكلية الوظيفية)")
st.markdown("---")

st.sidebar.header("1. الإعدادات العامة للبعثة")

# المدخلات العامة في الشريط الجانبي (Sidebar)
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


# --- المدخلات الخاصة بالإدارات (التغطية والزمن) ---
st.sidebar.header("3. معايير التغطية والتدفق")
# معايير التغطية (Ratio-based)
st.sidebar.subheader("معايير التغطية (حاج/موظف)")
ratios = {}
ratios['مركز الضيافة'] = st.sidebar.number_input("مركز الضيافة (حاج / موظف)", min_value=1, value=75)
ratios['الخدمات الميدانية والإسكان'] = st.sidebar.number_input("الإسكان (حاج / موظف)", min_value=1, value=50)
ratios['المتابعة الميدانية'] = st.sidebar.number_input("المتابعة (حاج / موظف)", min_value=1, value=100)
ratios['الدعم والضيافة'] = st.sidebar.number_input("الدعم (حاج / موظف)", min_value=1, value=80)
ratios['التوجيه'] = st.sidebar.number_input("التوجيه (حاج / موظف)", min_value=1, value=90)
ratios['الرعاية الصحية'] = st.sidebar.number_input("الرعاية الصحية (حاج / موظف)", min_value=1, value=200)

# معايير الحافلات
st.sidebar.subheader("إرشاد الحافلات (معيار خاص)")
num_buses = st.sidebar.number_input("عدد الحافلات المتوقعة", min_value=1, value=20)
buses_per_staff = st.sidebar.number_input("حافلة / موظف إرشاد", min_value=1, value=2)

# معايير الزمن (Time-based)
st.sidebar.subheader("معايير التدفق الزمني (دقيقة/حدث)")
time_based_inputs = {}
time_based_inputs['استقبال الهجرة'] = st.sidebar.number_input("استقبال الهجرة (دقيقة/حاج)", min_value=0.5, value=2.0, step=0.1)
time_based_inputs['استقبال المطار'] = st.sidebar.number_input("استقبال المطار (دقيقة/حاج)", min_value=0.5, value=3.0, step=0.1)
time_based_inputs['استقبال القطار'] = st.sidebar.number_input("استقبال القطار (دقيقة/حاج)", min_value=0.5, value=1.5, step=0.1)
time_based_inputs['الزيارة وإرشاد التأهيل'] = st.sidebar.number_input("الزيارة (دقيقة/حاج)", min_value=0.5, value=2.5, step=0.1)


# -------------------------------------------------------------------
# تنفيذ الحسابات والتوزيع
# -------------------------------------------------------------------

st.markdown("---")
# **** الزر الذي يجبر التطبيق على إعادة الحساب والعرض ****
calculate_button = st.button("🔄 اضغط هنا لحساب وعرض الاحتياج", type="primary")

# يتم الحساب والعرض فقط عند الضغط على الزر، أو عند تحميل التطبيق لأول مرة (حيث أن num_hajjaj موجودة)
if calculate_button: # يمكن تعديلها إلى 'if calculate_button or not st.session_state.get("results_displayed"): ' 
    
    all_results = []
    total_staff_needed = 0

    # أ. حساب الإدارات المعتمدة على التغطية (حاج / موظف)
    for dept, ratio in ratios.items():
        res_basic = calculate_ratio_based_staff(num_hajjaj, ratio, 0) 
        staff_breakdown = distribute_staff(res_basic['Basic'], ratio_supervisor, ratio_assistant_head, ratio_head)
        
        total_needed_with_reserve = math.ceil(sum(staff_breakdown.values()) * (1 + reserve_factor))
        
        all_results.append({
            'الإدارة': dept, 
            'رئيس': staff_breakdown['رئيس'], 
            'مساعد رئيس': staff_breakdown['مساعد_رئيس'],
            'مشرف إداري': staff_breakdown['مشرف_إداري'],
            'مشرف ميداني': staff_breakdown['مشرف_ميداني'],
            'مقدم خدمة': staff_breakdown['مقدم_خدمة'],
            'إداري': staff_breakdown['إداري'],
            'المجموع الإجمالي (بالاحتياط)': total_needed_with_reserve
        })
        total_staff_needed += total_needed_with_reserve


    # ب. حساب إرشاد الحافلات (معيار خاص)
    res_basic_buses = calculate_ratio_based_staff(num_buses, buses_per_staff, 0) 
    staff_breakdown_buses = distribute_staff(res_basic_buses['Basic'], ratio_supervisor, ratio_assistant_head, ratio_head)
    total_needed_buses = math.ceil(sum(staff_breakdown_buses.values()) * (1 + reserve_factor))

    all_results.append({
        'الإدارة': 'إرشاد الحافلات', 
        'رئيس': staff_breakdown_buses['رئيس'], 
        'مساعد رئيس': staff_breakdown_buses['مساعد_رئيس'],
        'مشرف إداري': staff_breakdown_buses['مشرف_إداري'],
        'مشرف ميداني': staff_breakdown_buses['مشرف_ميداني'],
        'مقدم خدمة': staff_breakdown_buses['مقدم_خدمة'],
        'إداري': staff_breakdown_buses['إداري'],
        'المجموع الإجمالي (بالاحتياط)': total_needed_buses
    })
    total_staff_needed += total_needed_buses


    # ج. حساب الإدارات المعتمدة على الزمن (Time-based)
    for dept, time_min in time_based_inputs.items():
        res_basic_time = calculate_time_based_staff(num_hajjaj * 2, time_min, service_days, staff_work_hours_day, 0)
        staff_breakdown_time = distribute_staff(res_basic_time['Basic'], ratio_supervisor, ratio_assistant_head, ratio_head)
        total_needed_time = math.ceil(sum(staff_breakdown_time.values()) * (1 + reserve_factor))

        all_results.append({
            'الإدارة': dept, 
            'رئيس': staff_breakdown_time['رئيس'], 
            'مساعد رئيس': staff_breakdown_time['مساعد_رئيس'],
            'مشرف إداري': staff_breakdown_time['مشرف_إداري'],
            'مشرف ميداني': staff_breakdown_time['مشرف_ميداني'],
            'مقدم خدمة': staff_breakdown_time['مقدم_خدمة'],
            'إداري': staff_breakdown_time['إداري'],
            'المجموع الإجمالي (بالاحتياط)': total_needed_time
        })
        total_staff_needed += total_needed_time


    # -------------------------------------------------------------------
    # عرض النتائج
    # -------------------------------------------------------------------

    st.subheader("نتائج الاحتياج للقوى العاملة والتوزيع الوظيفي")
    st.markdown("يتم تطبيق نسبة الاحتياط على **المجموع الإجمالي** لكل إدارة.")

    # إنشاء جدول النتائج
    df = pd.DataFrame(all_results)
    df = df.set_index('الإدارة') 

    st.dataframe(df.style.background_gradient(cmap='Blues', subset=['المجموع الإجمالي (بالاحتياط)']), use_container_width=True)

    st.markdown("---")

    # عرض الإجمالي
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="**المجموع الكلي للقوى العاملة المطلوبة للشركة**",
            value=f"{total_staff_needed} موظف",
        )
    with col2:
        st.info(f"نسبة الاحتياط الإجمالية المطبقة: {reserve_factor_input}%")
else:
    st.info("يرجى تعديل المدخلات في الشريط الجانبي ثم النقر على زر الحساب لرؤية النتائج.")
