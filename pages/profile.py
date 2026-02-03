import streamlit as st

def render():
    """Profile Page: Welcome Survey"""
    rc = st.session_state.get('reset_count', 0)
    
    # Load persisted values
    def_name = st.session_state.get('name', "Freddy Mercury")
    def_age = st.session_state.get('age', 0)
    def_target = st.session_state.get('target_retirement', 65)
    def_savings = st.session_state.get('current_savings', 0.00)
    cpp_stored = st.session_state.get('cpp_contribution', "Yes")
    cpp_idx = 0 if cpp_stored == "Yes" else 1

    # Name Input
    name = st.text_input("Name", value=def_name, key=f"name_input_{rc}")

    # Age and Retirement Age (side by side)
    col1, col2 = st.columns(2)
    with col1:
        age_val = st.number_input("Age", min_value=0, value=def_age, step=1, key=f"age_input_{rc}")
    with col2:
        target_ret_val = st.number_input("Retirement Age", min_value=0, value=def_target, step=1, key=f"target_ret_input_{rc}")

    # Current Total Savings
    savings_val = st.number_input("Current Total Savings", min_value=0.00, value=def_savings, step=1000.0, format="%.2f", key=f"savings_input_{rc}")
    
    # CPP Contribution Toggle
    cpp_toggle = st.radio("CPP Contribution", ["Yes", "No"], index=cpp_idx, horizontal=True, key=f"cpp_contrib_input_{rc}")

    st.markdown("###")
    
    # Calibrate & Continue Button
    if st.button("Calibrate & Continue", type="primary", key=f"calibrate_btn_{rc}"):
        # Save to session state
        st.session_state['name'] = name
        st.session_state['age'] = age_val
        st.session_state['target_retirement'] = target_ret_val
        st.session_state['current_savings'] = savings_val
        st.session_state['cpp_contribution'] = cpp_toggle
        
        # Background calculations
        st.session_state['oas_benefit'] = 728
        st.session_state['cpp_benefit'] = 804 if cpp_toggle == "Yes" else 0
        st.session_state['max_age'] = 100
        
        # Navigate to financial data page
        st.switch_page("pages/financial_data.py")

# Auto-run when page is loaded
render()
