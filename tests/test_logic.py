import pytest
import pandas as pd
# Import functions from app.py. 
# Note: pytest needs to be run from the directory containing app.py or we need to adjust python path.
# We will assume running from root.
from app import run_financial_simulation, get_cpp_estimate, get_oas_estimate

# --- Government Benefits Tests ---

def test_cpp_estimate_standard():
    # Age 65 should be standard ~803.76
    assert get_cpp_estimate(65) == 803.76

def test_cpp_estimate_early():
    # Age 60 is 5 years early. 0.6% * 60 months = 36% reduction.
    # 803.76 * (1 - 0.36) = 803.76 * 0.64 = 514.41
    expected = round(803.76 * (1 - (65-60)*0.072), 2)
    assert get_cpp_estimate(60) == expected

def test_oas_estimate_standard():
    # Age 65 should be ~727.67
    assert get_oas_estimate(65) == 727.67

# --- Financial Simulation Tests ---

def test_simulation_basics():
    current_age = 40
    net_worth = 100000
    annual_spend = 50000
    retirement_age = 65
    gov_benefits = {
        'cpp_start': 65, 'cpp_amt': 800,
        'oas_start': 65, 'oas_amt': 700
    }
    
    df = run_financial_simulation(current_age, net_worth, annual_spend, retirement_age, gov_benefits)
    
    # Check structure
    assert 'Age' in df.columns
    assert 'Net Worth' in df.columns
    assert len(df) == (100 - 40 + 1)
    
    # Check initial values (approx check due to year 1 logic)
    # The simulation logic calculates year-end.
    # Year 40: Start 100k -> Grow 6% -> + Cashflow (0 if working)
    # 100000 * 1.06 = 106000
    assert df.iloc[0]['Net Worth'] == 106000

def test_splurge_impact():
    current_age = 40
    net_worth = 100000
    annual_spend = 50000
    retirement_age = 65
    gov_benefits = {'cpp_start':65, 'cpp_amt':0, 'oas_start':65, 'oas_amt':0}
    
    # Run Baseline
    df_base = run_financial_simulation(current_age, net_worth, annual_spend, retirement_age, gov_benefits)
    
    # Run Splurge (10k at 40)
    df_splurge = run_financial_simulation(current_age, net_worth, annual_spend, retirement_age, gov_benefits,
                                          splurge_cost=10000, splurge_age=current_age)
    
    # Net Worth at age 40 (End of Year)
    # Base: 100000 * 1.06 = 106000
    # Splurge: (100000 - 10000) * 1.06 = 90000 * 1.06 = 95400
    
    assert df_base.iloc[0]['Net Worth'] == 106000
    assert df_splurge.iloc[0]['Net Worth'] == 95400
    
    # Final Estate should be lower
    assert df_splurge.iloc[-1]['Net Worth'] < df_base.iloc[-1]['Net Worth']
