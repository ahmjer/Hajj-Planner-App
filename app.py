# ... (استمرار الكود السابق)

# -------------------------------------------------------------------
# 4. منطق الشاشة الموحدة الجديدة (All Departments Page Logic)
# -------------------------------------------------------------------

def all_departments_page():
    st.title("📊 مخطط القوى العاملة الموحد")
    st.markdown("---")
    
    st.subheader("1. ضبط معايير الاحتساب لجميع الإدارات")
    
    # ... (كود تهيئة user_settings)
    
    # --- إدارة المراكز الديناميكية (خارج النموذج) ---
    st.markdown("#### 🏷️ الضيافة")
    with st.container():
        st.button("➕ إضافة مركز ضيافة جديد", on_click=add_hospitality_center, type="secondary", key="add_hosp_center_btn")
        st.markdown("---") 
        
        # 💡 التصحيح الرابع: إذا تم تعديل القائمة، قم بإعادة التشغيل واخرج فورًا.
        if st.session_state.get('center_list_modified', False):
            st.warning("جاري تحديث قائمة المراكز... يرجى الانتظار.")
            st.session_state['center_list_modified'] = False
            st.rerun()

        # إذا لم يكن هناك تعديل، نستمر في العرض
        with st.container(border=True): # (تم التخلص من st.empty)
            st.markdown("**مراكز الضيافة الديناميكية (إدارة الإغلاق/الفتح وتحديد الحجاج)**")
            
            # 🛑 التصحيح النهائي: إنشاء نسخة ثابتة من القائمة للتكرار
            # هذا يمنع أي تغييرات تحدث أثناء Rerun من التأثير على حلقة for الجارية.
            centers_to_display = st.session_state.dynamic_hospitality_centers[:]
            
            for i, center in enumerate(centers_to_display):
                center_id = center['id']
                
                expander_title_label = f"مركز ضيافة #{center_id}"
                expander_title_key = f"hosp_expander_key_{center_id}"
                
                # السطر الذي يسبب الخطأ (الآن محمي بـ centers_to_display)
                # يجب أن يكون المفتاح ثابتاً ويعتمد فقط على ID المركز
                with st.expander(expander_title_label, expanded=True, key=expander_title_key): 
                    
                    # ... (بقية منطق العرض الداخلي)
                    
                    # ملاحظة: يجب أن نستخدم حلقة البحث للعثور على الفهرس الصحيح في القائمة الأصلية dynamic_hospitality_centers 
                    # للتأكد من أننا نحدث العنصر الصحيح في حالة الجلسة.
                    
                    # بحث عن الفهرس الأصلي في قائمة session_state
                    original_index = next((j for j, c in enumerate(st.session_state.dynamic_hospitality_centers) if c['id'] == center_id), None)
                    
                    if original_index is not None:
                    
                        # عرض الاسم الفعلي للمركز بخط أغمق وفي المنتصف
                        current_name = st.session_state.get(f"hosp_name_{center_id}", center.get('name', f'مركز ضيافة #{center_id}'))
                        st.markdown(f'<h4 style="text-align: center; font-weight: 700; color: #800020;">{current_name}</h4>', unsafe_allow_html=True)
                        
                        # إبقاء تصميم الأعمدة السابق
                        col_status, col_name, col_hajjaj, col_remove = st.columns([1.5, 3, 2.5, 1])
                        
                        # 1. زر الإغلاق/الفتح (Toggle)
                        new_active = col_status.toggle(
                            "مفعل", 
                            value=center.get('active', True), 
                            key=f"hosp_active_{center_id}",
                            label_visibility="visible"
                        )
                        st.session_state.dynamic_hospitality_centers[original_index]['active'] = new_active

                        # 2. اسم المركز
                        new_name = col_name.text_input(
                            "اسم المركز", 
                            value=center.get('name', f'مركز ضيافة #{center_id}'), 
                            key=f"hosp_name_{center_id}",
                            label_visibility="visible"
                        )
                        st.session_state.dynamic_hospitality_centers[original_index]['name'] = new_name

                        # 3. عدد حجاج المركز
                        new_hajjaj_count = col_hajjaj.number_input(
                            "عدد الحجاج/الزوار (تقديري)",
                            min_value=1, 
                            value=center.get('hajjaj_count', st.session_state['num_hajjaj_present']), 
                            step=100, 
                            key=f"hosp_hajjaj_{center_id}",
                            label_visibility="visible"
                        )
                        st.session_state.dynamic_hospitality_centers[original_index]['hajjaj_count'] = new_hajjaj_count
                        
                        # 4. زر الإزالة
                        col_remove.markdown("<div style='margin-top: 29px;'>", unsafe_allow_html=True)
                        col_remove.button(
                            "🗑️ إزالة", 
                            on_click=remove_hospitality_center, 
                            args=(center_id,), 
                            key=f"hosp_remove_{center_id}"
                        )
                        col_remove.markdown("</div>", unsafe_allow_html=True)

        
        st.markdown("---")
        
        # ... (بقية الكود الخاص بالـ Form والمعايير)
