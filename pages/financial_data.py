import streamlit as st

def render():
    """Financial Data Page: Phase Header"""
    age = st.session_state.get('age', 0)
    
    # Determine phase based on age
    if age < 55:
        phase_title = "Build"
        phase_message = "You are in the Build phase. Let's get you set up right and make sure you know how much you should be saving."
    elif 55 <= age < 65:
        phase_title = "Optimize"
        phase_message = "You are in the Optimize phase. Let's make sure everything's set up right and that you know you'll have enough."
    elif 65 <= age < 75:
        phase_title = "Enjoyment"
        phase_message = "You are in the Enjoyment phase. Let's find out how much fun you can have."
    else:  # 75+
        phase_title = "Legacy"
        phase_message = "You are in the Legacy phase. Let's make sure everything is set up right."
    
    # Phase header
    st.markdown(f"<h2 style='text-align: center; font-size: 2.5em;'>{phase_title}</h2>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center; color: #555;'>{phase_message}</h3>", unsafe_allow_html=True)
    st.markdown("###")
    
    # Phase tip cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**{phase_title} Phase Tip #1**\n\nPlaceholder content.")
    with col2:
        st.info(f"**{phase_title} Phase Tip #2**\n\nPlaceholder content.")
    with col3:
        st.info(f"**{phase_title} Phase Tip #3**\n\nPlaceholder content.")

# Auto-run when page is loaded
render()
