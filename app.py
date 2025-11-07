# ... (داخل دالة all_departments_page)

        for i, center in enumerate(centers_to_display):
            center_id = center['id']
            
            # 💡 التعديل الرئيسي: تبسيط عنوان Expander إلى اسم المركز فقط
            with st.expander(f"مركز الضيافة #{center_id}: {center['name']}", expanded=True): 
                
                # إبقاء تصميم الأعمدة السابق
                # نستخدم st.session_state مباشرة لقراءة قيمة الاسم الحالي لتجنب الريرن غير الضروري
                current_name = st.session_state.get(f"hosp_name_{center_id}", center.get('name', f'مركز ضيافة #{center_id}'))
                
                col_status, col_name, col_hajjaj, col_remove = st.columns([1.5, 3, 2.5, 1])
                
                # 1. زر الإغلاق/الفتح (Toggle)
                new_active = col_status.toggle(
                    "مفعل", 
                    value=center.get('active', True), 
                    key=f"hosp_active_{center_id}"
                )
                st.session_state.dynamic_hospitality_centers[i]['active'] = new_active

                # 2. اسم المركز
                # 💡 استخدام label_visibility="collapsed" لحل مشكلة التداخل في لقطة الشاشة
                new_name = col_name.text_input(
                    "اسم المركز", 
                    value=center.get('name', f'مركز ضيافة #{center_id}'), 
                    key=f"hosp_name_{center_id}",
                    label_visibility="visible" # أبقيتها visible للتجربة، إذا تداخلت نحولها إلى collapsed
                )
                # ... (بقية المدخلات بنفس الطريقة) ...
