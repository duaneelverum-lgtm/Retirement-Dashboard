import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import json
import os
from datetime import datetime
import zipfile
import io
from fpdf import FPDF

# --- Configuration ---
st.set_page_config(
    page_title="The Retirement Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Use absolute path relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "finance.json")
DEMO_MODE = True  # Set to True for User Testing Deployment to disable saving

# Ensure data dir exists
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)


# --- Data Handling ---
def load_data():
    try:
        if os.path.exists(DATA_FILE):
             with open(DATA_FILE, "r") as f:
                 return json.load(f)
    except Exception as e:
        print(f"Error loading data: {e}")

    # Fallback to empty structure
    return {
        "accounts": [],
        "transactions": [],
        "history": [],
        "personal": {},
        "budget": [],
        "annual_expenditures": [],
        "government": {},
        "inheritance": {},
        "scenarios": []
    }

# Custom Metric Display to prevent truncation
def display_custom_metric(label, value, delta=None, help_text=None):
    delta_html = ""
    if label is None or str(label).lower() == "undefined":
        label = "Net Worth"
    if delta:
        # Determine color based on content
        color = "#007a33" # Green
        bg_color = "#e6f4ea"
        if "-" in str(delta) and "benefit" not in label.lower() and "income" not in label.lower():
             color = "#d93025" # Red
             bg_color = "#fce8e6"
        
        delta_html = f'<div style="background-color: {bg_color}; color: {color}; display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.85rem; margin-top: 4px;">{delta}</div>'

    st.markdown(f"""
    <div style="margin-bottom: 2px; width: 100%;">
        <div style="font-size: 14px; font-weight: bold; color: rgba(49, 51, 63, 0.8); margin-bottom: 2px; font-family: 'Source Sans Pro', sans-serif;">{label}</div>
        <div style="font-size: 25px; font-weight: bold; color: rgb(49, 51, 63); line-height: 1.1; word-wrap: break-word; font-family: 'Source Sans Pro', sans-serif;">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

# Global custom CSS for premium "frames"
st.markdown("""
<style>
    /* Styling for st.container(border=True) to look like premium dashboard cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff !important;
        border: 1px solid #f0f2f6 !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02), 0 1px 2px rgba(0, 0, 0, 0.04) !important;
        padding: 20px !important;
        margin-bottom: 15px !important;
    }
    
    /* Remove nested borders and padding around Plotly charts */
    [data-testid="stPlotlyChart"] {
        border: none !important;
        padding: 0 !important;
    }
</style>
""", unsafe_allow_html=True)



def save_data(data):
    if DEMO_MODE:
        # In demo mode, save to session state instead of file
        st.session_state["finance_data"] = data
        return
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_net_worth(data):
    total_assets = 0.0
    total_liabilities = 0.0
    liquid_nw = 0.0
    
    for acc in data["accounts"]:
        b = acc.get("balance", 0.0)
        t = acc.get("type", "")
        
        # Calculate Logic
        is_liability = (t in ["Liability", "Credit Card", "Loan", "Mortgage"]) or (b < 0)
        
        if is_liability:
            debt = abs(b)
            total_liabilities += debt
            # Subtract from Liquid Net Worth logic
            liquid_nw -= debt
        else:
            total_assets += b
            # Add to Liquid NW only if Bank or Investments
            if t in ["Bank", "Investments"]:
                liquid_nw += b

    return liquid_nw, total_assets, total_liabilities

def get_cpp_estimate(age):
    """Returns approximate average monthly CPP based on start age (2025 guidelines)."""
    # 2025 Average for new recipients at age 65 is approx $803.76
    base_65 = 803.76
    if age < 65:
        # Reduction of 0.6% per month (7.2% per year)
        factor = 1.0 - (65 - age) * 0.072
        return round(base_65 * factor, 2)
    elif age > 65:
        # Increase of 0.7% per month (8.4% per year)
        factor = 1.0 + (age - 65) * 0.084
        return round(base_65 * factor, 2)
    return base_65

def get_oas_estimate(age):
    """Returns approximate average monthly OAS based on start age (2025 guidelines)."""
    # 2025 Standard amount for 65-74 is approx $727.67
    base_65 = 727.67
    if age > 65:
        # Increase of 0.6% per month (7.2% per year)
        factor = 1.0 + (age - 65) * 0.072
        return round(base_65 * factor, 2)
    return base_65

# --- Callbacks for Profile Autofill ---
def update_cpp_amt():
    age = st.session_state.p_cpp_start_new
    st.session_state.p_cpp_amt_direct = get_cpp_estimate(age)

def update_oas_amt():
    age = st.session_state.p_oas_start_new
    st.session_state.p_oas_amt_direct = get_oas_estimate(age)

# --- UI Components ---
def create_project_backup():
    """Creates a zip file of the current project directory, excluding venv and junk."""
    buffer = io.BytesIO()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Go up one level to zip the whole project folder (FinancialDashboard)
    # Actually, current running dir should be project root if launched correctly.
    # Cwd is /Users/Home/Documents/FinancialDashboard
    
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk("."):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in ["venv", "__pycache__", ".git", ".gemini", ".DS_Store"]]
            
            for file in files:
                if file == ".DS_Store" or file.endswith(".zip") or file.endswith(".pyc"):
                    continue
                    
                file_path = os.path.join(root, file)
                # Store in zip with relative path
                zip_file.write(file_path, arcname=file_path)
                
    buffer.seek(0)
    return buffer, f"financial_dashboard_backup_{timestamp}.zip"

def sanitize_for_pdf(text):
    """Sanitizes text to ensure it is compatible with FPDF (Latin-1)."""
    if text is None:
        return ""
    text = str(text)
    # Replace common incompatible characters
    replacements = {
        "•": "-",
        "–": "-",
        "—": "-",
        "’": "'",
        "“": '"',
        "”": '"',
        "…": "..."
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
        
    # Standardize to Latin-1, replacing unsupported chars (like emojis) with ?
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- HELPER: Chart Generation Functions ---
def get_net_worth_history_fig(data, net_worth):
    """Generates the Net Worth History Figure."""
    if data["history"]:
        df_hist_g = pd.DataFrame(data["history"])
        df_hist_g['date'] = pd.to_datetime(df_hist_g['date'])
        df_hist_g['date_label'] = df_hist_g['date'].dt.strftime('%b %Y')
        
        current_value_g = net_worth
        max_val_in_data = max(current_value_g, df_hist_g['net_worth'].max()) if not df_hist_g.empty else current_value_g
        target_million = float(((int(max_val_in_data) // 1000000) + 1) * 1000000)
        y_min = 0
        y_max = target_million * 1.1

        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(
            x=df_hist_g['date_label'],
            y=df_hist_g['net_worth'],
            mode='lines+markers',
            fill='tozeroy',
            line=dict(color='#0068c9', width=3),
            marker=dict(size=12, color='#0068c9'),
            fillcolor='rgba(0, 104, 201, 0.2)',
        ))
        
        fig_hist.update_layout(
            title="Net Worth Over Time",
            xaxis_title="Date",
            yaxis_title="Net Worth",
            yaxis_tickformat='$,.0f',
            yaxis_range=[y_min, y_max],
            title_font=dict(size=20, color='#31333F'),
            font=dict(family="sans-serif", size=12, color="#31333F"),
            margin=dict(l=40, r=40, t=60, b=40),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig_hist
    return None

def get_projection_fig(years_axis, history_bal, current_age, max_years, y_max_proj, y_dtick, custom_ticks, 
                       planned_ret_age, is_retired, cpp_start, oas_start, inh_age, inh_amt):
    """Generates the Projection Figure."""
    fig_proj = px.line(x=years_axis, y=history_bal, labels={'x': 'Age', 'y': 'Net Worth'})
    fig_proj.update_layout(
        title="Retirement Projection",
        yaxis=dict(range=[0, y_max_proj], tickformat='$,.0f', dtick=y_dtick),
        xaxis=dict(
            range=[current_age, current_age + max_years],
            tickvals=custom_ticks,
            tickmode='array',
            tickangle=0
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        font=dict(size=12),
        height=550,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    # Annotations
    if not is_retired and planned_ret_age > current_age and planned_ret_age <= (current_age + max_years):
        fig_proj.add_vline(x=planned_ret_age, line_width=2, line_dash="solid", line_color="#ff2b2b", annotation_text="Retire", annotation_position="top left", annotation=dict(y=0.85))

    if cpp_start > current_age and cpp_start <= (current_age + max_years):
        fig_proj.add_vline(x=cpp_start, line_width=1, line_dash="dash", line_color="#21c354", annotation_text="CPP", annotation_position="top left", annotation=dict(y=0.90))
        
    if oas_start > current_age and oas_start <= (current_age + max_years):
            fig_proj.add_vline(x=oas_start, line_width=1, line_dash="dash", line_color="#21c354", annotation_text="OAS", annotation_position="top left", annotation=dict(y=0.95))

    if inh_amt > 0 and inh_age > current_age and inh_age <= (current_age + max_years):
        fig_proj.add_vline(x=inh_age, line_width=1, line_dash="dash", line_color="#a855f7", annotation_text="Inheritance", annotation_position="top right", annotation=dict(y=0.95))
        
    return fig_proj

def run_financial_simulation(
    current_age,
    principal,
    monthly_income,
    monthly_expenses,
    annual_return,
    inflation,
    planned_ret_age,
    gov_data,
    inheritance_data,
    annual_expenditures,
    scenarios=None,
    max_years=60,
    fill_zeros=False
):
    import math
    
    bal = float(principal)
    # Convert percentages to decimals
    curr_return = float(annual_return)
    curr_inflation = float(inflation)
    
    # Setup
    history_bal = [bal]
    age_axis = [float(current_age)]
    
    c_inc = float(monthly_income)
    c_exp = float(monthly_expenses)
    
    cpp_start_age = gov_data.get("cpp_start_age", 65)
    cpp_amount = gov_data.get("cpp_amount", 0.0)
    oas_start_age = gov_data.get("oas_start_age", 65)
    oas_amount = gov_data.get("oas_amount", 0.0)
    
    inh_age = inheritance_data.get("age", 0)
    inh_amt = inheritance_data.get("amount", 0.0)
    inh_type = inheritance_data.get("type", "Cash / Investments")
    inh_sell = inheritance_data.get("sell_property", False)
    inh_sell_age = inheritance_data.get("sell_age", 0)
    
    months_survived = 0
    ran_out = False
    
    total_months = max_years * 12
    
    for m in range(1, total_months + 1):
        months_survived = m
        age_mo = (current_age * 12) + m
        age_yr = age_mo / 12.0
        
        eff_inc = c_inc
        # Salary Stop Logic
        if float(planned_ret_age) > float(current_age) and age_yr >= float(planned_ret_age):
            eff_inc = 0.0
            
        # Pensions
        if age_mo >= (cpp_start_age * 12): eff_inc += cpp_amount
        if age_mo >= (oas_start_age * 12): eff_inc += oas_amount
        
        # Inheritance
        if inh_age > 0 and inh_amt > 0:
            if inh_type == "Cash / Investments" and age_mo == (inh_age * 12):
                bal += inh_amt
            elif inh_type == "Property / House" and inh_sell and age_mo == (inh_sell_age * 12):
                bal += inh_amt
                
        # Scenarios
        if scenarios:
             for ev in scenarios:
                e_age = ev.get("age", 0)
                e_impact = ev.get("impact", 0)
                e_ret = ev.get("sc_return", 0)
                e_inf = ev.get("sc_inflation", 0)
                e_type = ev.get("type", "Cost")
                e_freq = ev.get("frequency", "One-time")
                
                is_trigger = False
                if e_freq == "One-time": is_trigger = (age_mo == (e_age * 12))
                elif e_freq in ["Monthly", "Until End of Plan"]: is_trigger = (age_mo >= (e_age * 12))
                elif e_freq == "Annually": is_trigger = (age_mo >= (e_age * 12)) and ((age_mo - (e_age * 12)) % 12 == 0)
                elif e_freq == "Twice per year": is_trigger = (age_mo >= (e_age * 12)) and ((age_mo - (e_age * 12)) % 6 == 0)
                elif e_freq == "Every 2 years": is_trigger = (age_mo >= (e_age * 12)) and ((age_mo - (e_age * 12)) % 24 == 0)
                elif e_freq == "Every 3 years": is_trigger = (age_mo >= (e_age * 12)) and ((age_mo - (e_age * 12)) % 36 == 0)
                elif e_freq == "Every 5 years": is_trigger = (age_mo >= (e_age * 12)) and ((age_mo - (e_age * 12)) % 60 == 0)
                elif e_freq == "Every 10 years": is_trigger = (age_mo >= (e_age * 12)) and ((age_mo - (e_age * 12)) % 120 == 0)
                
                if is_trigger:
                    if e_type in ["Financial Gain", "Income", "Asset"]:
                        if e_freq == "One-time": bal += e_impact
                        else: eff_inc += e_impact
                    else: # Cost
                        if e_freq == "One-time": bal -= abs(e_impact)
                        else: eff_inc -= abs(e_impact)
                    
                    if e_ret > 0: curr_return = e_ret
                    if e_inf > 0: curr_inflation = e_inf

        # Interest & Cashflow
        interest = bal * (curr_return / 100 / 12)
        bal += interest
        bal += (eff_inc - c_exp)
        
        # Annual Expenditures
        if m % 12 == 1:
            age_floor = int(age_yr)
            for exp in annual_expenditures:
                 e_amt = float(exp.get("amount", 0.0))
                 e_freq = exp.get("frequency", "One-time")
                 e_start = int(exp.get("start_age", 65))
                 
                 should_apply = False
                 if e_freq == "One-time" and age_floor == e_start: should_apply = True
                 elif e_freq == "Every Year" and age_floor >= e_start: should_apply = True
                 elif e_freq == "Every 2 Years" and age_floor >= e_start and (age_floor - e_start) % 2 == 0: should_apply = True
                 elif e_freq == "Every 5 Years" and age_floor >= e_start and (age_floor - e_start) % 5 == 0: should_apply = True
                 elif e_freq == "Every 10 Years" and age_floor >= e_start and (age_floor - e_start) % 10 == 0: should_apply = True
                 
                 if should_apply:
                     bal -= e_amt

        if bal < 0: bal = 0
        
        history_bal.append(bal)
        age_axis.append(float(current_age + (m / 12.0)))
        
        if bal <= 0:
            ran_out = True
            if not fill_zeros:
                break
            
        if m % 12 == 0:
            c_exp *= (1 + curr_inflation / 100)

    # Fill Zeros Logic if requested and we broke out early (only if we didn't use the fill loop above)
    # The loop above continues if fill_zeros is True because we only break if not fill_zeros.
    # So if fill_zeros=True, we already have full length unless we ran out and balance stayed 0 (which it does)
    
    return history_bal, age_axis, ran_out, months_survived
    

@st.cache_data(show_spinner=False)
def create_pdf_report(data, sim_inflation=3.0, sim_return=5.0):
    """Creates a 4-Page PDF report attempting to mirror the visual dashboard."""
    import tempfile
    import math

    pdf = FPDF()
    
    # --- PAGE 1: Profile & Metrics ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, sanitize_for_pdf("The Retirement Dashboard"), ln=1, align="C")
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 10, sanitize_for_pdf(f"Report Generated: {datetime.now().strftime('%Y-%m-%d')}"), ln=1, align="C")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, sanitize_for_pdf("1. Profile Summary"), ln=1, fill=False)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    personal = data.get("personal", {})
    gov = data.get("government", {})
    
    pdf.set_font("Helvetica", "", 12)
    # 2-column layout simulation
    col_width = 90
    
    # Left Col (Personal)
    start_y = pdf.get_y()
    pdf.cell(col_width, 8, sanitize_for_pdf(f"Name: {personal.get('name', 'N/A')}"), ln=1)
    pdf.cell(col_width, 8, sanitize_for_pdf(f"Retirement Age: {personal.get('retirement_age', 65)}"), ln=1)
    pdf.cell(col_width, 8, sanitize_for_pdf(f"Life Expectancy: {personal.get('life_expectancy', 95)}"), ln=1)
    
    # Right Col (Gov) - Reset Y, Move X
    pdf.set_xy(10 + col_width + 10, start_y)
    pdf.cell(col_width, 8, sanitize_for_pdf(f"CPP Start: {gov.get('cpp_start_age', 65)} (${gov.get('cpp_amount', 0):,.0f}/mo)"), ln=1)
    pdf.cell(col_width, 8, sanitize_for_pdf(f"OAS Start: {gov.get('oas_start_age', 65)} (${gov.get('oas_amount', 0):,.0f}/mo)"), ln=1)
    
    pdf.ln(20)
    pdf.set_x(10)
    
    # High Level Calcs
    net_worth, assets, liabilities = get_net_worth(data)
    
    # Calculate Income/Expenses
    current_budget = data.get("budget", [])
    total_income = sum(float(i.get("amount", 0)) for i in current_budget if i.get("type") == "Income")
    
    total_expenses = 0.0
    for item in current_budget:
        if item["type"] == "Expense":
            amt = float(item.get("amount", 0))
            if item.get("frequency") == "Annually": total_expenses += amt / 12
            else: total_expenses += amt
    annual_exp_global = data.get("annual_expenditures", [])
    avg_annual_monthly = sum(float(ann.get("amount", 0.0)) / 12 for ann in annual_exp_global)
    total_expenses += avg_annual_monthly
    
    monthly_cashflow = total_income - total_expenses
    
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, sanitize_for_pdf("Snapshot Metrics"), ln=1)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(60, 10, sanitize_for_pdf("Net Worth"), border=1, align="C")
    pdf.cell(60, 10, sanitize_for_pdf("Monthly Cashflow"), border=1, align="C")
    pdf.cell(60, 10, sanitize_for_pdf("Est. Nest Egg Need"), border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(60, 12, sanitize_for_pdf(f"${net_worth:,.0f}"), border=1, align="C")
    pdf.cell(60, 12, sanitize_for_pdf(f"${monthly_cashflow:,.0f}"), border=1, align="C")
    
    # Quick Nest Egg Calc
    p_cpp = gov.get("cpp_amount", 0.0)
    p_oas = gov.get("oas_amount", 0.0)
    net_spend = max(0, total_expenses - (p_cpp + p_oas))
    nest_egg = (net_spend * 12) / 0.04
    pdf.cell(60, 12, sanitize_for_pdf(f"${nest_egg:,.0f}"), border=1, align="C")
    
    # --- PAGE 2: The Big Picture (Chart + Tables) ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, sanitize_for_pdf("2. The Big Picture"), ln=1)
    pdf.ln(5)
    
    # CHART: Net Worth History
    fig_nw = get_net_worth_history_fig(data, net_worth)
    if fig_nw:
        # Save temp image
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_nw:
                pio.write_image(fig_nw, tmp_nw.name, format="png", width=800, height=400, scale=2)
                pdf.image(tmp_nw.name, x=10, w=190)
                tmp_nw_path = tmp_nw.name
        except Exception as e:
            pdf.set_font("Helvetica", "I", 10)
            pdf.cell(0, 10, sanitize_for_pdf("[Chart unavailable - Visual generation failed]"), ln=1)
        # Clean up later or rely on OS temp clean. 
        # (For strictness we should remove it, but in Streamlit threading it's tricky. 
        # OS temp is safe enough for "download as is".)
    
    pdf.ln(5)
    
    # Asset/Liab Tables
    pdf.set_font("Helvetica", "B", 12)
    col1_x = 10
    col2_x = 110
    
    # Assets Title
    pdf.set_xy(col1_x, pdf.get_y())
    pdf.cell(90, 8, sanitize_for_pdf("Assets"), ln=1)
    
    # Assets Table
    pdf.set_font("Helvetica", "", 10)
    accs = data.get("accounts", [])
    assets_l = [a for a in accs if a.get("type") not in ["Liability", "Credit Card", "Loan", "Mortgage"] and a.get("balance", 0) >= 0]
    
    # Store Y to align liabilities column
    top_table_y = pdf.get_y()
    
    for a in assets_l:
        pdf.cell(60, 6, sanitize_for_pdf(a.get("name","")), border=1)
        pdf.cell(30, 6, sanitize_for_pdf(f"${a.get('balance',0):,.0f}"), border=1, align="R")
        pdf.ln()
    
    # Liabilities Column
    pdf.set_xy(col2_x, top_table_y - 8) # Move up to title level
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(90, 8, sanitize_for_pdf("Liabilities"), ln=1)
    
    pdf.set_xy(col2_x, top_table_y)
    pdf.set_font("Helvetica", "", 10)
    liabs = [a for a in accs if a.get("type") in ["Liability", "Credit Card", "Loan", "Mortgage"] or a.get("balance", 0) < 0]
    
    for l in liabs:
        pdf.set_x(col2_x)
        pdf.cell(60, 6, sanitize_for_pdf(l.get("name","")), border=1)
        pdf.cell(30, 6, sanitize_for_pdf(f"${abs(l.get('balance',0)):,.0f}"), border=1, align="R")
        pdf.ln()

    # --- PAGE 3: Projections ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, sanitize_for_pdf("3. How Long Will It Last?"), ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, sanitize_for_pdf(f"Simulation Parameters: Inflation {sim_inflation}%, Return {sim_return}%"), ln=1)
    pdf.ln(5)
    
    # Re-Run Logic for Chart
    # (Copied minimal logic from dashboard to generate axes)
    
    # Calculate Age
    current_age = 0
    p_dob_str = personal.get("dob")
    if p_dob_str:
        try:
            p_dob_dt = datetime.strptime(p_dob_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            current_age = today.year - p_dob_dt.year - ((today.month, today.day) < (p_dob_dt.month, p_dob_dt.day))
        except:
            pass
    current_age = int(current_age)
    
    # Calculate Income/Expenses for Simulation
    # Note: run_financial_simulation uses monthly_income and monthly_expenses.
    # total_income is mostly Budget Income.
    # total_expenses already includes avg_annual_monthly BUT run_financial_simulation handles annuals separately.
    # We should exclude avg_annual_monthly from the monthly_expenses passed to the simulation.
    
    sim_monthly_expenses = total_expenses - avg_annual_monthly

    # Run Simulation
    sim_bal_arr, sim_yr_arr, ran_out, months_survived = run_financial_simulation(
        current_age, net_worth, total_income, sim_monthly_expenses, sim_return, sim_inflation,
        personal.get("retirement_age", 65), gov, data.get("inheritance", {}), annual_exp_global, max_years=60
    )

    # Generate Chart
    max_proj = max(sim_bal_arr) if sim_bal_arr else net_worth
    target_mil = math.ceil(max_proj / 1000000.0) * 1000000.0 if max_proj > 0 else 1000000
    
    custom_ticks_p = [current_age]
    nxt = ((current_age // 5) + 1) * 5
    for v in range(nxt, current_age + 61, 5): custom_ticks_p.append(v)
    
    planned_ret_age = personal.get("retirement_age", 65)

    fig_proj_pdf = get_projection_fig(
        sim_yr_arr, sim_bal_arr, current_age, 60, target_mil, 1000000 if target_mil > 5000000 else 500000, 
        custom_ticks_p, planned_ret_age, (current_age >= planned_ret_age),
        gov.get("cpp_start_age",65), gov.get("oas_start_age",65), 
        data.get("inheritance",{}).get("age",0), data.get("inheritance",{}).get("amount",0.0)
    )
    
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_pr:
            pio.write_image(fig_proj_pdf, tmp_pr.name, format="png", width=800, height=400, scale=2)
            pdf.image(tmp_pr.name, x=10, w=190)
    except Exception as e:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 10, sanitize_for_pdf("[Chart unavailable - Visual generation failed]"), ln=1)
    
    pdf.ln(10)
    # Result Box
    final_age_ro = current_age + (months_survived / 12)
    
    pdf.set_fill_color(220, 240, 220) if not ran_out else pdf.set_fill_color(240, 220, 220)
    pdf.rect(10, pdf.get_y(), 190, 20, 'DF')
    pdf.set_xy(10, pdf.get_y() + 5)
    pdf.set_font("Helvetica", "B", 14)
    res_text = f"Money lasts until Age {int(final_age_ro)}" if ran_out else "Money lasts forever (60+ years)"
    pdf.cell(190, 10, sanitize_for_pdf(res_text), align="C")
    
    # --- PAGE 4: Financial Data ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, sanitize_for_pdf("4. Financial Data Inputs"), ln=1)
    pdf.ln(5)
    
    # Re-use table logic from before for Income/Expenses but cleaner
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, sanitize_for_pdf("Monthly Budget"), ln=1)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(80, 8, "Item", 1)
    pdf.cell(30, 8, "Type", 1)
    pdf.cell(40, 8, "Amount", 1)
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 10)
    for b in current_budget:
        pdf.cell(80, 8, sanitize_for_pdf(b.get("name","")), 1)
        pdf.cell(30, 8, sanitize_for_pdf(b.get("type","")), 1)
        pdf.cell(40, 8, sanitize_for_pdf(f"${float(b.get('amount',0)):,.0f}"), 1)
        pdf.ln()
    
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, sanitize_for_pdf("Annual One-Time Items"), ln=1)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(80, 8, "Activity", 1)
    pdf.cell(30, 8, "Age", 1)
    pdf.cell(40, 8, "Amount", 1)
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 10)
    for a in annual_exp_global:
        pdf.cell(80, 8, sanitize_for_pdf(a.get("name","")), 1)
        pdf.cell(30, 8, sanitize_for_pdf(str(a.get("start_age",""))), 1)
        pdf.cell(40, 8, sanitize_for_pdf(f"${float(a.get('amount',0)):,.0f}"), 1)
        pdf.ln()

    return bytes(pdf.output())

@st.dialog("Reset")
def confirm_reset_dialog():
    st.write("Are you sure you want to reset? This will clear all your data and cannot be undone.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Yes, Reset Everything", type="primary", use_container_width=True):
            # Increment Reset Counter to force widget refresh
            current_reset = st.session_state.get("_reset_counter", 0)
            new_reset = current_reset + 1
            
            st.session_state.clear()
            st.session_state["_reset_counter"] = new_reset # Persist counter
            
            # 1. Reset Data Object
            st.session_state["finance_data"] = {
                "accounts": [], "transactions": [], "history": [], 
                "personal": {}, "budget": [], "government": {}, "inheritance": {}, "annual_expenditures": [], "scenarios": []
            }
            st.rerun()
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

# --- BLOG LOGIC ---
def load_blog_posts():
    """Loads markdown posts from the posts/ directory."""
    posts_dir = os.path.join(BASE_DIR, "posts")
    posts = []
    
    # Ensure directory exists
    if not os.path.exists(posts_dir):
        return []
        
    for filename in os.listdir(posts_dir):
        if filename.endswith(".md"):
            with open(os.path.join(posts_dir, filename), "r") as f:
                content = f.read()
                
            # Simple frontmatter parser
            if content.startswith("---"):
                try:
                    # Remove the first "---"
                    _, frontmatter, body = content.split("---", 2)
                    
                    # Parse simplified YAML-like structure
                    meta = {}
                    for line in frontmatter.strip().split("\n"):
                        if ":" in line:
                            key, val = line.split(":", 1)
                            meta[key.strip()] = val.strip()
                            
                    # Add post
                    posts.append({
                        "id": filename,
                        "title": meta.get("title", "Untitled"),
                        "date": meta.get("date", "1970-01-01"),
                        "author": meta.get("author", "Unknown"),
                        "category": meta.get("category", "General"),
                        "excerpt": meta.get("excerpt", ""),
                        "content": body.strip()
                    })
                except Exception as e:
                    print(f"Error parsing {filename}: {e}")
                    
    # Sort by date descending
    return sorted(posts, key=lambda x: x['date'], reverse=True)

def render_blog_card(post):
    """Renders a preview card for a blog post."""
    with st.container():
        col_img, col_text = st.columns([1, 5])
        
        with col_img:
            # Placeholder thumbnail
            st.markdown(f"""
            <div style="background-color: #f0f2f6; height: 80px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 30px;">
                📝
            </div>
            """, unsafe_allow_html=True)
            
        with col_text:
            st.markdown(f"**{post['title']}**")
            st.caption(f"📅 {post['date']} • 🏷️ {post['category']}")
            st.write(post["excerpt"])
            
            st.markdown('<div class="blog-btn">', unsafe_allow_html=True)
            if st.button(f"Read More", key=f"btn_read_{post['id']}", type="secondary"):
                st.session_state["selected_post"] = post
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()

def render_full_post(post):
    """Renders the full blog post view."""
    if st.button("← Back to Blog"):
        del st.session_state["selected_post"]
        st.rerun()
        
    st.title(post["title"])
    st.caption(f"Published on {post['date']} by {post['author']} • {post['category']}")
    
    st.markdown("---")
    st.markdown(post["content"])
    st.markdown("---")


def render_reset_button(key_suffix):
    with st.expander("Reset All Data", expanded=False):
        st.caption("This will clear all inputs and start fresh.")
        if st.button("Reset", key=f"btn_reset_{key_suffix}", type="primary", use_container_width=True):
            confirm_reset_dialog()

def main():
    # Custom CSS for Blue Primary Buttons and Title Positioning
    st.markdown("""
        <style>
        button[kind="primary"],
        button[kind="primary"]:disabled,
        div[data-testid="stFormSubmitButton"] button,
        div[data-testid="stFormSubmitButton"] button:disabled,
        div.stButton > button:first-child[kind="primary"],
        div.stFormSubmitButton > button:first-child[kind="primary"],
        div.stButton > button:first-child[kind="primary"]:disabled,
        div.stFormSubmitButton > button:first-child[kind="primary"]:disabled {
            background-color: #0068c9 !important;
            border-color: #0068c9 !important;
            color: white !important;
            opacity: 1 !important;
        }
        div.stButton > button:first-child[kind="primary"]:hover,
        div.stFormSubmitButton > button:first-child[kind="primary"]:hover {
            background-color: #0056a8;
            border-color: #0056a8;
            color: white;
        }
        div.stButton > button:first-child[kind="primary"]:focus,
        div.stFormSubmitButton > button:first-child[kind="primary"]:focus {
            background-color: #0056a8;
            border-color: #0056a8;
            color: white;
        }
        .main .block-container {
            padding-top: 0rem;
            margin-top: -2rem;
        }
        /* Increase spacing between tabs */
        button[data-baseweb="tab"] {
            margin-right: 0.25rem;
            padding-left: 0.25rem;
            padding-right: 0.25rem;
        }
        /* Right-align buttons in their columns */
        div.stButton > button {
            margin-left: auto !important;
            display: block !important;
        }
        /* Nudge Start Over button right to align with tabs/expanders */
        button[key="btn_start_over_final"],
        button[key="btn_start_over_final_demo"] {
            transform: translateX(28px); /* Adjusted to align with tab content right-edge */
        }
        /* Light Blue Buttons for Blog (similar to info note) */
        div.blog-btn > div.stButton > button {
            background-color: #e1f5fe !important;
            color: #01579b !important;
            border: 1px solid #b3e5fc !important;
            font-weight: 500 !important;
        }
        div.blog-btn > div.stButton > button:hover {
            background-color: #b3e5fc !important;
            border-color: #01579b !important;
        }
        /* Remove plus/minus buttons from number inputs */
        button[data-testid="stNumberInputStepUp"],
        button[data-testid="stNumberInputStepDown"] {
            display: none !important;
        }
        div[data-testid="stNumberInput"] input {
            padding-right: 1rem !important;
        }
        
        /* Chart Borders */
        .stPlotlyChart {
            border: 1px solid lightgray !important;
            border-radius: 8px !important;
            padding: 15px !important;
            background-color: white !important;
            box-sizing: border-box !important;
            width: 100% !important;
            display: block !important;
            overflow: hidden !important;
        }
        
        /* Fix Plotly Modebar Position */
        .js-plotly-plot .plotly .modebar {
            right: 15px !important;
            top: 15px !important;
        }
        /* Subtle Tab Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #f8f9fa;
            border-radius: 10px 10px 0px 0px;
            border-bottom: none;
            padding: 0px 16px;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #f0f2f6;
        }
        .stTabs [aria-selected="true"] {
            background-color: #ffffff !important;
            border-bottom: none !important;
            border-top: 1px solid #eee;
            border-left: 1px solid #eee;
            border-right: 1px solid #eee;
        }
        
        /* Font Styling for Tab Text */
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size: 1.0rem !important;
            font-weight: 600 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Session-state backed data for Demo interactivity
    if "finance_data" not in st.session_state:
        st.session_state["finance_data"] = load_data()
    
    # Initialize session state for form results persistence
    if "show_results" not in st.session_state:
        st.session_state["show_results"] = False
    if "calculated_results" not in st.session_state:
        st.session_state["calculated_results"] = {}
    
    data = st.session_state["finance_data"]

    # Hide Sidebar in Demo Mode (CSS)
    if DEMO_MODE:
        st.markdown("""
            <style>
                [data-testid="stSidebar"] {display: none;}
                [data-testid="collapsedControl"] {display: none;}
            </style>
        """, unsafe_allow_html=True)

    # --- Sidebar: Actions ---
    # --- Sidebar removed as per request ---

    # --- Main Dashboard ---
    # Calculate PDF Data (Pre-compute to avoid layout issues)
    pdf_data = None
    pdf_error = None
    try:
        inf_val = st.session_state.get("hl_inflation", 3.0)
        ret_val = st.session_state.get("hl_return", 5.0)
        # DEBUG: Isolating source of 'None'
        # PDF generation temporarily disabled to prevent UI artifact ("None" text)
        # pdf_data = create_pdf_report(data, sim_inflation=inf_val, sim_return=ret_val)
        pdf_data = None
    except Exception as e:
        pdf_error = str(e)
    # --- Main Dashboard ---
    col_title, col_btns = st.columns([3, 1])
    with col_title:
        st.title("The Retirement Dashboard")
    with col_btns:
        # Spacers to align buttons with the text of the title
        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
        c_reset, c_pdf = st.columns(2)
        with c_reset:
            if st.button("Reset", type="secondary", use_container_width=True, disabled=False, help="Clear all data and results"):
                confirm_reset_dialog()

        with c_pdf:
            if pdf_data:
                st.download_button(
                    label="📄 PDF", 
                    data=pdf_data, 
                    file_name=f"retirement_plan_visual_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    help="Download the full 4-page visual dashboard report"
                )
            else:
                # Show error state or disabled state
                err_msg = pdf_error if pdf_error else "Generation disabled"
                st.button("📄 PDF", disabled=True, use_container_width=True, help=f"PDF generation unavailable: {err_msg}")

    st.markdown("<br>", unsafe_allow_html=True)
    

    
    # Tabs (Top-Level Navigation)
    # Tabs (Top-Level Navigation)
    # Added "Blog" tab as the second item
    # Layout: Main Content (Left) + Blog (Right Sidebar)
    col_main, col_blog = st.columns([3.5, 1], gap="medium")
    
    with col_main:
        tab_personal, tab_summary, tab_will_it_last, tab_budget = st.tabs([
            "👤 Profile",
            "⛰️ The Big Picture", 
            "⏳ How Long Will It Last?",
            "💰 Financial Data"
        ])



    # --- RIGHT SIDEBAR: Blog ---
    with col_blog:
        st.subheader("Blog Posts")
        posts = load_blog_posts()
        if not posts:
            st.info("No posts.")
        else:
            # Scrollable container for blog posts
            with st.container(height=1000):
                for post in posts:
                    with st.container(border=True):
                        st.caption(f"📅 {post['date']}")
                        st.markdown(f"**{post['title']}**")
                        st.markdown('<div class="blog-btn">', unsafe_allow_html=True)
                        if st.button("Read", key=f"right_blog_{post['id']}", use_container_width=True):
                            @st.dialog(post['title'])
                            def show_post_item(item):
                                st.caption(f"📅 {item['date']} • 🏷️ {item['category']} • ✍️ {item['author']}")
                                st.markdown("---")
                                st.markdown(item['content'])
                            show_post_item(post)
                        st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        st.caption("v1.0")

    # --- TAB: Profile Details ---
    # --- Profile Tab ---
    with tab_personal:
        st.markdown("### 👤 Profile")
        
        # Custom CSS to force the toast to the center and make it prominent
        st.markdown("""
            <style>
            /* TARGET THE TOAST DIRECTLY */
            div[data-testid="stToast"] {
                position: fixed !important;
                top: 50% !important;
                left: 50% !important;
                transform: translate(-50%, -50%) !important;
                z-index: 999999 !important;
                width: auto !important;
                min-width: 400px !important;
                max-width: 80vw !important;
                background-color: #FFFFFF !important; /* White background for a clean look */
                color: #333333 !important; /* Dark text for readability */
                border: 1px solid #e0e0e0 !important; /* Subtle border */
                border-left: 6px solid #4CAF50 !important; /* Pleasant green accent */
                border-radius: 8px !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important; /* Soft shadow */
                padding: 16px !important;
                margin: 0 !important;
            }
            /* Ensure the text inside is centered and readable */
            div[data-testid="stToastText"] {
                font-size: 1.1rem !important;
                text-align: center !important;
                font-weight: 500 !important;
                color: #333333 !important;
            }
            /* Optional: Hide the default toast container transition if it interferes */
            [data-testid="stToastContainer"] {
                right: 50% !important;
                bottom: 50% !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Display Success Message if saved
        if "profile_save_success" in st.session_state and st.session_state.profile_save_success:
            st.toast("Please add your information to the Financial Data page next", icon="👤")
            st.session_state.profile_save_success = False

        st.info("💡 **Tip:** Start here. Changes on this page will update totals across the site. Your data is not being stored.")
        
        personal = data.get("personal", {})
        gov = data.get("government", {})
        inh = data.get("inheritance", {})

        # Unified Container for everything on the Profile page
        with st.container(border=True):
            st.markdown("#### Personal Details")
            col1, col2 = st.columns(2)
            with col1:
                name_input = st.text_input("Name", value="", placeholder=personal.get("name", "Enter your name"))
                name = name_input if name_input else personal.get("name", "")
                
                dob_val = None
                if personal.get("dob"):
                    try:
                        dob_val = datetime.strptime(personal["dob"], "%Y-%m-%d").date()
                    except:
                        pass
                
                dob = st.date_input("Date of Birth", value=dob_val, min_value=datetime(1900, 1, 1).date(), max_value=datetime.now().date())
                
                city_input = st.text_input("Current City", value="", placeholder=personal.get("city", "Enter your city"))
                city = city_input if city_input else personal.get("city", "")
            
            with col2:
                ret_age_input = st.number_input("When Do You Want to Retire?", value=None, min_value=0, max_value=120, placeholder="55" if not personal.get("retirement_age") else str(personal.get("retirement_age")))
                ret_age = ret_age_input if ret_age_input is not None else personal.get("retirement_age")
                
                life_exp_input = st.number_input("Life Expectancy", value=None, min_value=0, max_value=120, placeholder=str(personal.get("life_expectancy", 95)))
                life_exp = life_exp_input if life_exp_input is not None else personal.get("life_expectancy")

            st.markdown("---")
            st.markdown("#### 🇨🇦 Government Benefits")
            
            # 1. Define base variables first
            g_cpp_start = gov.get("cpp_start_age", 65)
            g_oas_start = gov.get("oas_start_age", 65)

            # 2. Ensure session state has the current amounts for display
            if "p_cpp_amt_direct" not in st.session_state:
                st.session_state.p_cpp_amt_direct = gov.get("cpp_amount", get_cpp_estimate(g_cpp_start))
            if "p_oas_amt_direct" not in st.session_state:
                st.session_state.p_oas_amt_direct = gov.get("oas_amount", get_oas_estimate(g_oas_start))

            c_cpp1, c_cpp2 = st.columns(2)
            with c_cpp1:
                # Ensure index is safe
                try: 
                    cpp_idx = list(range(60, 71)).index(g_cpp_start)
                except: 
                    cpp_idx = 5 # 65
                new_cpp_start = st.selectbox("CPP Start Age", options=list(range(60, 71)), index=cpp_idx, key="p_cpp_start_new", on_change=update_cpp_amt)
            with c_cpp2:
                st.markdown(f"""
                <div style="font-size: 14px; color: rgba(49, 51, 63, 0.6); margin-bottom: 2px;">CPP Amount ($/mo)</div>
                <div style="font-size: 24px; font-weight: 600; color: #31333F;">${st.session_state.p_cpp_amt_direct:,.0f}</div>
                <div style="font-size: 12px; color: rgba(49, 51, 63, 0.4); font-style: italic;">National Average (2025)</div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            c_oas1, c_oas2 = st.columns(2)
            with c_oas1:
                oas_opts = list(range(65, 71))
                try:
                    oas_idx = oas_opts.index(g_oas_start)
                except:
                    oas_idx = 0
                new_oas_start = st.selectbox("OAS Start Age", options=oas_opts, index=oas_idx, key="p_oas_start_new", on_change=update_oas_amt)
            with c_oas2:
                st.markdown(f"""
                <div style="font-size: 14px; color: rgba(49, 51, 63, 0.6); margin-bottom: 2px;">OAS Amount ($/mo)</div>
                <div style="font-size: 24px; font-weight: 600; color: #31333F;">${st.session_state.p_oas_amt_direct:,.0f}</div>
                <div style="font-size: 12px; color: rgba(49, 51, 63, 0.4); font-style: italic;">National Average (2025)</div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 💎 Inheritance / Windfall")
            i_col1, i_col2 = st.columns(2)
            with i_col1:
                i_age = inh.get("age", 0)
                i_amt = inh.get("amount", 0.0)
                i_age_ph = str(int(i_age)) if i_age > 0 else "e.g. 65"
                inp_inh_age = st.number_input("Inheritance Age", min_value=0, max_value=100, value=None, placeholder=i_age_ph, step=1, key="p_inh_age_direct")
                new_inh_age = inp_inh_age if inp_inh_age is not None else int(i_age)
                
                i_amt_ph = f"{float(i_amt):,.0f}" if i_amt > 0 else "e.g. 100,000"
                inp_inh_amt = st.number_input("Amount ($)", value=None, placeholder=i_amt_ph, step=1000.0, key="p_inh_amt_direct")
                new_inh_amt = inp_inh_amt if inp_inh_amt is not None else float(i_amt)
            
            with i_col2:
                i_type = inh.get("type", "Cash / Investments")
                new_inh_type = st.selectbox("Type", ["Cash / Investments", "Property / House"], index=0 if i_type == "Cash / Investments" else 1, key="p_inh_type_new")
                
                i_sell = inh.get("sell_property", False)
                i_sell_age = inh.get("sell_age", 0)
                new_sell_prop = st.checkbox("Plan to sell this property?", value=i_sell, key="p_sell_prop_check") if new_inh_type == "Property / House" else False
                
                new_sell_age = 0
                if new_inh_type == "Property / House" and new_sell_prop:
                    tgt_val = i_sell_age if i_sell_age >= new_inh_age else new_inh_age + 5
                    new_sell_age = st.number_input("Sell Age", min_value=new_inh_age, max_value=100, value=int(tgt_val), step=1, key="p_inh_sell_age_direct")

            st.markdown("<br>", unsafe_allow_html=True)
            _, c_save = st.columns([5, 1])
            with c_save:
                if st.button("Save", type="primary", use_container_width=True, key="save_profile_btn"):
                    # Save Personal
                    data["personal"] = {
                        "name": name,
                        "dob": str(dob) if dob else None,
                        "city": city,
                        "retirement_age": ret_age,
                        "life_expectancy": life_exp
                    }
                    # Save Gov
                    data["government"] = {
                        "cpp_start_age": new_cpp_start,
                        "cpp_amount": st.session_state.p_cpp_amt_direct,
                        "oas_start_age": new_oas_start,
                        "oas_amount": st.session_state.p_oas_amt_direct
                    }
                    # Save Inheritance
                    data["inheritance"] = {
                        "age": new_inh_age,
                        "amount": new_inh_amt,
                        "type": new_inh_type,
                        "sell_property": new_sell_prop,
                        "sell_age": new_sell_age
                    }
                    save_data(data)
                    st.session_state.profile_save_success = True
                    st.rerun()

    # Calculate calc_age outside for use in other tabs
    # Handle None cases for global variables
    p_dob_str = data.get("personal", {}).get("dob")
    calc_age = 0
    if p_dob_str:
        try:
            p_dob_dt = datetime.strptime(p_dob_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            calc_age = today.year - p_dob_dt.year - ((today.month, today.day) < (p_dob_dt.month, p_dob_dt.day))
        except:
            pass
            
    planned_ret_age_val = data.get("personal", {}).get("retirement_age")
    planned_ret_age = planned_ret_age_val if planned_ret_age_val is not None else 65 # Safe default for charts
    
    planned_life_exp_val = data.get("personal", {}).get("life_expectancy")
    planned_life_exp = planned_life_exp_val if planned_life_exp_val is not None else 95 # Safe default for charts
    

    # --- Pre-calculate Budget Totals ---
    current_budget_global = data.get("budget", [])
    annual_exp_global = data.get("annual_expenditures", [])
    
    total_income_global = sum(float(item.get("amount", 0.0)) for item in current_budget_global if item.get("type") == "Income")
    
    # Base monthly expenses from recurring budget
    base_monthly_expenses = 0.0
    for item in current_budget_global:
        if item["type"] == "Expense":
            amt = float(item.get("amount", 0.0))
            freq = item.get("frequency", "Monthly")
            if freq == "Annually":
                base_monthly_expenses += (amt / 12)
            else:
                base_monthly_expenses += amt
    
    # Averaged monthly cost of annual expenditures
    avg_annual_monthly = sum(float(ann.get("amount", 0.0)) / 12 for ann in annual_exp_global)
    
    total_expenses_global = base_monthly_expenses + avg_annual_monthly
    net_cashflow_global = total_income_global - total_expenses_global

    # --- TAB: Summary (Home) ---
    # --- TAB: Summary/Big Picture ---
    with tab_summary:
        st.markdown("### ⛰️ The Big Picture")
        st.info("💡 **Tip:** Please fill out the Profile, Budget, and Assets & Liabilities pages to see the big picture.")
        # Calculate Correct Net Worth (Investments + Other Assets + Inheritance - Liabilities)
        liquid_nw, raw_assets, liabilities = get_net_worth(data)
        inheritance_val = data.get("inheritance", {}).get("amount", 0.0)
        
        assets = raw_assets + inheritance_val # Total Assets (Includes Investments, Chattel, Inheritance)
        net_worth = assets - liabilities # Net Worth (Includes everything)
        
        # Calculate Investments Only (for Withdrawal Logic)
        investments_total = sum(a.get("balance", 0.0) for a in data["accounts"] 
                               if a.get("type") in ["Bank", "Investments"])
        
        # --- Auto-Update Today's History ---
        # Ensure the history table reflects the current calculation method
        today_str = str(datetime.now().date())
        changed = False
        hist_entry = next((h for h in data["history"] if h["date"] == today_str), None)
        
        if hist_entry:
            if abs(hist_entry["net_worth"] - net_worth) > 0.01:
                hist_entry["net_worth"] = net_worth
                changed = True
        else:
            # If no entry for today exists, add it to seed the chart
            data["history"].append({"date": today_str, "net_worth": net_worth})
            changed = True
            
        if changed:
            save_data(data)
        
        # Prepare Data & Metrics (Full Page Width)
        df_hist_metrics = pd.DataFrame(data["history"]) if data["history"] else pd.DataFrame()
        if not df_hist_metrics.empty:
             df_hist_metrics['date'] = pd.to_datetime(df_hist_metrics['date'])
             df_hist_metrics['date_label'] = df_hist_metrics['date'].dt.strftime('%b %Y')
             
             # Calculate Growth
             first_value = df_hist_metrics['net_worth'].iloc[0]
             growth = net_worth - first_value
             
             # DISPLAY METRICS (Full Page Width)
             # CSS to force st.metric to wrap and use specific size
             st.markdown("""
             <style>
             [data-testid="stMetricValue"] {
                 font-size: 25px !important;
                 font-weight: bold !important;
                 word-wrap: break-word !important;
                 white-space: normal !important;
                 line-height: 1.1 !important;
             }
             [data-testid="stMetricLabel"] {
                 font-size: 14px !important;
                 font-weight: bold !important;
             }
             [data-testid="stMetric"] {
                 margin-bottom: -5px !important;
                 padding-bottom: 0px !important;
             }
             </style>
             """, unsafe_allow_html=True)

             col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4, gap="large")
             col_metric1.metric("Total Assets", f"${assets:,.0f}", help=f"Investments & Other: ${raw_assets:,.0f} | Inheritance: ${inheritance_val:,.0f}")
             col_metric2.metric("Total Liabilities", f"${liabilities:,.0f}")
             
             if len(df_hist_metrics) > 1:
                 col_metric3.metric("Net Worth", f"${net_worth:,.0f}", f"${growth:,.0f}")
             else:
                 col_metric3.metric("Net Worth", f"${net_worth:,.0f}")
                 
             col_metric4.metric("Extra Monthly Cash", f"${net_cashflow_global:,.0f}")
             


        # Charts
        st.markdown("<br>", unsafe_allow_html=True) # Spacing
        
        if data["history"]:
            df_hist_g = pd.DataFrame(data["history"])
            
            # Convert date strings to datetime and format as "Month Year"
            df_hist_g['date'] = pd.to_datetime(df_hist_g['date'])
            df_hist_g['date_label'] = df_hist_g['date'].dt.strftime('%b %Y')
            
            # Calculate Y-axis range
            current_value_g = net_worth
            max_val_in_data = max(current_value_g, df_hist_g['net_worth'].max()) if not df_hist_g.empty else current_value_g
            target_million = float(((int(max_val_in_data) // 1000000) + 1) * 1000000)
            y_min = 0
            y_max = target_million * 1.1

            # Create area chart with gradient (with dots)
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Scatter(
                x=df_hist_g['date_label'],
                y=df_hist_g['net_worth'],
                mode='lines+markers',
                fill='tozeroy',
                line=dict(color='#0068c9', width=3),
                marker=dict(size=12, color='#0068c9'),
                fillcolor='rgba(0, 104, 201, 0.2)',
                hovertemplate='<b>%{x}</b><br>Net Worth: $%{y:,.0f}<extra></extra>'
            ))
            
            fig_hist.update_layout(
                xaxis_title="Date",
                yaxis_title="Net Worth",
                yaxis_tickformat='$,.0f',
                yaxis_range=[y_min, y_max],
                title="Net Worth Over Time",
                title_font=dict(size=24, color='#31333F'),
                font=dict(family="sans-serif", size=14, color="#31333F"),
                hovermode="x unified",
                height=500, # Taller chart since it's full width
                margin=dict(l=20, r=50, t=40, b=20)
            )
            
            st.plotly_chart(fig_hist, use_container_width=True)
            
        else:
            st.info("No history yet.")



        # --- NEW SECTION: How am I Doing? ---
        st.markdown("---")
        st.subheader("How am I Doing?")
        
        status_mode = st.pills("Current Status", ["I am still working", "I am retired"], default="I am still working", label_visibility="collapsed")
        
        # Calculate values first
        # Explicit check: User requested Annual Income from Budget Tab * 12
        annual_income = total_income_global * 12
        target_spend = total_expenses_global
        
        # Account for Govt Benefits to reduce Nest Egg Needed
        gov = data.get("government", {})
        passive_income = gov.get("cpp_amount", 0.0) + gov.get("oas_amount", 0.0)
        net_target_spend = max(0, target_spend - passive_income)

        withdraw_rate = 0.04 # Standard 4% rule
        target_nest_egg = (net_target_spend * 12) / withdraw_rate if net_target_spend > 0 else 0.0
        
        # Show helpful message if no budget data entered yet
        if annual_income == 0 and target_spend == 0:
            st.info("💡 **Tip:** Enter your income and expenses in the **Budget** tab to see personalized retirement projections here.")

        if status_mode == "I am still working":
            st.markdown("#### How much should I be saving?")
             
            if annual_income == 0:
                st.info("💡 **Tip:** Enter your financial data in the **Financial Data** tab to find out how much you should be saving.")
            elif net_cashflow_global < 0:
                st.error(f"⚠️ **Tip:** You are currently overspending by **${abs(net_cashflow_global):,.0f} / month** (your expenses exceed your income). You will need to address this deficit to start building your retirement nest egg.")
            else:
                # Standard Savings Logic
                years_to_ret = max(0, planned_ret_age - calc_age)
                months_to_ret = years_to_ret * 12
                r = 0.05 / 12
                pmt = net_cashflow_global 

                if years_to_ret > 0:
                    future_wealth = (investments_total * (1+r)**months_to_ret) + (pmt * (((1+r)**months_to_ret - 1) / r))
                else:
                    future_wealth = investments_total
                    
                final_gap = target_nest_egg - future_wealth 
                lump_sum_today = final_gap / ((1 + r) ** months_to_ret) if (final_gap > 0 and months_to_ret > 0) else final_gap

                # Calculate EXTRA monthly savings needed to close the gap
                extra_monthly_savings_needed = 0
                if final_gap > 0 and months_to_ret > 0:
                     extra_monthly_savings_needed = final_gap * r / ((1+r)**months_to_ret - 1)

                if final_gap > 0:
                     st.info(f"💡 **Tip:** To retire at the age you've indicated on the Profile page ({planned_ret_age}), and according to your investments and financial data, you need to be saving **${extra_monthly_savings_needed:,.0f}** more per month until you retire or add a lump sum of **${lump_sum_today:,.0f}**.")
                else:
                     st.success(f"✅ **Tip:** You are ON TRACK. Based on your current plan, you have achieved your financial goal for age {planned_ret_age}! (Over-funded by ${abs(final_gap):,.0f})")

        else:
            # --- RETIRED LOGIC ---
            st.markdown("#### How much more money can I spend?")
            
            if investments_total == 0 and target_spend == 0:
                st.info("💡 **Tip:** Enter your financial data in the **Financial Data** tab to find out how much more money you can spend.")
            else:
                # Simple 4% Rule Reverse Check (or customized)
                # Safe withdrawal from current assets
                safe_annual_draw = investments_total * withdraw_rate
                safe_monthly_draw = safe_annual_draw / 12
                
                total_monthly_spending_power = safe_monthly_draw + passive_income
                current_spend = target_spend
                
                surplus = total_monthly_spending_power - current_spend
                
                if surplus > 0:
                    st.success(f"💡 **Tip:** You can safely spend an additional **${surplus:,.0f} / month** above your current budget.")
                else:
                    st.error(f"⚠️ **Tip:** You are currently overspending your safe withdrawal rate by **${abs(surplus):,.0f} / month**.")
                
                st.markdown(f"""
                **Breakdown:**
                - Investable Assets: **${investments_total:,.0f}**
                - Safe Monthly Withdrawal (4%): **${safe_monthly_draw:,.0f}**
                - Monthly Pension Benefits: **${passive_income:,.0f}**
                - **Total Safe Spending Power: ${total_monthly_spending_power:,.0f}**
                - *Your Current Spending: ${current_spend:,.0f}*
                """)
            


    # --- TAB: Assets & Liabilities ---


        

    # --- TAB: Budget ---
    # --- TAB: Financial Data ---
    with tab_budget:
        st.markdown("### 💰 Financial Data")
        st.info("💡 **Tip:** Please provide financial information here. This data powers the dashboard.")

        # ==========================================
        # 1. INITIALIZE SESSION STATE (Budget + Assets)
        # ==========================================

        
        # --- Budget Init ---
        if "budget_list_demo" not in st.session_state:
            existing_budget = data.get("budget", [])
            if not existing_budget:
                existing_budget = [
                    {"id": "bud_demo_sample_1", "name": "Salary", "category": "Work", "amount": 0.0, "type": "Income", "frequency": "Monthly"},
                    {"id": "bud_demo_sample_2", "name": "Rent / Mortgage", "category": "Housing", "amount": 0.0, "type": "Expense", "frequency": "Monthly"}
                ]
            st.session_state.budget_list_demo = existing_budget
        
        # Ensure default fields for Budget
        for item in st.session_state.budget_list_demo:
            if "name" not in item: item["name"] = ""
            if "amount" not in item: item["amount"] = 0.0
            if "type" not in item: item["type"] = "Expense"
            if "frequency" not in item: item["frequency"] = "Monthly"
            if "id" not in item: item["id"] = f"bud_demo_{int(datetime.now().timestamp())}_{random.randint(0, 1000)}"

        # --- Assets/Liabilities Init ---
        # 1. Define Detection Logic
        liab_types = ["Credit Card", "Loan", "Mortgage", "Liability"]
        
        # 2. Split existing data for session state
        asset_accounts = [a for a in data["accounts"] if a.get("type") not in liab_types and a.get("balance", 0.0) >= 0]
        liability_accounts = [a for a in data["accounts"] if a.get("type") in liab_types or a.get("balance", 0.0) < 0]

        ss_key_assets = "assets_list_demo_combined"
        if ss_key_assets not in st.session_state:
            if not asset_accounts:
                asset_accounts = [{"id": "acc_sample_gen", "name": "Savings Account", "type": "Bank", "balance": 0.0}]
            st.session_state[ss_key_assets] = asset_accounts

        ss_key_liab = "liabs_list_demo_combined"
        if ss_key_liab not in st.session_state:
            if not liability_accounts:
                liability_accounts = [{"id": "liab_sample_generic", "name": "Mortgage", "type": "Liability", "balance": 0.0}]
            st.session_state[ss_key_liab] = liability_accounts

        ss_key_chattel = "chattel_list_demo"
        if ss_key_chattel not in st.session_state:
            chattel_accounts = [a for a in data["accounts"] if a.get("type") == "Chattel"]
            if not chattel_accounts:
                chattel_accounts = [{"id": "chat_sample_1", "name": "Furniture/Jewellery", "type": "Chattel", "balance": 0.0}]
            st.session_state[ss_key_chattel] = chattel_accounts

        # Ensure default fields for Assets/Liabs/Chattel
        for a in st.session_state[ss_key_assets]:
            if "name" not in a: a["name"] = ""
            if "balance" not in a: a["balance"] = 0.0
            if "id" not in a: a["id"] = f"acc_demo_{int(datetime.now().timestamp())}_{random.randint(0, 1000)}"
            if "type" not in a: a["type"] = "Investments"
        for l in st.session_state[ss_key_liab]:
            if "name" not in l: l["name"] = ""
            if "balance" not in l: l["balance"] = 0.0
            if "id" not in l: l["id"] = f"liab_demo_{int(datetime.now().timestamp())}_{random.randint(0, 1000)}"
            if "type" not in l: l["type"] = "Liability"
        for c in st.session_state[ss_key_chattel]:
            if "name" not in c: c["name"] = ""
            if "balance" not in c: c["balance"] = 0.0
            if "id" not in c: c["id"] = f"chat_demo_{int(datetime.now().timestamp())}_{random.randint(0, 1000)}"
            if "type" not in c: c["type"] = "Chattel"


        # ==========================================
        # 2. RENDER UNIFIED FORM
        # ==========================================
        
        if "annual_list_demo" not in st.session_state:
            existing_annual = data.get("annual_expenditures", [])
            if not existing_annual:
                existing_annual = [
                    {"id": "ann_sample_1", "name": "International Trip", "amount": 0.0, "frequency": "Every Year", "start_age": 65}
                ]
            st.session_state.annual_list_demo = existing_annual

        # Split budget into income/expenses for distinct sections
        income_items = [i for i in st.session_state.budget_list_demo if i.get("type") == "Income"]
        expense_items = [i for i in st.session_state.budget_list_demo if i.get("type") == "Expense"]

        # Pre-calculate totals for Headers
        total_inc_header = sum(float(i.get("amount", 0)) for i in income_items)
        total_exp_header = 0.0
        for e in expense_items:
            amt = float(e.get("amount", 0))
            freq = e.get("frequency", "Monthly")
            if freq == "Annually": total_exp_header += amt / 12
            else: total_exp_header += amt
        
        total_ann_header = sum(float(i.get("amount", 0)) for i in st.session_state.annual_list_demo)
        total_inv_header = sum(float(a.get("balance", 0)) for a in st.session_state[ss_key_assets])
        total_chat_header = sum(float(c.get("balance", 0)) for c in st.session_state[ss_key_chattel])
        total_liab_header = sum(float(l.get("balance", 0)) for l in st.session_state[ss_key_liab])

        with st.container(border=True):
            
            # --- SECTION 1: INCOME ---
            st.markdown(f"#### 1. Monthly Income: \${total_inc_header:,.0f}")
            h_cols_i = st.columns([3, 2, 2, 0.8])
            headers_i = ["Source", "Notes", "Amount", ""]
            for col, h in zip(h_cols_i, headers_i): 
                if h: col.markdown(f"**{h}**")
            
            updated_income = []
            to_delete_income = None
            subtotal_income = 0.0
            
            for idx, row in enumerate(income_items):
                r_cols_i = st.columns([3, 2, 2, 0.8])
                name_val = r_cols_i[0].text_input("Source", value="", placeholder=row["name"] or "Income source", key=f"i_name_demo_{idx}", label_visibility="collapsed")
                new_name = name_val if name_val else row["name"]
                
                cat_val = r_cols_i[1].text_input("Notes", value="", placeholder=row.get("category", "") or "Notes", key=f"i_cat_demo_{idx}", label_visibility="collapsed")
                new_cat = cat_val if cat_val else row.get("category", "")
                
                amt_val = r_cols_i[2].number_input("Amount", value=None, placeholder="5,000" if float(row['amount']) == 0 else f"{float(row['amount']):.0f}", key=f"i_amt_demo_{idx}", label_visibility="collapsed", format="%.0f")
                new_amt = amt_val if amt_val is not None else float(row["amount"])
                
                if r_cols_i[3].button("🗑️", key=f"i_del_inc_demo_{idx}"): to_delete_income = idx
                
                subtotal_income += new_amt
                updated_income.append({"id": row["id"], "name": new_name, "category": new_cat, "amount": new_amt, "type": "Income", "frequency": "Monthly"})

            if to_delete_income is not None:
                updated_income.pop(to_delete_income)
                st.session_state.budget_list_demo = updated_income + expense_items
                st.rerun()

            if st.button("➕ Add Income Source", key="btn_add_income_demo"):
                st.session_state.budget_list_demo.append({"id": f"bud_demo_{int(datetime.now().timestamp())}", "name": "", "category": "", "amount": 0.0, "type": "Income", "frequency": "Monthly"})
                st.rerun()

            st.markdown("---")
            
            # --- SECTION 2: EXPENSES ---
            st.markdown(f"#### 2. Expenses: \${total_exp_header:,.0f}/mo")
            h_cols_e = st.columns([3, 2, 2, 2, 0.8])
            headers_e = ["Kind", "Category", "Amount", "Frequency ⌵", ""]
            for col, h in zip(h_cols_e, headers_e): 
                if h: col.markdown(f"**{h}**")
            
            updated_expenses = []
            to_delete_expense = None
            sub_exp_monthly = 0.0

            for idx, row in enumerate(expense_items):
                r_cols_e = st.columns([3, 2, 2, 2, 0.8])
                name_val = r_cols_e[0].text_input("Name", value="", placeholder=row["name"] or "Expense", key=f"e_name_demo_{idx}", label_visibility="collapsed")
                new_name = name_val if name_val else row["name"]
                
                cat_val = r_cols_e[1].text_input("Cat", value="", placeholder=row.get("category", "") or "Category", key=f"e_cat_demo_{idx}", label_visibility="collapsed")
                new_cat = cat_val if cat_val else row.get("category", "")
                
                amt_val = r_cols_e[2].number_input("Amt", value=None, placeholder="2,000" if float(row['amount']) == 0 else f"{float(row['amount']):.0f}", key=f"e_amt_demo_{idx}", label_visibility="collapsed", format="%.0f")
                new_amt = amt_val if amt_val is not None else float(row["amount"])
                
                freq_opts = ["Monthly", "Annually"]
                curr_f = row.get("frequency", "Monthly")
                new_freq = r_cols_e[3].selectbox("Freq", options=freq_opts, index=0 if curr_f == "Monthly" else 1, key=f"e_freq_demo_{idx}", label_visibility="collapsed")
                if r_cols_e[4].button("🗑️", key=f"e_del_exp_demo_{idx}"): to_delete_expense = idx
                
                if new_freq == "Annually": sub_exp_monthly += (new_amt/12)
                else: sub_exp_monthly += new_amt
                
                updated_expenses.append({"id": row["id"], "name": new_name, "category": new_cat, "amount": new_amt, "type": "Expense", "frequency": new_freq})

            if to_delete_expense is not None:
                updated_expenses.pop(to_delete_expense)
                st.session_state.budget_list_demo = income_items + updated_expenses
                st.rerun()

            if st.button("➕ Add Expense", key="btn_add_expense_demo_new"):
                st.session_state.budget_list_demo.append({"id": f"exp_demo_{int(datetime.now().timestamp())}", "name": "", "category": "", "amount": 0.0, "type": "Expense", "frequency": "Monthly"})
                st.rerun()

            st.markdown("---")
            
            # --- SECTION 3: ANNUAL BUCKET LIST ---
            st.markdown(f"#### 3. 🏆 Annual Bucket List: \${total_ann_header:,.0f}")
            if "annual_list_demo" not in st.session_state:
                existing_annual = data.get("annual_expenditures", [])
                if not existing_annual:
                    existing_annual = [
                        {"id": "ann_sample_1", "name": "International Trip", "amount": 0.0, "frequency": "Every Year", "start_age": 65}
                    ]
                st.session_state.annual_list_demo = existing_annual
            
            h_cols_a = st.columns([3, 2, 3.5, 1, 0.8])
            headers_a = ["Activity", "Amount", "Frequency ⌵", "Start Age", ""]
            for col, h in zip(h_cols_a, headers_a): 
                if h: col.markdown(f"**{h}**")
            
            updated_ann = []
            to_delete_ann = None
            for idx, row in enumerate(st.session_state.annual_list_demo):
                r_cols_a = st.columns([3, 2, 3.5, 1, 0.8])
                name_val = r_cols_a[0].text_input("Name", value="", placeholder=row["name"] or "Activity", key=f"ann_n_demo_{idx}", label_visibility="collapsed")
                a_name = name_val if name_val else row["name"]
                
                amt_val = r_cols_a[1].number_input("Amt", value=None, placeholder="5,000" if float(row['amount']) == 0 else f"{float(row['amount']):.0f}", key=f"ann_a_demo_{idx}", label_visibility="collapsed", format="%.0f")
                a_amt = amt_val if amt_val is not None else float(row["amount"])
                
                ann_f_opts = ["One-time", "Every Year", "Every 2 Years", "Every 5 Years", "Every 10 Years"]
                curr_af = row.get("frequency", "One-time")
                a_freq = r_cols_a[2].selectbox("Freq", options=ann_f_opts, index=ann_f_opts.index(curr_af) if curr_af in ann_f_opts else 0, key=f"ann_f_demo_{idx}", label_visibility="collapsed")
                
                age_val = r_cols_a[3].number_input("Age", value=None, placeholder=str(int(row.get("start_age", 65))), key=f"ann_g_demo_{idx}", label_visibility="collapsed")
                a_age = age_val if age_val is not None else int(row.get("start_age", 65))
                
                if r_cols_a[4].button("🗑️", key=f"ann_d_demo_{idx}"): to_delete_ann = idx
                updated_ann.append({"id": row.get("id"), "name": a_name, "amount": a_amt, "frequency": a_freq, "start_age": a_age})

            if to_delete_ann is not None:
                updated_ann.pop(to_delete_ann)
                st.session_state.annual_list_demo = updated_ann
                st.rerun()

            if st.button("➕ Add Annual Item", key="btn_add_ann_demo_new"):
                st.session_state.annual_list_demo.append({"id": f"ann_demo_{int(datetime.now().timestamp())}", "name": "", "amount": 0.0, "frequency": "One-time", "start_age": 65})
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.container(border=True):

            # --- SECTION 4: INVESTMENTS (Savings, etc.) ---
            st.markdown(f"#### 4. 🏦 Investments (Savings, etc.): \${total_inv_header:,.0f}")
            h_cols_ass = st.columns([5, 3, 0.8])
            headers_ass = ["Name", "Balance", ""]
            for col, h in zip(h_cols_ass, headers_ass): 
                if h: col.markdown(f"**{h}**")
            
            updated_assets = []
            to_delete_asset = None
            subtotal_assets = 0.0
            
            for idx, row in enumerate(st.session_state[ss_key_assets]):
                r_cols_ass = st.columns([5, 3, 0.8])
                name_val = r_cols_ass[0].text_input("Name", value="", placeholder=row["name"] or "Account name", key=f"a_name_cmb_{idx}", label_visibility="collapsed")
                a_name = name_val if name_val else row["name"]
                
                try: curr_bal = float(row.get("balance", 0.0))
                except: curr_bal = 0.0
                bal_val = r_cols_ass[1].number_input("Balance", value=None, placeholder=f"{curr_bal:.0f}", key=f"a_bal_cmb_{idx}", label_visibility="collapsed", format="%.0f")
                a_bal = bal_val if bal_val is not None else curr_bal
                
                if r_cols_ass[2].button("🗑️", key=f"a_del_cmb_{idx}"): to_delete_asset = idx
                
                subtotal_assets += a_bal
                updated_assets.append({"id": row.get("id"), "name": a_name, "institution": row.get("institution", ""), "type": row.get("type", "Investments"), "balance": a_bal})

            if to_delete_asset is not None:
                updated_assets.pop(to_delete_asset)
                st.session_state[ss_key_assets] = updated_assets
                st.rerun()

            if st.button("➕ Add Asset", key="btn_add_asset_cmb"):
                st.session_state[ss_key_assets].append({"id": f"acc_demo_{int(datetime.now().timestamp())}", "name": "", "institution": "", "type": "Investments", "balance": 0.0})
                st.rerun()

            st.markdown("---")

            # --- SECTION 5: OTHER ASSETS (Cars, etc.) ---
            st.markdown(f"#### 5. 🛋️ Other Assets (Cars, etc.): \${total_chat_header:,.0f}")
            h_cols_cha = st.columns([5, 3, 0.8])
            headers_cha = ["Item", "Estimated Value", ""]
            for col, h in zip(h_cols_cha, headers_cha): 
                if h: col.markdown(f"**{h}**")

            updated_chattel = []
            to_delete_chattel = None
            subtotal_chattel = 0.0
            
            for idx, row in enumerate(st.session_state[ss_key_chattel]):
                r_cols_cha = st.columns([5, 3, 0.8])
                name_val = r_cols_cha[0].text_input("Name", value="", placeholder=row["name"] or "Item name", key=f"c_name_cmb_{idx}", label_visibility="collapsed")
                c_name = name_val if name_val else row["name"]
                
                try: curr_c_bal = float(row.get("balance", 0.0))
                except: curr_c_bal = 0.0
                bal_val = r_cols_cha[1].number_input("Value", value=None, placeholder=f"{curr_c_bal:.0f}", key=f"c_bal_cmb_{idx}", label_visibility="collapsed", format="%.0f")
                c_bal = bal_val if bal_val is not None else curr_c_bal
                
                if r_cols_cha[2].button("🗑️", key=f"c_del_cmb_{idx}"): to_delete_chattel = idx
                
                subtotal_chattel += c_bal
                updated_chattel.append({"id": row.get("id"), "name": c_name, "institution": "", "type": "Chattel", "balance": c_bal})

            if to_delete_chattel is not None:
                updated_chattel.pop(to_delete_chattel)
                st.session_state[ss_key_chattel] = updated_chattel
                st.rerun()

            if st.button("➕ Add Chattel", key="btn_add_chattel_cmb"):
                st.session_state[ss_key_chattel].append({"id": f"chat_demo_{int(datetime.now().timestamp())}", "name": "", "institution": "", "type": "Chattel", "balance": 0.0})
                st.rerun()

            st.markdown("---")

            # --- SECTION 6: LIABILITIES (Loans and Debt) ---
            st.markdown(f"#### 6. 💳 Liabilities (Loans and Debt): \${total_liab_header:,.0f}")
            h_cols_lia = st.columns([5, 3, 0.8])
            headers_lia = ["Name", "Balance", ""]
            for col, h in zip(h_cols_lia, headers_lia): 
                if h: col.markdown(f"**{h}**")

            updated_liabilities = []
            to_delete_liab = None
            subtotal_liabilities = 0.0
            
            for idx, row in enumerate(st.session_state[ss_key_liab]):
                r_cols_lia = st.columns([5, 3, 0.8])
                name_val = r_cols_lia[0].text_input("Name", value="", placeholder=row["name"] or "Liability name", key=f"l_name_cmb_{idx}", label_visibility="collapsed")
                l_name = name_val if name_val else row["name"]
                
                try: curr_l_bal = float(row.get("balance", 0.0))
                except: curr_l_bal = 0.0
                bal_val = r_cols_lia[1].number_input("Balance", value=None, placeholder=f"{curr_l_bal:.0f}", key=f"l_bal_cmb_{idx}", label_visibility="collapsed", format="%.0f")
                l_bal = bal_val if bal_val is not None else curr_l_bal
                
                if r_cols_lia[2].button("🗑️", key=f"l_del_cmb_{idx}"): to_delete_liab = idx
                
                subtotal_liabilities += abs(l_bal)
                updated_liabilities.append({"id": row.get("id"), "name": l_name, "institution": row.get("institution", ""), "type": row.get("type", "Liability"), "balance": l_bal})

            if to_delete_liab is not None:
                updated_liabilities.pop(to_delete_liab)
                st.session_state[ss_key_liab] = updated_liabilities
                st.rerun()

            if st.button("➕ Add Liability", key="btn_add_liab_cmb"):
                st.session_state[ss_key_liab].append({"id": f"liab_demo_{int(datetime.now().timestamp())}", "name": "", "institution": "", "type": "Liability", "balance": 0.0})
                st.rerun()


            # ==========================================
            # 3. UNIFIED SAVE BUTTON
            # ==========================================
            st.markdown("<br>", unsafe_allow_html=True)
            _, c_save_all = st.columns([5, 1])
            with c_save_all:
                if st.button("Save", type="primary", key="btn_master_save_finance", use_container_width=True):
                    # 1. Save Budget (Income + Expenses)
                    data["budget"] = updated_income + updated_expenses
                    
                    # 2. Save Annual Items
                    data["annual_expenditures"] = updated_ann
                    
                    # 3. Save Accounts (Assets + Chattel + Liabilities)
                    data["accounts"] = updated_assets + updated_chattel + updated_liabilities
                    
                    # 4. Persist to Disk
                    save_data(data)
                    
                    # 5. Sync ALL Session States
                    st.session_state.budget_list_demo = updated_income + updated_expenses
                    st.session_state.annual_list_demo = updated_ann
                    st.session_state[ss_key_assets] = updated_assets
                    st.session_state[ss_key_chattel] = updated_chattel
                    st.session_state[ss_key_liab] = updated_liabilities
                    
                    # 6. Trigger Metrics Updates
                    rc = st.session_state.get("_reset_counter", 0)
                    st.session_state[f"hl_income_direct_v4_{rc}"] = subtotal_income
                    st.session_state[f"hl_expenses_direct_v4_{rc}"] = sub_exp_monthly
                    
                    # Update Net Worth history
                    current_nw = (subtotal_assets + subtotal_chattel) - subtotal_liabilities
                    today_str = str(datetime.now().date())
                    existing_hist = next((h for h in data["history"] if h["date"] == today_str), None)
                    if existing_hist: existing_hist["net_worth"] = current_nw
                    else: data["history"].append({"date": today_str, "net_worth": current_nw})
                    
                    st.session_state[f"hl_principal_direct_v4_{rc}"] = current_nw
                    
                    # 7. Success Banner
                    st.toast("✅ Financial Data Saved Successfully!", icon="💾")
                    
                    # Optional: Force Rerun to update everything (Metrics, Charts) immediately
                    st.rerun()

        # ==========================================
        # 4. SUMMARY SECTION (Below Container)
        # ==========================================
        
        st.subheader("Results Summary")
        with st.container(border=True):
            
            # Row 1: Cashflow
            st.markdown("##### Monthly Cashflow")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Income", f"${subtotal_income:,.0f}")
            c2.metric("Total Expenses", f"${sub_exp_monthly:,.0f}", delta_color="inverse")
            net_cash_live = subtotal_income - sub_exp_monthly
            c3.metric("Net Cashflow", f"${net_cash_live:,.0f}", delta=f"{'Surplus' if net_cash_live >= 0 else 'Deficit'}", delta_color="normal" if net_cash_live >= 0 else "inverse")
            
            st.markdown("<hr style='margin: 5px 0 15px 0; opacity: 0.2;'>", unsafe_allow_html=True)
            
            # Row 2: Net Worth
            st.markdown("##### Net Worth")
            n1, n2, n3, n4, n5 = st.columns(5)
            
            inheritance_val = data.get("inheritance", {}).get("amount", 0.0)
            
            # New Calculation: Investments + Other Assets + Inheritance - Liabilities
            net_worth_val = subtotal_assets + subtotal_chattel + inheritance_val - subtotal_liabilities
            
            n1.metric("Investments", f"${subtotal_assets:,.0f}")
            n2.metric("Other Assets", f"${subtotal_chattel:,.0f}")
            n3.metric("Inheritance", f"${inheritance_val:,.0f}")
            n4.metric("Total Liabilities", f"${subtotal_liabilities:,.0f}", delta_color="inverse")
            n5.metric("Total Assets", f"${net_worth_val:,.0f}")

        



    # --- TAB: How Long Will It Last? ---
    with tab_will_it_last:
        st.markdown("### ⏳ How Long Will It Last?")
        st.info("💡 **Tip:** Adjust the market variables to see how your investments will be affected.")
        # Using columns to create "Left Panel" (Inputs) and "Right Panel" (Results)
        # Added spacer column in the middle for padding
        col_main_left, col_spacer, col_main_right = st.columns([1, 0.2, 2])
        
        # Pre-populate principal
        liquid_nw, total_assets, total_liabilities = get_net_worth(data)
        total_net_worth = total_assets - total_liabilities

        # Logic variables placeholders
        months = 0
        run_out = False
        max_years = max(5, 95 - calc_age)
        history_bal = []
        years_axis = []
        
        # --- Pre-Calculation & Defaults ---
        # 1. Budget Defaults
        current_budget = data.get("budget", [])
        default_income = sum(item["amount"] for item in current_budget if item["type"] == "Income")
        
        default_expenses = 0.0
        for item in current_budget:
            if item["type"] == "Expense":
                amt = item.get("amount", 0.0)
                freq = item.get("frequency", "Monthly")
                if freq == "Annually":
                    default_expenses += (amt / 12)
                else:
                    default_expenses += amt

        # 2. Age & Retirement Status
        current_age = int(calc_age)
        is_retired = (current_age >= planned_ret_age)
        retirement_age = planned_ret_age
        
        # 3. Load Global Settings (Gov/Inheritance)
        gov = data.get("government", {})
        cpp_start_age = gov.get("cpp_start_age", 65)
        cpp_amount = gov.get("cpp_amount", 0.0)
        oas_start_age = gov.get("oas_start_age", 65)
        oas_amount = gov.get("oas_amount", 0.0)
        
        inh = data.get("inheritance", {})
        inherit_age = inh.get("age", 0)
        inherit_amount = inh.get("amount", 0.0)
        inherit_type = inh.get("type", "Cash / Investments")
        sell_property = inh.get("sell_property", False)
        sell_age = inh.get("sell_age", 0)

        # --- Define Calculation Variables ---
        monthly_income = default_income
        monthly_expenses = default_expenses
        principal = liquid_nw





# NO_OP - Searching first

        # Get Market Variables (defined by sliders rendered later in the layout)
        inflation = st.session_state.get("hl_inflation", 3.0)
        annual_return = st.session_state.get("hl_return", 5.0)

        # Logic Calculation (Real-time)
        if (principal or 0.0) >= 0: # Allow 0 expenses or income
            balance = (principal or 0.0)
            monthly_return = annual_return / 100 / 12
            curr_income = (monthly_income or 0.0)
            curr_expenses = (monthly_expenses or 0.0)
            
            history_bal = [balance]
            
            history_bal, years_axis, run_out, months = run_financial_simulation(
                current_age, (principal or 0.0), (monthly_income or 0.0), (monthly_expenses or 0.0), 
                annual_return, inflation,
                planned_ret_age, gov, inh, data.get("annual_expenditures", []), 
                max_years=max_years, fill_zeros=False
            )

                # Result box moved below chart

            # Chart
            
            # Calculate Y-axis range for consistency
            # Rule: Start at 0, Top at exactly the next full million above the highest value
            import math
            max_projected = max(history_bal) if history_bal else principal
            
            # Check for empty history to avoid errors
            if max_projected <= 0:
                    target_million_proj = 1000000.0
            else:
                    # Use math.ceil for robust ceiling logic
                    # Division by 1M -> ceil -> multiply by 1M
                    
                    val_in_millions = max_projected / 1000000.0
                    ceil_val = math.ceil(val_in_millions)
                    
                    target_million_proj = ceil_val * 1000000.0
            
            y_max_proj = target_million_proj

            # Dynamic tick size based on range to avoid clutter
            if y_max_proj <= 2000000:
                y_dtick = 200000
            elif y_max_proj <= 5000000:
                y_dtick = 500000
            else:
                y_dtick = 1000000

            # Custom Tick Values Logic
            # 1. Start at current age
            custom_ticks = [current_age]
            
            # 2. Next multiple of 10
            next_ten = ((current_age // 10) + 1) * 10
            
            # 3. Add multiples of 10 up to 110
            for val in range(next_ten, 111, 10):
                if val > current_age: # Avoid duplicates if current_age works out to be a multiple
                    custom_ticks.append(val)
            
            fig_proj = px.line(x=years_axis, y=history_bal, labels={'x': 'Age', 'y': 'Net Worth'})
            fig_proj.update_layout(
                yaxis=dict(range=[0, y_max_proj], tickformat='$,.0f', dtick=y_dtick),
                xaxis=dict(
                    range=[current_age, current_age + max_years], # Explicit range based on calculation
                    tickvals=custom_ticks,
                    tickmode='array',
                    tickangle=0 # Force upright labels
                ),
                margin=dict(l=20, r=50, t=40, b=20),
                height=550,
                hovermode="x unified",
                font=dict(size=14)
            )
            
            # Add vertical lines for Pension starts (Absolute Age)
            if not is_retired and planned_ret_age > current_age and planned_ret_age <= (current_age + max_years):
                fig_proj.add_vline(x=planned_ret_age, line_width=2, line_dash="solid", line_color="#ff2b2b", annotation_text="Retire", annotation_position="top left", annotation=dict(y=0.85))

            if cpp_start_age > current_age and cpp_start_age <= (current_age + max_years):
                fig_proj.add_vline(x=cpp_start_age, line_width=1, line_dash="dash", line_color="#21c354", annotation_text="CPP", annotation_position="top left", annotation=dict(y=0.90))
                
            if oas_start_age > current_age and oas_start_age <= (current_age + max_years):
                    fig_proj.add_vline(x=oas_start_age, line_width=1, line_dash="dash", line_color="#21c354", annotation_text="OAS", annotation_position="top left", annotation=dict(y=0.95))

            if inherit_amount > 0 and inherit_age > current_age and inherit_age <= (current_age + max_years):
                fig_proj.add_vline(x=inherit_age, line_width=1, line_dash="dash", line_color="#a855f7", annotation_text="Inheritance", annotation_position="top right", annotation=dict(y=0.95))

            with st.container(border=True):

                # Display Graph and Sliders side-by-side
                c_graph, c_vars = st.columns([3, 1])
                with c_graph:
                    # Add vertical marker for Retirement
                    if planned_ret_age > current_age:
                        fig_proj.add_vline(
                            x=planned_ret_age, 
                            line_width=2, 
                            line_dash="dash", 
                            line_color="rgba(0,0,0,0.3)",
                            annotation_text="Retire Age", 
                            annotation_position="top left"
                        )

                    st.plotly_chart(fig_proj, use_container_width=True)
                with c_vars:
                    # st.markdown("<br>", unsafe_allow_html=True) # Removed spacer
                    st.markdown("##### Market Variables")
                    
                    inflation = st.slider("Inflation (%)", 0.0, 10.0, 3.0, 0.1, key="hl_inflation")
                    annual_return = st.slider("Annual Return (%)", 0.0, 15.0, 5.0, 0.1, key="hl_return")

                # --- 2. Render Result Box (Middle) ---
                # st.markdown("<br>", unsafe_allow_html=True) # Removed spacer
                
                # Result Box Logic
                years_last = months / 12
                y_val = int(months // 12)
                m_val = int(months % 12)
                
                # Get First Name for personalization
                full_name = data.get("personal", {}).get("name", "there")
                first_name = full_name.split()[0] if full_name else "there"

                # Styling based on outcome
                if not run_out:
                    # Green box
                    box_color = "#d4edda"
                    text_color = "#155724"
                    border_color = "#c3e6cb"
                    result_text = "You'll never run out of money!"
                    sub_text = "Savings grow faster than spending."
                elif y_val <= 0:
                    # Immediate warning
                    box_color = "#f8d7da"
                    text_color = "#721c24"
                    border_color = "#f5c6cb"
                    result_text = "Your money will run out immediately."
                    sub_text = "Better start saving!"
                else:
                    # Warning/Info box (Orange/Blue)
                    box_color = "#cce5ff"
                    text_color = "#004085"
                    border_color = "#b8daff"
                    result_text = f"Your money runs out in {y_val} years, {m_val} months."
                    sub_text = f"(Until {datetime.now().year + y_val})"

                # Result Box HTML (Single Line Flex)
                st.markdown(f"""
                <div style="
                    background-color: {box_color};
                    color: {text_color};
                    border: 1px solid {border_color};
                    padding: 8px 10px;
                    border-radius: 5px;
                    text-align: center;
                    margin-bottom: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                ">
                    <span style="font-size: 18px; font-weight: bold;">{result_text}</span>
                    <span style="font-size: 14px; opacity: 0.8;">{sub_text}</span>
                </div>
                """, unsafe_allow_html=True)

                # --- 3. Render Inputs & Assumptions (Bottom) ---
                # st.markdown("<br>", unsafe_allow_html=True) # Removed spacer
                c_inputs_btm, col_space_btm, c_assump_btm = st.columns([1, 0.4, 1])
                
                with c_inputs_btm:
                    st.markdown("#### Financial Inputs")
                    st.markdown(f"""
                    <div style="font-size:14px; margin-bottom: 5px;">
                    <b>Work Income / Salary:</b> ${total_income_global:,.0f}<br>
                    <b>Base Monthly Expenses:</b> ${base_monthly_expenses:,.0f}<br>
                    <b>Annuals (Averaged):</b> ${avg_annual_monthly:,.0f}<br>
                    <hr style="margin: 5px 0; opacity: 0.3;">
                    <b>Investments:</b> ${principal:,.0f}
                    </div>
                    """, unsafe_allow_html=True)
                    st.caption("Work income stops at retirement age. Adjust on **Budget** & **Assets** tabs.")

                with c_assump_btm:
                    st.markdown("#### Assumptions")
                    inh_str = "None"
                    if inherit_amount > 0:
                        inh_str = f"${inherit_amount:,.0f} at age {inherit_age}"
                        if inherit_type != "Cash / Investments":
                            inh_str += f" ({inherit_type})"

                    st.markdown(f"""
                    <div style="font-size:14px; margin-bottom: 5px;">
                    <b>Current Age:</b> {current_age} &nbsp;|&nbsp; <b>Retire Age:</b> {planned_ret_age}<br>
                    <b>CPP:</b> ${cpp_amount:,.0f}/mo at age {cpp_start_age}<br>
                    <b>OAS:</b> ${oas_amount:,.0f}/mo at age {oas_start_age}<br>
                    <b>Inheritance:</b> {inh_str}
                    </div>
                    """, unsafe_allow_html=True)
                    st.caption("Change these values on the **Profile** tab.")


            
            
            st.markdown("<br><br>", unsafe_allow_html=True)
            # Reverse Calculator Section
            st.subheader("🧮 Reverse Calculator")
            st.info("💡 **Tip:** Check to see how much more money you can withdraw")
            with st.container(border=True):
                
                col_rev_1, col_rev_2 = st.columns([1, 3])
                with col_rev_1:
                    target_years_input = st.number_input("For your savings to last (Years):", value=None, step=1, key="hl_target", placeholder="30")
                    target_years = target_years_input if target_years_input is not None else 30
                
                with col_rev_2:
                     # Binary search solver
                    low = 0.0
                    high = principal # rough upper bound
                    if high < 100000: high = 100000.0
                    
                    best_expenses = 0.0
                    for _ in range(20):
                        mid = (low + high) / 2
                        # Use helper to test 'mid' expenses
                        _, _, ran_out, _ = run_financial_simulation(
                            current_age, principal, monthly_income, mid, annual_return, inflation,
                            planned_ret_age, gov, inh, data.get("annual_expenditures", []), 
                            max_years=int(target_years), fill_zeros=False
                        )
                        ok = not ran_out
                        
                        if ok:
                            best_expenses = mid # valid, try higher spending
                            low = mid
                        else:
                            high = mid # too much spending
                    
                    monthly_withdrawal = max(0, best_expenses - monthly_income)
                    
                    st.markdown(f"""
                    <div style="background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; border: 1px solid #ffeeba;">
                        <strong>Result:</strong> To last <b>{target_years} years</b>, you can withdraw an additional
                        <h3 style="margin: 5px 0;">${monthly_withdrawal:,.0f} / month</h3>
                        (Total allowable monthly spending: ${best_expenses:,.0f})
                    </div>
                    """, unsafe_allow_html=True)

    # --- TAB: What If? ---
    # --- What If Section (Merged) ---
        st.write("") # Padding
        st.divider() # Line
        st.write("") # Padding
        
        st.markdown("### 🚀 What If Scenarios")
        st.info("💡 **Tip:** Enter big ticket items below and see how these choices affect your net worth on the graph.")
        
        # Unified Container for all Scenarios + Chart
        with st.container(border=True):

            # Custom Row-Based Editor for Single-Click Dropdowns
            if "scenarios_list_demo" not in st.session_state:
                loaded_scenarios = data.get("scenarios", [])
                if not loaded_scenarios:
                     # Add sample scenario if empty
                     loaded_scenarios = [{
                         "id": "sample_scen_1",
                         "name": "Buy a Cottage",
                         "age": 60,
                         "type": "Cost",
                         "impact": 0.0,
                         "frequency": "One-time"
                     }]
                st.session_state.scenarios_list_demo = loaded_scenarios
            
            # Ensure default fields for each scenario
            for s in st.session_state.scenarios_list_demo:
                if "name" not in s: s["name"] = ""
                if "age" not in s: s["age"] = 65
                if "type" not in s: s["type"] = "Cost"
                if "impact" not in s: s["impact"] = 0.0
                if "sc_return" not in s: s["sc_return"] = 0.0
                if "sc_inflation" not in s: s["sc_inflation"] = 0.0
                if "frequency" not in s: s["frequency"] = "One-time"
                if "id" not in s: s["id"] = f"scen_demo_{int(datetime.now().timestamp())}_{random.randint(0, 1000)}"

            # Header
            h_cols = st.columns([2, 1.3, 2.2, 2, 0.8])
            headers = ["Description", "Age", "Cost", "Frequency ⌵", ""]
            for col, h in zip(h_cols, headers):
                if h:
                    col.markdown(f"**{h}**")
            # Rows
            updated_list = []
            to_delete = None
            
            for idx, row in enumerate(st.session_state.scenarios_list_demo):
                r_cols = st.columns([2, 1.3, 2.2, 2, 0.8])
                
                # Force type to "Cost" since we removed the selector
                new_type = "Cost"

                # Click-to-clear pattern
                name_val = r_cols[0].text_input("Name", value="", placeholder=row["name"] or "Scenario description", key=f"sc_name_demo_{idx}", label_visibility="collapsed")
                new_name = name_val if name_val else row["name"]
                
                age_val = r_cols[1].number_input("Age", value=None, placeholder=str(int(row["age"])), min_value=18, max_value=110, key=f"sc_age_demo_{idx}", label_visibility="collapsed")
                new_age = age_val if age_val is not None else int(row["age"])
                
                impact_val = r_cols[2].number_input("Cost", value=None, placeholder="50,000" if float(row['impact']) == 0 else f"{float(row['impact']):.0f}", key=f"sc_impact_demo_{idx}", label_visibility="collapsed", format="%.0f")
                new_impact = impact_val if impact_val is not None else float(row["impact"])
                
                freq_opts = ["One-time", "Monthly", "Twice per year", "Annually", "Every 2 years", "Every 3 years", "Every 5 years", "Every 10 years", "Until End of Plan"]
                curr_freq = row.get("frequency", "One-time")
                if curr_freq not in freq_opts: curr_freq = "One-time"
                new_freq = r_cols[3].selectbox("Freq", options=freq_opts, index=freq_opts.index(curr_freq), key=f"sc_freq_demo_{idx}", label_visibility="collapsed")
                
                if r_cols[4].button("🗑️", key=f"sc_del_demo_{idx}"):
                    to_delete = idx

                updated_list.append({
                    "id": row.get("id"),
                    "name": new_name,
                    "age": new_age,
                    "type": new_type,
                    "impact": new_impact,
                    "sc_return": row.get("sc_return", 0.0),
                    "sc_inflation": row.get("sc_inflation", 0.0),
                    "frequency": new_freq
                })

            if to_delete is not None:
                updated_list.pop(to_delete)
                st.session_state.scenarios_list_demo = updated_list
                st.rerun()

            st.session_state.scenarios_list_demo = updated_list

            # Add Button
            if st.button("➕ Add Scenario", key="btn_add_scenario_demo"):
                st.session_state.scenarios_list_demo.append({
                    "id": f"scen_demo_{int(datetime.now().timestamp())}",
                    "name": "",
                    "age": 65,
                    "type": "Cost",
                    "impact": 0.0,
                    "sc_return": 0.0,
                    "sc_inflation": 0.0,
                    "frequency": "One-time"
                })
                st.rerun()
            
            # --- Unified Save Button ---
            st.markdown("<br>", unsafe_allow_html=True)
            _, c_save = st.columns([5, 1])
            with c_save:
                if st.button("Save", type="primary", key="btn_save_scenarios_demo", use_container_width=True):
                    data["scenarios"] = st.session_state.scenarios_list_demo
                    save_data(data)
                    st.toast("✅ Scenarios saved!", icon="🚀")
                    st.rerun()



            # 2. Calculation Logic
            # Run Simulations
            # --- Missing Sliders Section (Restored) ---
            c_chart, c_vars_scen = st.columns([3, 1])
            with c_vars_scen:
                 st.markdown("#### Market Variables")
                 # Use unique keys for scenario tab sliders to avoid conflicts
                 inflation_scen = st.slider("Inflation (%)", 0.0, 10.0, 3.0, 0.1, key="hl_inf_scen", help="Projected annual inflation rate")
                 return_scen = st.slider("Annual Return (%)", 0.0, 15.0, 5.0, 0.1, key="hl_ret_scen", help="Projected annual investment return")
                 
                 # Re-run simulation with THESE slider values
                 base_h, base_a, _, _ = run_financial_simulation(
                     current_age, principal, monthly_income, monthly_expenses, return_scen, inflation_scen,
                     planned_ret_age, gov, inh, data.get("annual_expenditures", []), 
                     max_years=max_years, fill_zeros=True
                 )
                 scen_h, scen_a, _, _ = run_financial_simulation(
                     current_age, principal, monthly_income, monthly_expenses, return_scen, inflation_scen,
                     planned_ret_age, gov, inh, data.get("annual_expenditures", []),
                     scenarios=st.session_state.get("scenarios_list_demo", []),
                     max_years=max_years, fill_zeros=True
                 )

            with c_chart:

                fig_comp = go.Figure()
                
                # Base Plan Line
                fig_comp.add_trace(go.Scatter(
                    x=base_a, 
                    y=base_h,
                    mode='lines',
                    name='Base Plan',
                    line=dict(color='#1f77b4', width=3),
                    hovertemplate="Age: %{x:.1f}<br>Net Worth: $%{y:,.0f}<extra></extra>"
                ))
                
                # Scenario Line (only if scenarios exist)
                if st.session_state.get("scenarios_list_demo", []):
                    fig_comp.add_trace(go.Scatter(
                        x=scen_a, 
                        y=scen_h,
                        mode='lines',
                        name='With Scenarios',
                        line=dict(color='#ff7f0e', width=3, dash='dash'),
                        hovertemplate="Age: %{x:.1f}<br>Balance: $%{y:,.0f}<extra></extra>"
                    ))
                
                # Calculate Max Y for scale consistent with Tab 2 Logic
                import math
                max_base = max(base_h) if (base_h and len(base_h)>0) else 0.0
                max_scen = max(scen_h) if (scen_h and len(scen_h)>0) else 0.0
                max_val = max(max_base, max_scen)
                
                if max_val <= 0:
                     target_million_proj = 1000000.0
                else:
                     val_in_millions = max_val / 1000000.0
                     ceil_val = math.ceil(val_in_millions)
                     target_million_proj = ceil_val * 1000000.0
                
                y_max_comp = target_million_proj
                
                # Dynamic Y Ticks
                if y_max_comp <= 2000000: y_dtick_comp = 200000
                elif y_max_comp <= 5000000: y_dtick_comp = 500000
                else: y_dtick_comp = 1000000
                
                # Custom X Ticks (Multiples of 10)
                custom_ticks = [current_age]
                next_ten = ((current_age // 10) + 1) * 10
                for val in range(int(next_ten), current_age + max_years + 1, 10):
                     if val > current_age: custom_ticks.append(val)

                # Chart Layout
                fig_comp.update_layout(
                    title="",
                    xaxis_title="Age",
                    yaxis_title="Net Worth",
                    yaxis=dict(range=[0, y_max_comp], tickformat='$,.0f', dtick=y_dtick_comp),
                    xaxis=dict(range=[current_age, current_age + max_years], tickvals=custom_ticks, tickmode='array', tickangle=0),
                    height=550,
                    hovermode="x unified",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    margin=dict(l=40, r=40, t=90, b=40)
                )
                
                # Add Limit Line (Zero)
                fig_comp.add_shape(
                    type="line",
                    x0=current_age,
                    y0=0,
                    x1=current_age + max_years,
                    y1=0,
                    line=dict(color="red", width=1, dash="dot"),
                )
                
                # Retirement Marker
                ret_yr = planned_ret_age
                if ret_yr > current_age and ret_yr < (current_age + max_years):
                    fig_comp.add_vline(
                        x=ret_yr,
                        line_width=2,
                        line_dash="dot",
                        line_color="green",
                        annotation_text="Retirement",
                        annotation_position="top left"
                    )

                st.plotly_chart(fig_comp, use_container_width=True)
            
        st.divider()

        # Summary Metrics
        m1, m2, m3 = st.columns(3)
        
        def get_run_out(h):
            for i, v in enumerate(h):
                if v <= 0: return calc_age + (i / 12)
            return calc_age + max_years
            
        base_ro = get_run_out(base_h)
        scen_ro = get_run_out(scen_h)
        
        m1.metric("Base Plan Lasts Until", f"Age {int(base_ro)}")
        m2.metric("Scenario Lasts Until", f"Age {int(scen_ro)}", delta=f"{int(scen_ro - base_ro)} years")
        
        final_diff = scen_h[-1] - base_h[-1]
        m3.metric("Net Change at Age 110", f"${abs(final_diff):,.0f}", delta=f"{final_diff:,.0f}", delta_color="normal")
            


if __name__ == "__main__":
    main()
