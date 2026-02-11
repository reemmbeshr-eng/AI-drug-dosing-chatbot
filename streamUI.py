import streamlit as st
from new_clean2 import DosageLogic 

st.set_page_config(page_title="Smart Dosage Assistant", layout="wide", page_icon="💊")


def get_logic():
    obj = DosageLogic('D:\\AI diploma\\new\\IV Drugs.xlsx')
    obj.load_data()
    return obj

logic = get_logic()

st.title("Pediatrics IV Drugs Dosage Assistant")


if 'final_drug_name' not in st.session_state:
    st.session_state.final_drug_name = ""

col_search, col_img = st.columns([2, 1])

with col_search:
    manual_name = st.text_input("🔍 Search Drug Name:", placeholder="Type name here...", key="manual_input")
    if manual_name:
        st.session_state.final_drug_name = manual_name

with col_img:
    uploaded_file = st.file_uploader("📷 Or upload photo", type=['jpg', 'png', 'jpeg'])
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Image", width=150)

    if st.button("🔍 Identify Medication", key="trigger_ai_btn"):
        with st.spinner("AI is reading label..."):
            st.session_state.final_drug_name = ""
                
                image_bytes = uploaded_file.getvalue()
                identified_name = logic.identify_drug_from_image(image_bytes)
                
                if identified_name:
                    st.session_state.final_drug_name = identified_name
                    st.success(f"Detected: **{identified_name}**")
                    st.rerun() # إجبار التطبيق على التحديث فوراً

drug_name_input = st.session_state.final_drug_name

if drug_name_input:
    results = logic.search_drug(drug_name_input)
    
    if not results.empty:
        drug_info = results.iloc[0]
        sections = logic.parse_indications(drug_info['Indication and Dosage'])
        st.success(f"✅ Found: **{drug_info['Generic Name']}**")

        for title, content in sections.items():
           
            st.subheader(f"📍 {title}") 
            
            with st.container():
                st.markdown(content)
    
    
            
            with st.expander(f"🔢 Dosage Calculation Flow for {title}"):
                
                # --- Step 1: Renal Check & Dose Parameters ---
                st.markdown("#### Step 1: Dose Parameters")
                
                requires_renal = str(drug_info.get('renal adjustment', 'No')).strip().lower()
                
                if requires_renal == 'yes':
                    renal_check = st.radio(
                        "This drug requires **Renal Adjustment**. Apply it?", 
                        ["No", "Yes"], key=f"renal_{title}", horizontal=True
                    )
                else:
                    renal_check = "No"
                    st.info("ℹ️ No standard renal adjustment required.")

                adjustment_factor = 100.0
                
                if renal_check == "Yes":
                    st.warning("⚠️ **Renal Adjustment Instructions:**")
                    raw_renal_info = str(drug_info.get('renal adjustment dose', 'Consult guidelines.'))
                    # تنسيق النص ليبدأ كل GFR في سطر جديد
                    formatted_renal_info = raw_renal_info.replace("GFR", "\n\n**GFR**")
                    st.markdown(formatted_renal_info)
                    
                    st.markdown("---")
                    adjustment_factor = st.number_input(
                        "Enter percentage of dose to give (%)", 
                        min_value=1.0, max_value=100.0, value=50.0, key=f"factor_{title}"
                    )

                col1, col2 = st.columns(2)
                with col1:
                    weight = st.number_input(f"Weight (kg)", min_value=0.1, value=10.0, format="%.2f", key=f"w_{title}")
                    concentration = st.number_input(f"Available Conc. (mg/ml)", min_value=0.1, value=100.0, format="%.2f", key=f"c_{title}")
                with col2:
                    dosage_unit = st.selectbox("Unit:", ["mg/kg/day", "mg/kg/dose"], key=f"unit_{title}")
                    dose_value = st.number_input("Standard Dose Value:", min_value=1.0, value=50.0, format="%.2f", key=f"val_{title}")
                    frequency = st.selectbox("Frequency:", ["Every 6 hours", "Every 8 hours", "Every 12 hours", "Every 24 hours"], key=f"freq_{title}")

                if st.button(f"🚀 Calculate Dose", key=f"btn_dose_{title}"):
                    st.session_state[f"dose_done_{title}"] = True

                if st.session_state.get(f"dose_done_{title}", False):
                    calc_result = logic.calculate_dosage(weight, dose_value, dosage_unit, frequency, concentration)
                    
                    if calc_result:
                        final_mg = calc_result['mg_per_dose'] * (adjustment_factor / 100.0)
                        final_ml = final_mg / concentration
                        st.session_state[f"final_mg_{title}"] = final_mg 
                        
                        st.subheader("📊 Dose Result")
                        st.success(f"✅ **Dose: {final_mg:.2f} mg ({final_ml:.2f} ml)**")
                        
                        st.divider()
                        
                        # --- Step 2: Dilution ---
                        st.markdown("#### Step 2: Dilution & Preparation")
                        if st.button(f"🧪 Show Dilution Guidelines", key=f"btn_dilute_data_{title}"):
                            st.session_state[f"show_dilute_{title}"] = True
                        
                        if st.session_state.get(f"show_dilute_{title}", False):
                            dilution_info = drug_info.get('Preparation for administration', 'No data recorded')
                            st.warning(f"**Reference Guideline:**\n\n{dilution_info}")
                            
                            target_conc = st.number_input("Enter desired Final Concentration (mg/ml):", min_value=0.1, value=20.0, format="%.2f", key=f"target_{title}")
                            
                            if st.button(f"🔢 Calculate Final Volume", key=f"btn_final_calc_{title}"):
                                st.session_state[f"final_done_{title}"] = True
                            
                            if st.session_state.get(f"final_done_{title}", False):
                                final_infusion_vol = st.session_state[f"final_mg_{title}"] / target_conc
                                st.success(f"💡 **Final Infusion Volume:** Dilute to a total of **{final_infusion_vol:.2f} ml**")
                                
                                st.divider()
                                # --- Step 3: Administration ---
                                st.markdown("#### Step 3: Administration Method")
                                admin_info = drug_info.get('Administration', 'No data recorded')
                                st.info(f"📌 **Method:** {admin_info}")
            st.divider()
    else:
        st.error("❌ Drug not found.")