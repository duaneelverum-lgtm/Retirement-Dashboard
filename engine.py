def calculate_trajectory(
    current_age,
    retirement_age,
    current_net_worth,
    monthly_income,
    monthly_expenses,
    bucket_rows=[],
    interest_rate=0.05,
    inflation_rate=0.02,
    is_scenario=False,
    splurge_items=[],
    inheritance_amount=0,
    inheritance_age=0,
    cpp_start_age=65,
    cpp_amount=804,
    oas_start_age=65,
    oas_amount=728,
    end_age=100
):
    """
    Calculates the net worth trajectory until end_age.
    Returns a list of dictionaries with age and net_worth.
    """
    trajectory = []
    current_nw = current_net_worth
    
    for age in range(current_age, end_age + 1):
        # 1. Record state at start of year
        trajectory.append({"age": age, "net_worth": int(current_nw)})
        
        # 2. Add Annual Cash Flow
        # Income only persists until retirement age
        if age < retirement_age:
            annual_flow = (monthly_income - monthly_expenses) * 12
        else:
            annual_flow = -monthly_expenses * 12
        
        # 3. Add CPP if age >= start age
        if age >= cpp_start_age:
            annual_flow += cpp_amount * 12
            annual_flow += cpp_amount * 12
            
        # 4. Add OAS if age >= start age
        if age >= oas_start_age:
            # Factor in 10% increase at age 75+
            actual_oas = oas_amount
            if age >= 75:
                actual_oas *= 1.10
            annual_flow += actual_oas * 12
            
        # 5. Subtract Bucket List items for this age
        for item in bucket_rows:
            if item.get('start_age') == age:
                annual_flow -= item.get('amount', 0)
        
        # 6. Handle Scenario-specific events
        if is_scenario:
            for item in splurge_items:
                start_age = item.get('age')
                cost = item.get('cost')
                freq = item.get('frequency', 'Once')
                
                if start_age is not None and cost is not None and age >= start_age:
                    if freq == 'Once':
                        if age == start_age:
                            annual_flow -= cost
                    elif freq == 'Annually':
                        annual_flow -= cost
                    elif freq == 'Bi-annually':
                        if (age - start_age) % 2 == 0:
                            annual_flow -= cost
                    elif freq == 'Semi-annually':
                        # Twice per year
                        annual_flow -= cost * 2
                    elif freq == 'Every 5 years':
                        if (age - start_age) % 5 == 0:
                            annual_flow -= cost
            if inheritance_age is not None and inheritance_amount is not None:
                if age == inheritance_age:
                    annual_flow += inheritance_amount
        
        # 7. Apply Growth and Inflation logic
        real_growth = interest_rate - inflation_rate
        current_nw = (current_nw + annual_flow) * (1 + real_growth)
        
        # Avoid dramatic negative numbers for chart clarity
        if current_nw < -10000000:
            current_nw = -10000000
            
    return trajectory
