import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime
import zipfile
import io

# --- Configuration ---
st.set_page_config(
    page_title="The Retirement Dashboard Demo",
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
    # Return pre-populated structure for Demo with User Requested Defaults
    return {
        "accounts": [
            {"id": "demo_acc_1", "name": "High Interest Savings", "type": "Bank", "balance": 50000.0},
            {"id": "demo_acc_2", "name": "RRSP / Investment Portfolio", "type": "Investments", "balance": 150000.0},
            {"id": "demo_acc_3", "name": "Primary Residence", "type": "Asset", "balance": 700000.0},
            {"id": "demo_acc_4", "name": "Mortgage", "type": "Liability", "balance": -500000.0}
        ],
        "transactions": [],
        "history": [],
        "personal": {
            "name": "Alex",
            "dob": "1981-01-01", # Approx Age 45
            "retirement_age": 55,
            "life_expectancy": 95
        },
        "budget": [
            {"id": "demo_inc_1", "name": "Employment Income", "amount": 5000.0, "frequency": "Monthly", "type": "Income"},
            {"id": "demo_exp_1", "name": "Core Living Expenses", "amount": 4000.0, "frequency": "Monthly", "type": "Expense"}
        ],
        "annual_expenditures": [],
        "government": {
            "cpp_start_age": 70,
            "cpp_amount": 1100.0,
            "oas_start_age": 65,
            "oas_amount": 713.0
        },
        "inheritance": {
            "age": 65,
            "amount": 500000.0,
            "type": "Cash / Investments"
        },
        "scenarios": []
    }

# Custom Metric Display to prevent truncation
def display_custom_metric(label, value, delta=None, help_text=None):
    delta_html = ""
    if delta:
        # Determine color based on content
        color = "#007a33" # Green
        bg_color = "#e6f4ea"
        if "-" in str(delta) and "benefit" not in label.lower() and "income" not in label.lower():
             color = "#d93025" # Red
             bg_color = "#fce8e6"
        
        delta_html = f'<div style="background-color: {bg_color}; color: {color}; display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.85rem; margin-top: 4px;">{delta}</div>'

    st.markdown(f"""
    <div style="margin-bottom: 15px; width: 100%;">
        <div style="font-size: 14px; color: rgba(49, 51, 63, 0.6); margin-bottom: 4px; font-family: 'Source Sans Pro', sans-serif;">{label}</div>
        <div style="font-size: 34px; font-weight: 700; color: rgb(49, 51, 63); line-height: 1.2; word-wrap: break-word; font-family: 'Source Sans Pro', sans-serif;">{value}</div>
        {delta_html}
    </div>
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

@st.dialog("Reset Dashboard?")
def confirm_reset_dialog():
    st.warning("Are you sure you want to reset? This will clear all your data and cannot be undone.")
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
                "personal": {}, "budget": [], "government": {}, "inheritance": {}, "annual_expenditures": []
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
            
            if st.button(f"Read More", key=f"btn_read_{post['id']}", type="secondary"):
                st.session_state["selected_post"] = post
                st.rerun()
        
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
        if st.button("Reset Dashboard", key=f"btn_reset_{key_suffix}", type="primary", use_container_width=True):
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
    col_title, col_clear = st.columns([5, 1])
    with col_title:
        st.title("The Retirement Dashboard Demo")
    with col_clear:
        if st.button("🗑️ Clear Session", type="secondary", use_container_width=True, help="Clear all data and results"):
            confirm_reset_dialog()

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Info banner about session state
    st.info("💡 Your data is private. It only lasts for this session. Please use the **Clear Session** button to reset, or close your browser.")
    
    # Tabs (Top-Level Navigation)
    # Tabs (Top-Level Navigation)
    # Added "Blog" tab as the second item
    # Layout: Main Content (Left) + Blog (Right Sidebar)
    col_main, col_blog = st.columns([3.5, 1], gap="medium")
    
    with col_main:
        tab_summary, tab_will_it_last, tab_what_if, tab_personal, tab_budget, tab_details, tab_liabilities = st.tabs([
            "⛰️ The Big Picture", 
            "⏳ Will It Last?",
            "🚀 What If?",
            "👤 Profile",
            "💰 Budget",
            "🏦 Assets", 
            "💳 Liabilities"
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
                        if st.button("Read", key=f"right_blog_{post['id']}", use_container_width=True):
                            @st.dialog(post['title'])
                            def show_post_item(item):
                                st.caption(f"📅 {item['date']} • 🏷️ {item['category']} • ✍️ {item['author']}")
                                st.markdown("---")
                                st.markdown(item['content'])
                            show_post_item(post)

        st.divider()
        st.caption("v1.0")

    # --- TAB: Profile Details ---
    # --- Profile Tab ---
    with tab_personal:
        if st.session_state.get("show_personal_results"):
            st.toast("✅ Profile details saved!", icon="👤")

        st.markdown("### 👤 Profile")
        st.info("💡 **Start here.** Changes on this page will update totals across the site.")
        
        personal = data.get("personal", {})
        
        # Form for input
        with st.form("personal_details_form"):
            col1, col2 = st.columns(2)
            with col1:
                # Click-to-clear: empty value, placeholder shows saved data
                name_input = st.text_input("Full Name", value="", placeholder=personal.get("name", "Enter your name"))
                name = name_input if name_input else personal.get("name", "")
                
                dob_val = None
                if personal.get("dob"):
                    try:
                        dob_val = datetime.strptime(personal["dob"], "%Y-%m-%d").date()
                    except:
                        pass
                
                dob = st.date_input("Date of Birth", value=dob_val, min_value=datetime(1900, 1, 1).date(), max_value=datetime.now().date())
                
                # Click-to-clear city field
                city_input = st.text_input("Current City", value="", placeholder=personal.get("city", "Enter your city"))
                city = city_input if city_input else personal.get("city", "")
            
            with col2:
                ret_age_input = st.number_input("Target Retirement Age", value=None, min_value=0, max_value=120, placeholder=str(personal.get("retirement_age", 65)))
                ret_age = ret_age_input if ret_age_input is not None else personal.get("retirement_age")
                
                life_exp_input = st.number_input("Plan Until Age (Life Expectancy)", value=None, min_value=0, max_value=120, placeholder=str(personal.get("life_expectancy", 95)))
                life_exp = life_exp_input if life_exp_input is not None else personal.get("life_expectancy")
            
            _, c_save = st.columns([5, 1])
            with c_save:
                if st.form_submit_button("Save", type="primary", use_container_width=True):
                    # Calculate age
                    calc_age = "---"
                    if dob:
                        today = datetime.now().date()
                        calc_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    
                    # Save to data
                    data["personal"] = {
                        "name": name,
                        "dob": str(dob) if dob else None,
                        "city": city,
                        "retirement_age": ret_age,
                        "life_expectancy": life_exp
                    }
                    save_data(data)
                    
                    # Store in session state for immediate display
                    st.session_state["show_personal_results"] = True
                    st.session_state["saved_personal_data"] = data["personal"]
                    st.session_state["calculated_age"] = calc_age
                    
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
    
    # --- Government Benefits Section (Moved to Profile) ---
    with tab_personal:
        st.markdown("---")
        st.markdown("### 🇨🇦 Government Benefits")
        
        gov = data.get("government", {})
        
        # Display saved results if they exist
        if st.session_state.get("show_gov_results"):
            st.toast("✅ Government benefits saved!", icon="🇨🇦")
        
        with st.form("gov_benefits_form"):
            # CPP Section
            st.markdown("**CPP (Canada Pension Plan)**")
            c_cpp1, c_cpp2 = st.columns(2)
            with c_cpp1:
                g_cpp_start = gov.get("cpp_start_age", 65)
                new_cpp_start = st.selectbox("CPP Start Age", options=list(range(60, 71)), index=list(range(60, 71)).index(g_cpp_start), key="p_cpp_start")
            with c_cpp2:
                g_cpp_amt = gov.get("cpp_amount", 0.0)
                new_cpp_amt_input = st.number_input("CPP Amount ($/mo)", value=None, step=50.0, placeholder=f"{float(g_cpp_amt):.2f}")
                new_cpp_amt = new_cpp_amt_input if new_cpp_amt_input is not None else float(g_cpp_amt)
            
            st.markdown("<br>", unsafe_allow_html=True)

            # OAS Section
            st.markdown("**OAS (Old Age Security)**")
            c_oas1, c_oas2 = st.columns(2)
            with c_oas1:
                g_oas_start = gov.get("oas_start_age", 65)
                oas_opts = list(range(65, 71))
                try:
                    oas_idx = oas_opts.index(g_oas_start)
                except ValueError:
                    oas_idx = 0
                new_oas_start = st.selectbox("OAS Start Age", options=oas_opts, index=oas_idx, key="p_oas_start")
            with c_oas2:
                g_oas_amt = gov.get("oas_amount", 0.0)
                new_oas_amt_input = st.number_input("OAS Amount ($/mo)", value=None, step=50.0, placeholder=f"{float(g_oas_amt):.2f}")
                new_oas_amt = new_oas_amt_input if new_oas_amt_input is not None else float(g_oas_amt)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            _, c_save = st.columns([5, 1])
            with c_save:
                if st.form_submit_button("Save", type="primary", use_container_width=True):
                    data["government"] = {
                        "cpp_start_age": new_cpp_start,
                        "cpp_amount": new_cpp_amt,
                        "oas_start_age": new_oas_start,
                        "oas_amount": new_oas_amt
                    }
                    save_data(data)
                    
                    # Store in session state for immediate display
                    st.session_state["show_gov_results"] = True
                    st.session_state["saved_gov_data"] = data["government"]
                    
                    st.rerun()

    # --- Inheritance Section (Moved to Profile) ---
    with tab_personal:
        st.markdown("---")
        st.markdown("### 💎 Inheritance / Windfall")
        
        inh = data.get("inheritance", {})
        
        with st.form("inheritance_form"):
            c1, c2 = st.columns(2)
            with c1:
                # Defaults
                i_age = inh.get("age", 0)
                i_amt = inh.get("amount", 0.0)
                
                # Age input also requested to be cleared? "where I'm entering dollar amounts... or inheritance age"
                # USER TESTING: Default to None with saved value as placeholder
                new_inh_age_input = st.number_input("Inheritance Age", min_value=0, max_value=100, value=None, step=1, help="Age you expect to receive this.", placeholder=str(int(i_age)))
                new_inh_age = new_inh_age_input if new_inh_age_input is not None else int(i_age)
                
                # USER TESTING: Default to None with saved value as placeholder
                new_inh_amt_input = st.number_input("Amount ($)", value=None, step=1000.0, placeholder=f"{float(i_amt):.2f}")
                new_inh_amt = new_inh_amt_input if new_inh_amt_input is not None else float(i_amt)
            
            with c2:
                i_type = inh.get("type", "Cash / Investments")
                new_inh_type = st.selectbox("Type", ["Cash / Investments", "Property / House"], index=0 if i_type == "Cash / Investments" else 1)
                
                # Logic for Property
                i_sell = inh.get("sell_property", False)
                i_sell_age = inh.get("sell_age", 0)
                
                new_sell_prop = False
                new_sell_age = 0
                
                if new_inh_type == "Property / House":
                    new_sell_prop = st.checkbox("Plan to sell this property?", value=i_sell)
                    if new_sell_prop:
                        tgt_val = i_sell_age if i_sell_age >= new_inh_age else new_inh_age + 5
                        sell_age_input = st.number_input("Sell Age", min_value=new_inh_age, max_value=100, value=None, step=1, placeholder=str(int(tgt_val)))
                        new_sell_age = sell_age_input if sell_age_input is not None else int(tgt_val)
                    else:
                        st.caption("Value will add to Net Worth but NOT to liquid spendable balance.")
            
            _, c_save = st.columns([5, 1])
            with c_save:
                if st.form_submit_button("Save", type="primary", use_container_width=True):
                    data["inheritance"] = {
                        "age": new_inh_age,
                        "amount": new_inh_amt,
                        "type": new_inh_type,
                        "sell_property": new_sell_prop,
                        "sell_age": new_sell_age
                    }
                    save_data(data)
                    st.success("Inheritance plan saved!")
                    st.rerun()

    # --- Pre-calculate Budget Totals ---
    # These are needed for both the Summary tab calculations and the Budget tab metrics
    current_budget_global = data.get("budget", [])
    
    total_income_global = sum(float(item.get("amount", 0.0)) for item in current_budget_global if item.get("type") == "Income")
    total_expenses_global = 0.0
    for item in current_budget_global:
        if item["type"] == "Expense":
            amt = item.get("amount", 0.0)
            freq = item.get("frequency", "Monthly")
            if freq == "Annually":
                total_expenses_global += (amt / 12)
            else:
                total_expenses_global += amt
    net_cashflow_global = total_income_global - total_expenses_global

    # --- TAB: Summary (Home) ---
    # --- TAB: Summary/Big Picture ---
    with tab_summary:
        st.markdown("### ⛰️ The Big Picture")
        st.info("💡 Please fill out the Profile, Budget, Assets and Liabilities pages to see the big picture.")
        net_worth, assets, liabilities = get_net_worth(data)
        
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
             
             first_value = df_hist_metrics['net_worth'].iloc[0]
             current_value = net_worth
             growth = current_value - first_value
             growth_pct = (growth / first_value * 100) if first_value != 0 else 0
             
             # DISPLAY METRICS (Full Page Width)
             # CSS to force st.metric to wrap and use specific size
             st.markdown("""
             <style>
             [data-testid="stMetricValue"] {
                 font-size: 34px !important;
                 word-wrap: break-word !important;
                 white-space: normal !important;
                 line-height: 1.2 !important;
             }
             [data-testid="stMetric"] {
                 margin-bottom: -15px !important;
                 padding-bottom: 0px !important;
             }
             </style>
             """, unsafe_allow_html=True)

             if len(df_hist_metrics) > 1:
                col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4, gap="large")
                col_metric1.metric("Current Net Worth", f"${current_value:,.2f}", f"${growth:,.2f}")
                col_metric2.metric("Growth", f"{growth_pct:+.1f}%", f"since {df_hist_metrics['date_label'].iloc[0]}")
                col_metric3.metric("Total Assets", f"${assets:,.2f}")
                col_metric4.metric("Guilt Free Spending", f"${net_cashflow_global:,.2f}")
             else:
                col_metric1, col_metric2, col_metric3 = st.columns(3, gap="large")
                col_metric1.metric("Current Net Worth", f"${current_value:,.2f}", "First snapshot recorded")
                col_metric2.metric("Total Assets", f"${assets:,.2f}")
                col_metric3.metric("Guilt Free Spending", f"${net_cashflow_global:,.2f}")
             


        # Charts
        c1, c2 = st.columns([1, 1]) # 50/50 split to give donut room to grow
        
        with c1:
            if data["history"]:
                df_hist = pd.DataFrame(data["history"])
                
                # Convert date strings to datetime and format as "Month Year"
                df_hist['date'] = pd.to_datetime(df_hist['date'])
                df_hist['date_label'] = df_hist['date'].dt.strftime('%b %Y')
                
                # Calculate growth metrics
                first_value = df_hist['net_worth'].iloc[0]
                current_value = net_worth # Use live calculated value to ensure alignment with top metric
                growth = current_value - first_value
                growth_pct = (growth / first_value * 100) if first_value != 0 else 0
                
                # Calculate Y-axis range
                # Rule: Exactly the next full million above the highest value in data
                max_val_in_data = max(current_value, df_hist['net_worth'].max())
                target_million = float(((int(max_val_in_data) // 1000000) + 1) * 1000000)
                y_min = 0
                y_max = target_million * 1.1  # Add 10% buffer so the top line is visible as a grid line
                

                
                # Create area chart with gradient (with dots)
                fig_hist = go.Figure()
                fig_hist.add_trace(go.Scatter(
                    x=df_hist['date_label'],
                    y=df_hist['net_worth'],
                    mode='lines+markers',
                    fill='tozeroy',
                    line=dict(color='#0068c9', width=3),
                    marker=dict(size=12, color='#0068c9'), # Increased size slightly for visibility
                    fillcolor='rgba(0, 104, 201, 0.2)',
                    hovertemplate='<b>%{x}</b><br>Net Worth: $%{y:,.2f}<extra></extra>'
                ))
                
                fig_hist.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Net Worth",
                    yaxis_tickformat='$,.0f',
                    yaxis_range=[y_min, y_max],
                    yaxis=dict(dtick=200000), # Ensure lines at 200k, 400k, 600k, 800k, 1M, etc.
                    hovermode='x unified',
                    showlegend=False,
                    margin=dict(l=0, r=40, t=30, b=0),
                    height=300,
                    font=dict(size=14)
                )
                
                st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("No history data yet. Add transactions or snapshots to see trends.")

        with c2:
            if data["accounts"]:
                df_acc = pd.DataFrame(data["accounts"])
                df_acc = df_acc[df_acc["balance"] > 0]  # Only positive balances
                if not df_acc.empty:
                    # Group by type and sum
                    df_grouped = df_acc.groupby('type')['balance'].sum().reset_index()
                    # Sort by custom order: Investments, Bank, Assets, Other
                    custom_order = ["Investments", "Bank", "Assets", "Other"]
                    df_grouped['sort_key'] = df_grouped['type'].apply(lambda x: custom_order.index(x) if x in custom_order else 999)
                    df_grouped = df_grouped.sort_values('sort_key')
                    
                    # Calculate percentages for legend
                    total_balance = df_grouped['balance'].sum()
                    df_grouped['label_with_pct'] = df_grouped.apply(lambda x: f"{x['type']} ({x['balance']/total_balance*100:.1f}%)", axis=1)
                    
                    # Custom color palette
                    colors = ['#0068c9', '#83c9ff', '#ff2b2b', '#ffa421', '#21c354', '#a855f7', '#ec4899']
                    
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=df_grouped['label_with_pct'],
                        values=df_grouped['balance'],
                        hole=0.5,
                        marker=dict(colors=colors),
                        sort=False, # Respect our custom DF sort order
                        textposition='inside',
                        textinfo='percent', # Add percentages back to slices
                        hovertemplate='<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>'
                    )])
                    
                    fig_pie.update_layout(
                        showlegend=True,
                        margin=dict(l=10, r=0, t=30, b=0), # Align with top of line chart
                        height=300, # Matches line chart height for center alignment
                        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05, font=dict(size=14)) # Reverted legend alignment
                    )
                    
                    st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
                else:
                     st.info("Accounts have 0 balance.")
            else:
                st.info("No accounts created.")



        # --- NEW SECTION: When can I stop working? ---
        st.markdown("---")
        st.subheader("🎯 Will It Last?")
        
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
        
        # Calculation logic
        is_retired_calc = (calc_age >= planned_ret_age)
        gap = target_nest_egg - net_worth
        years_to_ret = max(0, planned_ret_age - calc_age)
        months_to_ret = years_to_ret * 12
        
        # Projected Future Wealth (Current NW + Savings @ 5% return)
        r = 0.05 / 12
        pmt = net_cashflow_global
        
        if years_to_ret > 0:
            future_wealth = (net_worth * (1+r)**months_to_ret) + (pmt * (((1+r)**months_to_ret - 1) / r))
        else:
            future_wealth = net_worth
            
        final_gap = target_nest_egg - future_wealth
        
        # Calculate natural retirement timeline first (Including 3% Inflation + Annual Bucket List)
        inf_rate = 0.03 / 12 # 3% annual inflation
        annual_exp_plan = data.get("annual_expenditures", [])
        
        if not is_retired_calc and net_cashflow_global > 0:
            temp_nw = net_worth
            curr_target = target_nest_egg
            years_until_retire = 0
            while temp_nw < curr_target and years_until_retire < 100:
                y_idx = years_until_retire
                sim_age = calc_age + y_idx
                
                # Monthly loop for high accuracy
                for mm in range(12):
                    temp_nw += (temp_nw * r)
                    temp_nw += (pmt / 1) # Monthly savings
                
                # Subtract Annual Expenditures
                for exp in annual_exp_plan:
                    e_amt = exp.get("amount", 0.0)
                    e_freq = exp.get("frequency", "One-time")
                    e_start = exp.get("start_age", 65)
                    
                    should_apply = False
                    if e_freq == "One-time" and sim_age == e_start: should_apply = True
                    elif e_freq == "Every Year" and sim_age >= e_start: should_apply = True
                    elif e_freq == "Every 2 Years" and sim_age >= e_start and (sim_age - e_start) % 2 == 0: should_apply = True
                    elif e_freq == "Every 5 Years" and sim_age >= e_start and (sim_age - e_start) % 5 == 0: should_apply = True
                    elif e_freq == "Every 10 Years" and sim_age >= e_start and (sim_age - e_start) % 10 == 0: should_apply = True
                    
                    if should_apply:
                        temp_nw -= e_amt

                # Adjust target nest egg for inflation (expenses grow)
                curr_target = curr_target * (1.03) 
                years_until_retire += 1
        else:
            years_until_retire = 0
        
        # Sentence 1: Annual income + natural retirement timeline + nest egg
        if not is_retired_calc:
            # Construct standard sentence parts so data is always visible
            start_text = f"With your annual income level of <strong>${annual_income:,.0f}</strong>"
            
            if net_cashflow_global > 0 and years_until_retire > 0 and years_until_retire < 100:
                 mid_text = f", and considering your current expenses and assets, you can retire in approximately <strong>{years_until_retire} years</strong> (at age <strong>{calc_age + years_until_retire}</strong>)."
            elif net_cashflow_global <= 0:
                 mid_text = ", your expenses currently exceed your income."
            else:
                 if target_spend == 0:
                    mid_text = ", please enter your monthly expenses in the Budget tab to see when you can retire."
                 elif net_worth >= target_nest_egg:
                    mid_text = ", you have already reached your financial independence number!"
                 else:
                    mid_text = ", you are working toward your retirement goal."
            
            nest_egg_text = ""
            if target_nest_egg >= 0:
                 pension_note = f" (after ${passive_income:,.0f} benefits)" if passive_income > 0 else ""
                 nest_egg_text = f" To sustain your <strong>${target_spend:,.0f}/mo</strong> lifestyle{pension_note}, you need a Net Worth of <strong>${target_nest_egg:,.0f}</strong>."
            
            full_sentence = start_text + mid_text + nest_egg_text
            
            if net_cashflow_global <= 0:
                 # Display as warning but include ALL data
                st.markdown(f"""
                <div style="background-color: #fff4e5; padding: 15px; border-radius: 5px; border-left: 5px solid #ffa421; color: #663c00; margin-bottom: 10px;">
                ⚠️ {full_sentence}
                </div>
                """, unsafe_allow_html=True)
            else:
                 # Display as normal paragraph
                st.markdown(f"""
                <p style='margin: 0; padding: 0; line-height: 1.6;'>
                {full_sentence}
                </p>
                """, unsafe_allow_html=True)
                st.write("")  # Add space after first paragraph

        elif is_retired_calc:
            st.success("🎉 Congratulations. You've already stopped working.")
        
        # Sentence 2: Target retirement scenario
        # Sentence 2: Target retirement scenario
        if not is_retired_calc:
            # Use a default target of 10 years or the calculated years, whichever is smaller
            target_years = min(10, max(1, years_to_ret)) if years_to_ret > 0 else 10
            target_age = calc_age + target_years
            
            st.markdown(f"""
            <p style='margin: 0; padding: 0; line-height: 1.6;'>
            If you wanted to retire in <strong>{target_years} years</strong> (at age <strong>{target_age}</strong>), you could...
            </p>
            """, unsafe_allow_html=True)
            
            target_months = target_years * 12
            
            # Recalculate based on target years
            target_future_wealth = (net_worth * (1+r)**target_months) + (pmt * (((1+r)**target_months - 1) / r))
            target_gap = target_nest_egg - target_future_wealth
        
            st.write("")  # Small spacer before scenario cards
            
            # Scenarios cards
            s1, s2, s3, s4 = st.columns(4)
            
            # 1. Win the Lottery
            with s1:
                # Calculate what lump sum is needed today to retire in target_years
                lump_sum_needed = max(0.0, target_gap)
                
                # If gap is 0, show "On Track"
                if target_spend > 0 and target_gap <= 0:
                    lump_content = f'<div><div style="font-weight: bold; font-size: 24px; color: #21c354; margin-top: 10px;">ON TRACK</div><div style="font-size: 13px; color: #555; margin-top: 5px;">You\'ve already met this target!</div></div>'
                elif target_spend == 0:
                    lump_content = f'<div><div style="font-size: 13px; color: #999; margin-top: 10px;">Please enter expenses in the Budget tab.</div></div>'
                else:
                    lump_content = f'<div><div style="font-size: 13px; color: #555;">To retire in {target_years} years, you\'d need a one-time investment of:</div><div style="font-weight: bold; font-size: 18px; color: #0068c9;">${lump_sum_needed:,.0f}</div><div style="font-size: 11px; color: #888; margin-top: 5px;">Added to your current assets today.</div></div>'

                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; height: 240px; text-align: center; border: 1px solid #ddd;">
                    <div style="font-size: 24px;">🎰</div>
                    <div style="font-weight: bold; margin-bottom: 5px; color: black;">Win the Lottery</div>
                    {lump_content}
                </div>
                """, unsafe_allow_html=True)
            
            # 2. Get a Career Boost
            with s2:
                if target_months > 0 and target_gap > 0:
                    extra_monthly = (target_gap * r) / ((1+r)**target_months - 1)
                else:
                    extra_monthly = 0
                
                if target_spend > 0 and target_gap <= 0:
                    boost_content = f'<div><div style="font-weight: bold; font-size: 24px; color: #21c354; margin-top: 10px;">ON TRACK</div><div style="font-size: 13px; color: #555; margin-top: 5px;">No extra income needed!</div></div>'
                elif target_spend == 0:
                    boost_content = f'<div><div style="font-size: 13px; color: #999; margin-top: 10px;">Data needed.</div></div>'
                else:
                    boost_content = f'<div><div style="font-size: 13px; color: #555;">Invest an additional</div><div style="font-weight: bold; font-size: 18px; color: #21c354;">${max(0.0, extra_monthly):,.0f}/mo</div><div style="font-size: 11px; color: #888; margin-top: 5px;">Your current monthly surplus is <b>${net_cashflow_global:,.2f}</b>.</div></div>'

                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; height: 240px; text-align: center; border: 1px solid #ddd;">
                    <div style="font-size: 24px;">📈</div>
                    <div style="font-weight: bold; margin-bottom: 5px; color: black;">Get a Career Boost</div>
                    {boost_content}
                </div>
                """, unsafe_allow_html=True)

            # 3. Retire Later
            with s3:
                found_age = planned_ret_age
                temp_wealth = future_wealth
                # Adjust target for inflation in the "Retire Later" logic too
                retire_later_target = target_nest_egg * (1.03**(found_age - planned_ret_age))
                
                while temp_wealth < retire_later_target and found_age < 100:
                    found_age += 1
                    temp_wealth = (temp_wealth * (1+r)**12) + (pmt * (((1+r)**12 - 1) / r))
                    retire_later_target *= 1.03
                
                if target_spend > 0 and target_gap <= 0:
                    later_content = f'<div><div style="font-weight: bold; font-size: 24px; color: #21c354; margin-top: 10px;">ON TRACK</div><div style="font-size: 13px; color: #555; margin-top: 5px;">Current age: {planned_ret_age}</div></div>'
                elif target_spend == 0:
                    later_content = f'<div><div style="font-size: 13px; color: #999; margin-top: 10px;">Data needed.</div></div>'
                else:
                    later_content = f'<div><div style="font-size: 13px; color: #555;">Hit your goal with current savings by retiring at age</div><div style="font-weight: bold; font-size: 18px; color: #ffa421;">{found_age}</div><div style="font-size: 11px; color: #888; margin-top: 5px;">Based on current <b>${net_worth:,.0f}</b> assets.</div></div>'

                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; height: 240px; text-align: center; border: 1px solid #ddd;">
                    <div style="font-size: 24px;">⏳</div>
                    <div style="font-weight: bold; margin-bottom: 5px; color: black;">Retire Later</div>
                    {later_content}
                </div>
                """, unsafe_allow_html=True)

            # 4. Spend Less
            with s4:
                safe_spend = (future_wealth * withdraw_rate) / 12
                
                if target_spend > 0 and target_gap <= 0:
                    less_content = f'<div><div style="font-weight: bold; font-size: 24px; color: #21c354; margin-top: 10px;">ON TRACK</div><div style="font-size: 13px; color: #555; margin-top: 5px;">No spending cuts needed!</div></div>'
                elif target_spend == 0:
                    less_content = f'<div><div style="font-size: 13px; color: #999; margin-top: 10px;">Data needed.</div></div>'
                else:
                    less_content = f'<div><div style="font-size: 13px; color: #555;">A safe monthly amount is</div><div style="font-weight: bold; font-size: 18px; color: #ff2b2b;">${max(0.0, safe_spend):,.0f}/mo</div><div style="font-size: 11px; color: #888; margin-top: 5px;">Requires <b>${abs(safe_spend - total_expenses_global):,.0f} {"more" if (safe_spend - total_expenses_global) > 0 else "less"}</b> than current.</div></div>'

                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; height: 240px; text-align: center; border: 1px solid #ddd;">
                    <div style="font-size: 24px;">📉</div>
                    <div style="font-weight: bold; margin-bottom: 5px; color: black;">Spend Less</div>
                    {less_content}
                </div>
                """, unsafe_allow_html=True)
            


    # --- TAB: Assets ---
    with tab_details:

        # 1. Account Categories (Editable Summaries)
        # Placeholder for dynamic title
        asset_header_placeholder = st.empty()

        # 1. Gather all Asset Accounts (Inverse of Liabilities)
        liab_types = ["Liability", "Credit Card", "Loan", "Mortgage"]
        asset_accounts = [
            a for a in data["accounts"] 
            if a.get("type") not in liab_types and a.get("balance", 0.0) >= 0
        ]
        
        # Calculate Total Assets
        total_assets_val = sum(a["balance"] for a in asset_accounts)
        asset_header_placeholder.markdown(f"### Assets — ${total_assets_val:,.2f}")
        st.info("💡 Please provide details for assets on this page in order to see how it affects the big picture.")
        
        # Fixed categories to allow adding data even when empty
        types = ["Investments", "Assets", "Cash", "Other"]
        
        for asset_type in types:
            type_accounts = [a for a in asset_accounts if a["type"] == asset_type]
            type_total = sum(a["balance"] for a in type_accounts)
            
            with st.expander(f"**{asset_type}** — ${type_total:,.2f}", expanded=False):
                # Custom Row-Based Editor for Assets
                ss_key = f"assets_list_demo_{asset_type}"
                if ss_key not in st.session_state:
                    # If existing data is empty for this type, add a sample
                    if not type_accounts:
                        sample_name = "Sample Account"
                        if asset_type == "Investments": sample_name = "RRSP"
                        elif asset_type == "Cash": sample_name = "Emergency Fund"
                        elif asset_type == "Assets": sample_name = "Car"
                        
                        type_accounts = [
                            {"id": f"acc_sample_{asset_type}", "name": sample_name, "institution": "Bank", "type": asset_type, "balance": 1000.0}
                        ]
                    st.session_state[ss_key] = type_accounts
                
                # Ensure default fields
                for a in st.session_state[ss_key]:
                    if "name" not in a: a["name"] = ""
                    if "institution" not in a: a["institution"] = ""
                    if "type" not in a: a["type"] = asset_type
                    if "balance" not in a: a["balance"] = 0.0
                    if "id" not in a: a["id"] = f"acc_demo_{int(datetime.now().timestamp())}_{random.randint(0, 1000)}"

                # Header
                h_cols = st.columns([5, 3, 0.8])
                headers = ["Name", "Balance", ""]
                for col, h in zip(h_cols, headers):
                    if h:
                        col.markdown(f"**{h}**")
                # Rows
                updated_type_list = []
                to_delete_asset = None
                
                for a_idx, a_row in enumerate(st.session_state[ss_key]):
                    r_cols = st.columns([5, 3, 0.8])
                    
                    # Click-to-clear pattern
                    name_val = r_cols[0].text_input("Name", value="", placeholder=a_row["name"] or "Account name", key=f"a_name_demo_{asset_type}_{a_idx}", label_visibility="collapsed")
                    a_name = name_val if name_val else a_row["name"]
                    
                    # Institution removed from UI, preserve existing data
                    a_inst = a_row.get("institution", "")
                    
                    # Implicitly use the current section type since column was removed
                    a_type = asset_type
                    
                    # Handle balance safely with click-to-clear
                    try:
                        curr_bal = float(a_row.get("balance", 0.0))
                    except:
                        curr_bal = 0.0
                    bal_val = r_cols[1].number_input("Balance", value=None, placeholder=f"{curr_bal:.2f}", key=f"a_bal_demo_{asset_type}_{a_idx}", label_visibility="collapsed", format="%.2f")
                    a_bal = bal_val if bal_val is not None else curr_bal
                    
                    if r_cols[2].button("🗑️", key=f"a_del_demo_{asset_type}_{a_idx}"):
                        to_delete_asset = a_idx

                    updated_type_list.append({
                        "id": a_row.get("id"),
                        "name": a_name,
                        "institution": a_inst,
                        "type": a_type,
                        "balance": a_bal
                    })

                if to_delete_asset is not None:
                    updated_type_list.pop(to_delete_asset)
                    st.session_state[ss_key] = updated_type_list
                    st.rerun()

                st.session_state[ss_key] = updated_type_list

                # Add Button
                if st.button("➕ Add Account", key=f"btn_add_asset_demo_{asset_type}"):
                    st.session_state[ss_key].append({
                        "id": f"acc_demo_{int(datetime.now().timestamp())}",
                        "name": "",
                        "institution": "",
                        "type": asset_type,
                        "balance": 0.0
                    })
                    st.rerun()
                
                _, c_save = st.columns([5, 1])
                with c_save:
                    if st.button("Save", type="primary", key=f"save_demo_{asset_type}", use_container_width=True):
                        new_type_accounts = st.session_state[ss_key]
                        original_ids_in_scope = set(a.get("id") for a in type_accounts if a.get("id"))
                        other_accounts = [a for a in data["accounts"] if a.get("id") not in original_ids_in_scope]
                        data["accounts"] = other_accounts + new_type_accounts
                        
                        current_nw, _, _ = get_net_worth(data)
                        today_str = str(datetime.now().date())
                        existing_hist = next((h for h in data["history"] if h["date"] == today_str), None)
                        if existing_hist:
                            existing_hist["net_worth"] = current_nw
                        else:
                            data["history"].append({"date": today_str, "net_worth": current_nw})
                        
                        save_data(data)
                        rc = st.session_state.get("_reset_counter", 0)
                        st.session_state[f"hl_principal_direct_v4_{rc}"] = current_nw
                        st.success(f"{asset_type} updated!")
                        st.rerun()
        
        # Global "Add Account" could be here if needed, but typically users can add rows in any category editor
        # provided they set the type correctly.
        # If they change the type to something else, it will move to that category expander on reload.



    # --- TAB: Liabilities ---
    with tab_liabilities:
        # Placeholder for dynamic title
        liab_header_placeholder = st.empty()
        
        # 1. Define Liability Categories for Detection
        liab_types = ["Credit Card", "Loan", "Mortgage", "Liability"]
        
        # 2. Gather All Liability Accounts first (for the global total)
        all_liability_accounts = []
        for a in data["accounts"]:
            t = a.get("type", "")
            b = a.get("balance", 0.0)
            if t in liab_types or b < 0:
                all_liability_accounts.append(a)
        
        # Calculate Global Total (Abs value of debt)
        global_liab_total = sum(abs(a["balance"]) for a in all_liability_accounts)
        liab_header_placeholder.markdown(f"### Liabilities — ${global_liab_total:,.2f}")
        st.info("💡 Please provide details for liabilities on this page in order to see how it affects the big picture.")

        # 3. Single Liabilities Expander
        l_type_display = "Liabilities" # Display capability
        
        with st.expander(f"**{l_type_display}** — ${global_liab_total:,.2f}", expanded=True):
            ss_key_liab = "liabs_list_demo_combined"
            
            if ss_key_liab not in st.session_state:
                 # If existing data is empty, add a sample
                if not all_liability_accounts:
                    all_liability_accounts = [
                        {"id": f"liab_sample_generic", "name": "Credit Card", "institution": "Bank", "type": "Liability", "balance": 1500.0}
                    ]
                st.session_state[ss_key_liab] = all_liability_accounts
            
            # Ensure default fields
            for l in st.session_state[ss_key_liab]:
                if "name" not in l: l["name"] = ""
                if "institution" not in l: l["institution"] = ""
                if "type" not in l: l["type"] = "Liability"
                if "balance" not in l: l["balance"] = 0.0
                if "id" not in l: l["id"] = f"liab_demo_{int(datetime.now().timestamp())}_{random.randint(0, 1000)}"

            # Header
            h_cols_l = st.columns([5, 3, 0.8])
            headers_l = ["Name", "Balance", ""]
            for col, h in zip(h_cols_l, headers_l):
                if h:
                    col.markdown(f"**{h}**")
            # Rows
            updated_liab_list = []
            to_delete_liab = None
            
            for l_idx, l_row in enumerate(st.session_state[ss_key_liab]):
                r_cols_l = st.columns([5, 3, 0.8])
                
                # Name
                name_val = r_cols_l[0].text_input("Name", value="", placeholder=l_row["name"] or "Liability name", key=f"l_name_cmb_{l_idx}", label_visibility="collapsed")
                l_name = name_val if name_val else l_row["name"]
                
                # Balance
                try:
                    curr_l_bal = float(l_row.get("balance", 0.0))
                except:
                    curr_l_bal = 0.0
                bal_val = r_cols_l[1].number_input("Balance", value=None, placeholder=f"{curr_l_bal:.2f}", key=f"l_bal_cmb_{l_idx}", label_visibility="collapsed", format="%.2f")
                l_bal = bal_val if bal_val is not None else curr_l_bal
                
                # Delete
                if r_cols_l[2].button("🗑️", key=f"l_del_cmb_{l_idx}"):
                    to_delete_liab = l_idx

                updated_liab_list.append({
                    "id": l_row.get("id"),
                    "name": l_name,
                    "institution": l_row.get("institution", ""),
                    "type": l_row.get("type", "Liability"), # Preserve original type if possible, or default
                    "balance": l_bal
                })

            if to_delete_liab is not None:
                updated_liab_list.pop(to_delete_liab)
                st.session_state[ss_key_liab] = updated_liab_list
                st.rerun()

            st.session_state[ss_key_liab] = updated_liab_list

            # Add Button
            if st.button("➕ Add Liability", key="btn_add_liab_cmb"):
                st.session_state[ss_key_liab].append({
                    "id": f"liab_demo_{int(datetime.now().timestamp())}",
                    "name": "",
                    "institution": "",
                    "type": "Liability",
                    "balance": 0.0
                })
                st.rerun()
            
            _, c_save = st.columns([5, 1])
            with c_save:
                if st.button("Save", type="primary", key="save_liab_cmb", use_container_width=True):
                    new_accounts = st.session_state[ss_key_liab]
                    
                    # Logic: We are managing ALL liability accounts here.
                    # So we should gather non-liability accounts from original data, and append these new ones.
                    # Identify IDs of liabilities currently being managed
                    managed_ids = set(a.get("id") for a in st.session_state[ss_key_liab] if a.get("id"))
                    
                    # Also identify IDs of liabilities that might have been deleted (were in all_liability_accounts but not in new_accounts)
                    # Actually, safer approach:
                    # 1. Identify all accounts in `data["accounts"]` that are NOT liabilities (Bank, Investments that are positive).
                    # 2. Append `new_accounts` to them.
                    
                    # Helper to check if an account is liability (same logic as block start)
                    def is_liability(acc):
                         return acc.get("type", "") in liab_types or acc.get("balance", 0.0) < 0
                    
                    non_liability_accounts = [a for a in data["accounts"] if not is_liability(a)]
                    
                    # Wait, if I have a bank account with positive balance, it is non-liability.
                    # If I have a bank account with negative balance, it IS a liability (per logic line 1164).
                    # If I edit it here, it stays a liability.
                    # If I delete it here, it is gone.
                    # This seems correct.
                    
                    data["accounts"] = non_liability_accounts + new_accounts
                    
                    current_nw, _, _ = get_net_worth(data)
                    today_str = str(datetime.now().date())
                    existing_hist = next((h for h in data["history"] if h["date"] == today_str), None)
                    if existing_hist:
                        existing_hist["net_worth"] = current_nw
                    else:
                        data["history"].append({"date": today_str, "net_worth": current_nw})
                    
                    save_data(data)
                    rc = st.session_state.get("_reset_counter", 0)
                    st.session_state[f"hl_principal_direct_v4_{rc}"] = current_nw
                    st.success("Liabilities updated!")
                    st.rerun()
        

    # --- TAB: Budget ---
    # --- TAB: Budget ---
    with tab_budget:
        st.markdown("### Income & Expenses")
        st.info("💡 Please provide details for income and expenses on this page in order to see how it affects the big picture.")

        # Prepare Budget Data
        if "budget_list_demo" not in st.session_state:
            # Check if actual data exists, else use sample
            existing_budget = data.get("budget", [])
            if not existing_budget:
                # Add sample data
                existing_budget = [
                    {"id": f"bud_demo_sample_1", "name": "Salary", "category": "Work", "amount": 5000.0, "type": "Income", "frequency": "Monthly"},
                    {"id": f"bud_demo_sample_2", "name": "Rent / Mortgage", "category": "Housing", "amount": 2000.0, "type": "Expense", "frequency": "Monthly"}
                ]
            st.session_state.budget_list_demo = existing_budget
        
        # Ensure default fields
        for item in st.session_state.budget_list_demo:
            if "name" not in item: item["name"] = ""
            if "amount" not in item: item["amount"] = 0.0
            if "type" not in item: item["type"] = "Expense"
            if "frequency" not in item: item["frequency"] = "Monthly"
            if "id" not in item: item["id"] = f"bud_demo_{int(datetime.now().timestamp())}_{random.randint(0, 1000)}"

        # Split into income and expenses
        income_items = [i for i in st.session_state.budget_list_demo if i.get("type") == "Income"]
        expense_items = [i for i in st.session_state.budget_list_demo if i.get("type") == "Expense"]

        # --- Section 1: Income ---
        with st.expander("Monthly Income", expanded=True):
            h_cols_i = st.columns([3, 2, 2, 0.8])
            headers_i = ["Source", "Notes", "Amount", ""]
            for col, h in zip(h_cols_i, headers_i): 
                if h:
                    col.markdown(f"**{h}**")
            updated_income = []
            to_delete_income = None
            subtotal_income = 0.0
            
            for idx, row in enumerate(income_items):
                r_cols_i = st.columns([3, 2, 2, 0.8])
                # Click-to-clear pattern
                name_val = r_cols_i[0].text_input("Name", value="", placeholder=row["name"] or "Income source", key=f"i_name_demo_{idx}", label_visibility="collapsed")
                new_name = name_val if name_val else row["name"]
                
                cat_val = r_cols_i[1].text_input("Notes", value="", placeholder=row.get("category", "") or "Notes", key=f"i_cat_demo_{idx}", label_visibility="collapsed")
                new_cat = cat_val if cat_val else row.get("category", "")
                
                amt_val = r_cols_i[2].number_input("Amount", value=None, placeholder=f"{float(row['amount']):.2f}", key=f"i_amt_demo_{idx}", label_visibility="collapsed", format="%.2f")
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

            st.write("")
            st.metric("Total Income", f"${subtotal_income:,.2f}")
            
            _, c_save = st.columns([5, 1])
            with c_save:
                if st.button("Save", type="primary", key="btn_save_income_demo", use_container_width=True):
                    data["budget"] = updated_income + expense_items
                    save_data(data)
                    rc = st.session_state.get("_reset_counter", 0)
                    st.session_state[f"hl_income_direct_v4_{rc}"] = subtotal_income
                    st.success("Income updated!")
                    st.rerun()

        # --- Section 2: Expenses ---
        with st.expander("Monthly Expenses", expanded=True):
            h_cols_e = st.columns([3, 2, 2, 2, 0.8])
            headers_e = ["Kind", "Category", "Amount", "Frequency ⌵", ""]
            for col, h in zip(h_cols_e, headers_e): 
                if h:
                    col.markdown(f"**{h}**")
            updated_expenses = []
            to_delete_expense = None
            sub_exp_monthly = 0.0

            for idx, row in enumerate(expense_items):
                r_cols_e = st.columns([3, 2, 2, 2, 0.8])
                # Click-to-clear pattern
                name_val = r_cols_e[0].text_input("Name", value="", placeholder=row["name"] or "Expense", key=f"e_name_demo_{idx}", label_visibility="collapsed")
                new_name = name_val if name_val else row["name"]
                
                cat_val = r_cols_e[1].text_input("Cat", value="", placeholder=row.get("category", "") or "Category", key=f"e_cat_demo_{idx}", label_visibility="collapsed")
                new_cat = cat_val if cat_val else row.get("category", "")
                
                amt_val = r_cols_e[2].number_input("Amt", value=None, placeholder=f"{float(row['amount']):.2f}", key=f"e_amt_demo_{idx}", label_visibility="collapsed", format="%.2f")
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

            st.write("")
            st.metric("Total Expenses", f"${sub_exp_monthly:,.2f}")
            
            _, c_save = st.columns([5, 1])
            with c_save:
                if st.button("Save", type="primary", key="btn_save_expenses_demo_new", use_container_width=True):
                    data["budget"] = income_items + updated_expenses
                    save_data(data)
                    rc = st.session_state.get("_reset_counter", 0)
                    st.session_state[f"hl_expenses_direct_v4_{rc}"] = sub_exp_monthly
                    st.success("Expenses updated!")
                    st.rerun()

        # --- Section 3: Annual Bucket List ---
        with st.expander("🏆 Annual Bucket List", expanded=True):
            if "annual_list_demo" not in st.session_state:
                existing_annual = data.get("annual_expenditures", [])
                if not existing_annual:
                    existing_annual = [
                        {"id": "ann_sample_1", "name": "International Trip", "amount": 5000.0, "frequency": "Every Year", "start_age": 65}
                    ]
                st.session_state.annual_list_demo = existing_annual
            
            h_cols_a = st.columns([3, 2, 2, 2, 0.8])
            headers_a = ["Activity", "Amount", "Frequency ⌵", "Start Age", ""]
            for col, h in zip(h_cols_a, headers_a): 
                if h:
                    col.markdown(f"**{h}**")
            updated_ann = []
            to_delete_ann = None
            for idx, row in enumerate(st.session_state.annual_list_demo):
                r_cols_a = st.columns([3, 2, 2, 2, 0.8])
                # Click-to-clear pattern
                name_val = r_cols_a[0].text_input("Name", value="", placeholder=row["name"] or "Activity", key=f"ann_n_demo_{idx}", label_visibility="collapsed")
                a_name = name_val if name_val else row["name"]
                
                amt_val = r_cols_a[1].number_input("Amt", value=None, placeholder=f"{float(row['amount']):.2f}", key=f"ann_a_demo_{idx}", label_visibility="collapsed", format="%.2f")
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

            _, c_save = st.columns([5, 1])
            with c_save:
                if st.button("Save", type="primary", key="btn_save_ann_demo_new", use_container_width=True):
                    data["annual_expenditures"] = updated_ann
                    save_data(data)
                    st.success("Annual expenditures saved!")
                    st.rerun()

        st.markdown("---")
        st.subheader("Budget Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Income", f"${subtotal_income:,.2f}")
        c2.metric("Total Expenses", f"${sub_exp_monthly:,.2f}", delta_color="inverse")
        net_cash_live = subtotal_income - sub_exp_monthly
        c3.metric("Net Cashflow", f"${net_cash_live:,.2f}", delta=f"${net_cash_live:,.2f}")
        



    # --- TAB: How Long Will It Last? ---
    with tab_will_it_last:
        st.markdown("### ⏳ Will It Last?")
        st.info("💡 Adjust the market variables to see how your investments will be affected.")
        # Using columns to create "Left Panel" (Inputs) and "Right Panel" (Results)
        # Added spacer column in the middle for padding
        col_main_left, col_spacer, col_main_right = st.columns([1, 0.2, 2])
        
        # Pre-populate principal
        liquid_nw, total_assets, total_liabilities = get_net_worth(data)
        total_net_worth = total_assets - total_liabilities

        # Logic variables placeholders
        months = 0
        run_out = False
        max_years = 60
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
            years_axis = [0]
            
            run_out = False
            months = max_years * 12
            
# ... (lines 1603-1785 remain same, I will use precise TargetContent to bridge) ...
# Actually, I am jumping to line 1591 to insert the fetch logic first, 
# then I will do a separate call for the graph sliders to keep it clean.
# Let's DO ONE CALL for the fetch logic at ~line 1591.

            
            run_out = False
            months = max_years * 12
            
            for m in range(1, max_years * 12 + 1):
                # Calculate effective income for this month based on age
                sim_age_months = (current_age * 12) + m
                sim_age_years = sim_age_months / 12.0
                
                # Base Income Logic (Salary vs Pension)
                # Salary stops at planned_ret_age regardless of current status
                effective_income = curr_income 
                
                if sim_age_years >= planned_ret_age:
                    effective_income = 0.0 # Salary stops officially at this age
                
                # Pension Triggers
                if sim_age_months >= (cpp_start_age * 12):
                    effective_income += (cpp_amount or 0.0)
                if sim_age_months >= (oas_start_age * 12):
                    effective_income += (oas_amount or 0.0)
                
                # Inheritance Trigger
                if inherit_age > 0 and (inherit_amount or 0.0) > 0:
                    # Case 1: Cash/Investments -> Add at inheritance age
                    if inherit_type == "Cash / Investments":
                         if sim_age_months == (inherit_age * 12):
                             balance += (inherit_amount or 0.0)
                    
                    # Case 2: Property -> Add only if selling
                    elif inherit_type == "Property / House":
                        if sell_property and sim_age_months == (sell_age * 12):
                            balance += (inherit_amount or 0.0)

                interest = balance * monthly_return
                balance += interest
                balance += (effective_income - curr_expenses)
                
                # Subtract Annual Expenditures if it's the right month (e.g. month 1 of the year)
                if m % 12 == 1:
                    sim_age_floor = int(sim_age_years)
                    for exp in data.get("annual_expenditures", []):
                        e_amt = exp.get("amount", 0.0)
                        e_freq = exp.get("frequency", "One-time")
                        e_start = exp.get("start_age", 65)
                        
                        should_apply = False
                        if e_freq == "One-time" and sim_age_floor == e_start: should_apply = True
                        elif e_freq == "Every Year" and sim_age_floor >= e_start: should_apply = True
                        elif e_freq == "Every 2 Years" and sim_age_floor >= e_start and (sim_age_floor - e_start) % 2 == 0: should_apply = True
                        elif e_freq == "Every 5 Years" and sim_age_floor >= e_start and (sim_age_floor - e_start) % 5 == 0: should_apply = True
                        elif e_freq == "Every 10 Years" and sim_age_floor >= e_start and (sim_age_floor - e_start) % 10 == 0: should_apply = True
                        
                        if should_apply:
                            balance -= e_amt

                history_bal.append(max(0, balance))
                # years_axis.append(m / 12) <-- Old "Years from Now" logic
                years_axis.append(current_age + (m / 12)) # New "Age" logic
                
                if balance <= 0:
                    months = m
                    run_out = True
                    break
                
                if m % 12 == 0:
                    # Non-indexed Base Income (Conservative)
                    # curr_income *= (1.0) 
                    curr_expenses *= (1 + inflation / 100)

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
            
            # 2. Next multiple of 5
            next_five = ((current_age // 5) + 1) * 5
            
            # 3. Add multiples of 5 up to 110
            for val in range(next_five, 111, 5):
                if val > current_age: # Avoid duplicates if current_age works out to be a multiple
                    custom_ticks.append(val)
            
            fig_proj = px.line(x=years_axis, y=history_bal, labels={'x': 'Age', 'y': 'Balance'})
            fig_proj.update_layout(
                yaxis=dict(range=[0, y_max_proj], tickformat='$,.0f', dtick=y_dtick),
                xaxis=dict(
                    range=[current_age, current_age + max_years], # Explicit range based on calculation
                    tickvals=custom_ticks,
                    tickmode='array',
                    tickangle=0 # Force upright labels
                ),
                margin=dict(l=20, r=20, t=40, b=20),
                height=350,
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

            st.markdown("#### Investments Over Time")
            # Display Graph and Sliders side-by-side
            c_graph, c_vars = st.columns([3, 1])
            with c_graph:
                st.plotly_chart(fig_proj, use_container_width=True)
            with c_vars:
                st.markdown("<br>", unsafe_allow_html=True) # Spacer
                st.markdown("##### Market Variables")
                
                # --- CSS to force Blue Sliders ---
                st.markdown("""
                <style>
                /* Force blue sliders for this scope */
                div.stSlider > div[data-baseweb="slider"] > div > div > div[role="slider"]{
                    background-color: #0068c9 !important;
                }
                div.stSlider > div[data-baseweb="slider"] > div > div > div > div {
                        background-color: #0068c9 !important;
                }
                </style>
                """, unsafe_allow_html=True)

                inflation = st.slider("Inflation (%)", 0.0, 10.0, 3.0, 0.1, key="hl_inflation")
                annual_return = st.slider("Annual Return (%)", 0.0, 15.0, 5.0, 0.1, key="hl_return")

            # --- 2. Render Result Box (Middle) ---
            st.markdown("<br>", unsafe_allow_html=True)
            
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
            st.markdown("<br>", unsafe_allow_html=True)
            c_inputs_btm, col_space_btm, c_assump_btm = st.columns([1, 0.4, 1])
            
            with c_inputs_btm:
                st.markdown("#### Financial Inputs")
                st.markdown(f"""
                <div style="font-size:14px; margin-bottom: 5px;">
                <b>Total Monthly Income:</b> ${monthly_income:,.2f}<br>
                <b>Monthly Expenses:</b> ${monthly_expenses:,.2f}<br>
                <b>Investments:</b> ${principal:,.0f}
                </div>
                """, unsafe_allow_html=True)
                st.caption("Change these values on the **Budget** & **Assets** tabs.")

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
                <b>CPP:</b> ${cpp_amount:,.2f}/mo at age {cpp_start_age}<br>
                <b>OAS:</b> ${oas_amount:,.2f}/mo at age {oas_start_age}<br>
                <b>Inheritance:</b> {inh_str}
                </div>
                """, unsafe_allow_html=True)
                st.caption("Change these values on the **Profile** tab.")

            st.markdown("---")
            
            # Reverse Calculator Section
            st.subheader("Reverse Calculator")
            
            with st.container():
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
                        sim_bal = principal
                        sim_inc = monthly_income
                        sim_exp = mid
                        ok = True
                        for m in range(1, int(target_years * 12) + 1):
                            # Effective Income (Base + Pensions)
                            eff_inc = sim_inc
                            s_age_mo = (current_age * 12) + m
                            if s_age_mo >= (cpp_start_age * 12):
                                eff_inc += cpp_amount
                            if s_age_mo >= (oas_start_age * 12):
                                eff_inc += oas_amount
                            
                            sim_bal += (sim_bal * monthly_return)
                            sim_bal += (eff_inc - sim_exp)
                            
                            # Subtract Annual Expenditures
                            if m % 12 == 1:
                                s_age_floor = int(s_age_mo / 12)
                                for exp in data.get("annual_expenditures", []):
                                    if exp.get("frequency") == "One-time" and s_age_floor == exp.get("start_age"): sim_bal -= exp.get("amount", 0)
                                    elif exp.get("frequency") == "Every Year" and s_age_floor >= exp.get("start_age"): sim_bal -= exp.get("amount", 0)
                                    # (Simplified for reverse calc to prevent performance hit, basic every year/one-time check)

                            if sim_bal < 0:
                                ok = False
                                break
                            if m % 12 == 0:
                                # sim_inc *= (1 + inflation / 100)
                                sim_exp *= (1 + inflation / 100)
                        
                        if ok:
                            best_expenses = mid # valid, try higher spending
                            low = mid
                        else:
                            high = mid # too much spending
                    
                    monthly_withdrawal = max(0, best_expenses - monthly_income)
                    
                    st.markdown(f"""
                    <div style="background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; border: 1px solid #ffeeba;">
                        <strong>Result:</strong> To last <b>{target_years} years</b>, you can withdraw an additional
                        <h3 style="margin: 5px 0;">${monthly_withdrawal:,.2f} / month</h3>
                        (Total allowable monthly spending: ${best_expenses:,.2f})
                    </div>
                    """, unsafe_allow_html=True)
    # --- TAB: What If? ---
    with tab_what_if:
        st.markdown("### 🚀 What if")
        st.info('💡 The "What If" scenarios do not affect your real tracking data.')
        
        # 1. Manage Scenarios
        scenarios = data.get("scenarios", [])
        df_scenarios = pd.DataFrame(scenarios)
        with st.expander("🚀 Scenarios", expanded=True):
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
                         "impact": 150000.0,
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
            h_cols = st.columns([2, 1, 2.5, 2, 0.8])
            headers = ["Description", "Age", "Cost", "Frequency ⌵", ""]
            for col, h in zip(h_cols, headers):
                if h:
                    col.markdown(f"**{h}**")
            # Rows
            updated_list = []
            to_delete = None
            
            for idx, row in enumerate(st.session_state.scenarios_list_demo):
                r_cols = st.columns([2, 1, 2.5, 2, 0.8])
                
                # Force type to "Cost" since we removed the selector
                new_type = "Cost"

                # Click-to-clear pattern
                name_val = r_cols[0].text_input("Name", value="", placeholder=row["name"] or "Scenario description", key=f"sc_name_demo_{idx}", label_visibility="collapsed")
                new_name = name_val if name_val else row["name"]
                
                age_val = r_cols[1].number_input("Age", value=None, placeholder=str(int(row["age"])), min_value=18, max_value=110, key=f"sc_age_demo_{idx}", label_visibility="collapsed")
                new_age = age_val if age_val is not None else int(row["age"])
                
                impact_val = r_cols[2].number_input("Cost", value=None, placeholder=f"{float(row['impact']):.2f}", key=f"sc_impact_demo_{idx}", label_visibility="collapsed")
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
            
            st.write("")
            _, c_save = st.columns([5, 1])
            with c_save:
                if st.button("Save", type="primary", key="btn_save_scenarios_demo", use_container_width=True):
                    data["scenarios"] = st.session_state.scenarios_list_demo
                    save_data(data)
                    st.success("Scenarios saved!")
                    st.rerun()

        st.write("") # Extra padding
        st.write("")
        st.write("")

        # 2. Calculation Logic
        def run_sim(p_income, p_expenses, p_principal, p_return, p_inflation, events=None):
            bal = p_principal
            curr_return = p_return
            curr_inflation = p_inflation
            hist = [bal]
            curr_age_sim = calc_age
            
            c_inc = p_income
            c_exp = p_expenses
            
            for m in range(1, max_years * 12 + 1):
                sim_age_mo = (curr_age_sim * 12) + m
                sim_age_yr = sim_age_mo / 12.0
                
                eff_inc = c_inc
                if sim_age_yr >= planned_ret_age: eff_inc = 0.0
                
                # Pensions
                if sim_age_mo >= (cpp_start_age * 12): eff_inc += cpp_amount
                if sim_age_mo >= (oas_start_age * 12): eff_inc += oas_amount
                
                # Default Inheritance Logic
                if inherit_age > 0 and inherit_amount > 0:
                    if inherit_type == "Cash / Investments" and sim_age_mo == (inherit_age * 12):
                        bal += inherit_amount
                    elif inherit_type == "Property / House" and sell_property and sim_age_mo == (sell_age * 12):
                        bal += inherit_amount

                # --- Apply Scenario Events ---
                if events:
                    for ev in events:
                        e_age = ev.get("age", 0)
                        e_impact = ev.get("impact", 0)
                        e_ret = ev.get("sc_return", 0)
                        e_inf = ev.get("sc_inflation", 0)
                        e_type = ev.get("type", "Expense")
                        e_freq = ev.get("frequency", "One-time")
                        
                        # Check if the event triggers this month
                        is_trigger = False
                        if e_freq == "One-time":
                            is_trigger = (sim_age_mo == (e_age * 12))
                        elif e_freq in ["Monthly", "Until End of Plan"]:
                            is_trigger = (sim_age_mo >= (e_age * 12))
                        elif e_freq == "Annually":
                            is_trigger = (sim_age_mo >= (e_age * 12)) and ((sim_age_mo - (e_age * 12)) % 12 == 0)
                        elif e_freq == "Twice per year":
                            is_trigger = (sim_age_mo >= (e_age * 12)) and ((sim_age_mo - (e_age * 12)) % 6 == 0)
                        elif e_freq == "Every 2 years":
                            is_trigger = (sim_age_mo >= (e_age * 12)) and ((sim_age_mo - (e_age * 12)) % 24 == 0)
                        elif e_freq == "Every 3 years":
                            is_trigger = (sim_age_mo >= (e_age * 12)) and ((sim_age_mo - (e_age * 12)) % 36 == 0)
                        elif e_freq == "Every 5 years":
                            is_trigger = (sim_age_mo >= (e_age * 12)) and ((sim_age_mo - (e_age * 12)) % 60 == 0)
                        elif e_freq == "Every 10 years":
                            is_trigger = (sim_age_mo >= (e_age * 12)) and ((sim_age_mo - (e_age * 12)) % 120 == 0)

                        if is_trigger:
                            # Cashflows
                            if e_type in ["Financial Gain", "Income", "Asset"]: 
                                if e_freq == "One-time": bal += e_impact # One-time income hits balance
                                else: eff_inc += e_impact # Recurring income hits monthly flow
                            elif e_type in ["Cost", "Expense", "Financial Cost"]: 
                                if e_freq == "One-time": bal -= abs(e_impact) # One-time expense hits balance
                                else: eff_inc -= abs(e_impact) # Recurring expense hits monthly flow
                            else: 
                                # Fallback: treat as Cost if type is unknown/null
                                if e_freq == "One-time": bal -= abs(e_impact)
                                else: eff_inc -= abs(e_impact)
                            
                            # Rates (Update if non-zero)
                            if e_ret > 0: curr_return = e_ret
                            if e_inf > 0: curr_inflation = e_inf
                
                # Standard Growth
                interest = bal * (curr_return / 100 / 12)
                bal += interest
                bal += (eff_inc - c_exp)
                
                # Annual Expenditures (Real)
                if m % 12 == 1:
                    sim_age_f = int(sim_age_yr)
                    for exp in data.get("annual_expenditures", []):
                        if exp.get("frequency") == "One-time" and sim_age_f == exp.get("start_age"): bal -= exp.get("amount", 0)
                        elif exp.get("frequency") == "Every Year" and sim_age_f >= exp.get("start_age"): bal -= exp.get("amount", 0)

                hist.append(max(0, bal))
                if bal <= 0 and m < max_years * 12:
                    hist += [0] * (max_years * 12 - m)
                    break
                
                if m % 12 == 0:
                    c_exp *= (1 + curr_inflation / 100)
            
            return hist

        # Run Simulations
        base_h = run_sim(monthly_income, monthly_expenses, principal, annual_return, inflation)
        scen_h = run_sim(monthly_income, monthly_expenses, principal, annual_return, inflation, events=data.get("scenarios", []))
        
        # 3. Visualization
        st.markdown("#### Comparison: Net Worth Over Time")
        
        sim_years = list(range(max_years + 1))
        sim_ages = [calc_age + y for y in sim_years]
        
        fig_comp = go.Figure()
        
        # Base Case
        fig_comp.add_trace(go.Scatter(
            x=sim_ages, y=base_h[::12] if len(base_h) > max_years else base_h, 
            name="Current Plan (Base)",
            line=dict(color="#636EFA", width=2, dash='dot')
        ))
        
        # Scenario Case
        fig_comp.add_trace(go.Scatter(
            x=sim_ages, y=scen_h[::12] if len(scen_h) > max_years else scen_h, 
            name="What-If Scenario",
            line=dict(color="#00CC96", width=4)
        ))

        # Add vertical lines for each scenario event
        for s in data.get("scenarios", []):
            s_age = s.get("age")
            if s_age:
                fig_comp.add_vline(
                    x=s_age, 
                    line_width=1, 
                    line_dash="dash", 
                    line_color="gray", 
                    annotation_text=s.get("name", ""), 
                    annotation_position="top left",
                    annotation=dict(font=dict(size=12, color="gray"))
                )
        
        fig_comp.update_layout(
            xaxis_title="Age",
            yaxis_title="Account Balance",
            yaxis=dict(tickformat='$,.0f'),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=450,
            font=dict(size=14)
        )
        
        st.plotly_chart(fig_comp, use_container_width=True)
        
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
