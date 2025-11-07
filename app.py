# ... (بقية الثوابت والدوال)

# -------------------------------------------------------------------
# منطق الشاشة الموحدة الجديدة (All Departments Page Logic)
# -------------------------------------------------------------------

def all_departments_page():
    """
    شاشة لعرض وحساب احتياج القوى العاملة لجميع الإدارات في جدول واحد، مع إمكانية تعديل المعايير أولاً.
    """
    st.title("📊 تخطيط القوى العاملة الموحد")
    st.markdown("---")
    
    # 1. تعريف المتغيرات من Session State
    sidebar_inputs = {
        'num_hajjaj_present': st.session_state["num_hajjaj_present"],
        'num_hajjaj_flow': st.session_state["num_hajjaj_flow"],
        'service_days': st.session_state["service_days"],
        'staff_hours': st.session_state["staff_hours"],
        'reserve_factor_input': st.session_state["reserve_factor_input"],
        'shifts_count': st.session_state["shifts_count"],
        'ratio_supervisor': st.session_state["ratio_supervisor"],
        'ratio_assistant_head': st.session_state["ratio_assistant_head"],
    }
    
    # 2. منطقة إدخال المعايير لجميع الإدارات
    st.subheader("1. ضبط معايير الاحتساب لجميع الإدارات")
    
    # تعريف قواميس لتخزين مدخلات المستخدم
    user_settings = {}
    
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
                    
                    user_settings[name] = {}
                    
                    with col:
                        st.markdown(f"***_{name}_***")
                        
                        # --- معيار الاحتساب (المتواجدين/التدفق) ---
                        default_crit = dept.get('default_criterion', 'Present')
                        criterion_options = ['المتواجدين (حجم)', 'التدفق اليومي (حركة)']
                        
                        criterion_choice_text = st.radio(
                            "المعيار", 
                            options=criterion_options,
                            index=0 if default_crit == 'Present' else 1,
                            key=f"all_crit_{name}_{i}"
                        )
                        user_settings[name]['criterion'] = 'Present' if criterion_choice_text == criterion_options[0] else 'Flow'

                        # --- نسبة التغطية (لكل ما يعتمد على عدد الحجاج) ---
                        if dept_type in ['Ratio', 'Time']:
                            default_cov = dept.get('default_coverage', 100)
                            coverage_val = st.number_input(
                                "نسبة تغطية (%)", 
                                min_value=0, max_value=100, 
                                value=default_cov, 
                                step=1, 
                                key=f"all_cov_{name}_{i}"
                            )
                            user_settings[name]['coverage'] = coverage_val / 100

                        # --- إدخال معيار الاحتساب (Ratio/Time/Bus) ---
                        if dept_type == 'Ratio':
                            default_ratio = dept['default_ratio']
                            user_settings[name]['ratio'] = st.number_input("المعيار (وحدة/موظف)", min_value=1, value=default_ratio, key=f"all_ratio_{name}_{i}")
                            
                        elif dept_type == 'Time':
                            default_time = dept['default_time']
                            user_settings[name]['time'] = st.number_input("المعيار (دقيقة/وحدة)", min_value=0.5, value=default_time, step=0.1, key=f"all_time_{name}_{i}")
                            user_settings[name]['events_multiplier'] = st.number_input("معامل أحداث الحاج (x)", min_value=1, value=2, key=f"all_mult_{name}_{i}")
                            
                        elif dept_type == 'Bus_Ratio':
                            default_bus_count = 20
                            default_bus_ratio = dept['default_ratio']
                            user_settings[name]['bus_count'] = st.number_input("عدد الحافلات المتوقع", min_value=1, value=default_bus_count, key=f"all_bus_count_{name}_{i}")
                            user_settings[name]['ratio'] = st.number_input("المعيار (حافلة/موظف)", min_value=1, value=default_bus_ratio, key=f"all_bus_ratio_{name}_{i}")
            
            st.markdown("---")
            calculate_button = st.form_submit_button("🔄 احتساب وعرض النتائج الموحدة", type="primary")

    # 3. الحساب والعرض (يتم عند الضغط على زر الاحتساب داخل النموذج)
    if calculate_button:
        st.success("✅ جاري بدء الحساب الموحد بناءً على معاييرك المخصصة...")
        
        # استخراج المدخلات العامة
        num_hajjaj_present = sidebar_inputs['num_hajjaj_present']
        num_hajjaj_flow = sidebar_inputs['num_hajjaj_flow']
        service_days = sidebar_inputs['service_days']
        staff_work_hours_day = sidebar_inputs['staff_hours']
        reserve_factor = sidebar_inputs['reserve_factor_input'] / 100
        shifts_count = sidebar_inputs['shifts_count']
        ratio_supervisor = sidebar_inputs['ratio_supervisor']
        ratio_assistant_head = sidebar_inputs['ratio_assistant_head']

        hajjaj_data = {'Present': num_hajjaj_present, 'Flow': num_hajjaj_flow}

        all_results = []
        total_staff_needed = 0

        # عملية الحساب لجميع الإدارات باستخدام مدخلات المستخدم
        for dept_name, dept_info in ALL_DEPARTMENTS_FLAT.items():
            
            dept_type = dept_info['type']
            settings = user_settings[dept_name] # مدخلات المستخدم للإدارة الحالية
            
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
                
                # استخدام معامل الأحداث من مدخلات المستخدم
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
            st.info(f"نسبة الاحتياط الإجمالية المطبقة: {sidebar_inputs['reserve_factor_input']}%")
    else:
        st.info("⬆️ يرجى إدخال أو مراجعة معايير الاحتساب ثم الضغط على زر **'احتساب وعرض النتائج الموحدة'** في نهاية الصفحة.")
