import streamlit as st
from test2 import ask_question, get_drug_info



if "step" not in st.session_state:
    st.session_state.step = 1

if "drug_name" not in st.session_state:
    st.session_state.drug_name = ""

if "route" not in st.session_state:
    st.session_state.route = None


# عنوان الصفحة
st.set_page_config(page_title="PDF Chatbot", page_icon="🤖")
st.title(" Medical PDF Chatbot")

if st.session_state.step == 1:
    st.subheader("Step 1: Enter drug name")

    drug = st.text_input("Drug name:")

    if st.button("Next"):
        if drug.strip() == "":
            st.warning("Please enter a drug name.")
        else:
            st.session_state.drug_name = drug
            st.session_state.step = 2
            st.rerun()
elif st.session_state.step == 2:
    st.subheader(f"Drug information: {st.session_state.drug_name}")

    with st.spinner("Searching medical PDF..."):
        info = get_drug_info(st.session_state.drug_name)

    # ---- Indication ----
    st.markdown("### Indication")
    st.write(info.get("indication", "Not found in reference"))

    # ---- Pediatric dose ----
    st.markdown("### Pediatric dose (from reference)")
    st.write(info.get("dose", "Not found in reference"))

    # ---- Maximum dose ----
    st.markdown("### Maximum recommended dose")
    st.write(info.get("max_dose", "Not found in reference"))

    st.divider()

    # ---- Route of administration ----
    routes = info.get("routes", [])

    if routes:
        st.markdown("### Route of administration")
        st.session_state.route = st.radio(
            "Select route:",
            routes
        )
    else:
        st.warning(
            "Route of administration is not clearly specified "
            "in the reference."
        )
        st.session_state.route = "Not specified"

    st.info(
        "Please review the dosing information and route carefully "
        "before proceeding."
    )

    # ---- Proceed ----
    if st.button("Continue to weight input"):
        st.session_state.step = 3
        st.rerun()




## child weight:
if "weight" not in st.session_state:
    st.session_state.weight = None
elif st.session_state.step == 3:
    st.subheader("Step 3: Child weight")

    weight = st.number_input(
        "Enter child weight (kg):",
        min_value=0.5,
        max_value=150.0,
        step=0.5
    )

    if st.button("Next"):
        if weight <= 0:
            st.warning("Please enter a valid weight.")
        else:
            st.session_state.weight = weight
            st.session_state.step = 4
            st.rerun()



## interval :
if "frequency" not in st.session_state:
    st.session_state.frequency = None
elif st.session_state.step == 4:
    st.subheader("Step 4: Number of doses per day")

    frequency = st.radio(
        "Select dosing frequency:",
        options=[1, 2, 3, 4],
        format_func=lambda x: f"{x} time(s) per day"
    )

    st.info(
        "Example:\n"
        "- 1 time/day → once daily\n"
        "- 2 times/day → every 12 hours\n"
        "- 3 times/day → every 8 hours\n"
        "- 4 times/day → every 6 hours"
    )

    if st.button("Next"):
        st.session_state.frequency = frequency
        st.session_state.step = 5
        st.rerun()


## drug conc.:
if "concentration" not in st.session_state:
    st.session_state.concentration = None
elif st.session_state.step == 5:
    st.subheader("Step 5: Drug concentration")

    concentration = st.text_input(
        "Enter drug concentration (e.g. 125 mg / 5 ml):"
    )

    if st.button("Calculate dose"):
        if concentration.strip() == "":
            st.warning("Please enter the drug concentration.")
        else:
            st.session_state.concentration = concentration
            st.session_state.step = 6
            st.rerun()

elif st.session_state.step == 6:
    st.subheader("Step 6: Dose calculation")

    # parse dose from Step 2 text
    dose_info = parse_dose_text(info.get("dose", ""))

    if not dose_info["values"] or dose_info["unit_type"] == "unknown":
        st.error("Unable to parse dose from reference.")
        st.stop()

    # choose dose value
    if len(dose_info["values"]) == 2:
        dose_value = st.slider(
            "Select dose (mg/kg):",
            min_value=dose_info["values"][0],
            max_value=dose_info["values"][1],
            step=1.0
        )
    else:
        dose_value = dose_info["values"][0]
        st.info(f"Using dose: {dose_value} mg/kg")

    # parse concentration
    mg_per_ml = parse_concentration(st.session_state.concentration)
    if not mg_per_ml:
        st.error("Invalid concentration format.")
        st.stop()

    result = calculate_dose(
        weight=st.session_state.weight,
        dose_value=dose_value,
        unit_type=dose_info["unit_type"],
        frequency=st.session_state.frequency,
        mg_per_ml=mg_per_ml
    )

    if not result:
        st.error("Dose calculation failed.")
        st.stop()

    # ---- Results ----
    st.markdown("### Calculated dose")
    st.write(f"- **Route:** {st.session_state.route}")
    st.write(f"- **Total daily dose:** {result['mg_day']} mg/day")
    st.write(f"- **Dose per administration:** {result['mg_dose']} mg")
    st.success(f"➡️ **Give {result['ml_dose']} ml per dose**")

    # ---- Safety (simple) ----
    max_text = info.get("max_dose", "").lower()
    max_match = re.search(r"(\d+(?:\.\d+)?)\s*mg", max_text)
    if max_match and result["mg_day"] > float(max_match.group(1)):
        st.warning("⚠️ Calculated dose exceeds maximum recommended dose.")
