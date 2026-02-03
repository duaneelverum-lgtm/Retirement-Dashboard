import pandas as pd
import pdfplumber
import io
import csv_parser

def parse_pdf(uploaded_file):
    """
    Parses PDF statements. 
    This is tricky and template-specific. 
    We will look for tables that resemble statements (Date, Desc, Amount).
    """
    transactions = []
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    # Check if table has headers we like
                    if not table: continue
                    
                    # Simple heuristic: Look for 3-5 Columns where one is Date, one is Amount
                    for row in table:
                        # Clean row
                        row = [x for x in row if x]
                        if len(row) < 3: continue
                        
                        # Try to parse date in first col
                        date_str = row[0]
                        try:
                            # Loose date parsing
                            parsed_date = pd.to_datetime(date_str)
                            # Look for amount in last col
                            amt_str = row[-1].replace('$', '').replace(',', '')
                            
                            # Check if negative usually means cr/dr
                            is_negative = False
                            if "DR" in amt_str: is_negative = True
                            if "(" in amt_str: is_negative = True
                            
                            amt_val = float(amt_str.replace('DR','').replace('CR','').replace('(','').replace(')',''))
                            if is_negative: amt_val = -amt_val
                            
                            # We found a valid line!
                            transactions.append({
                                "date": str(parsed_date).split(' ')[0],
                                "description": " ".join(row[1:-1]), # Middle cols are desc
                                "amount": amt_val,
                                "category": "Expense" if amt_val < 0 else "Income",
                                "account": "PDF Import",
                                "source_file": uploaded_file.name
                            })
                        except:
                            continue
        
        # If no transactions found (or even if they were), let's check for a "Summary" Balance
        # This is for the "Investment Snapshot" feature
        if not transactions:
            uploaded_file.seek(0)
            with pdfplumber.open(uploaded_file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
                
                # Look for keywords
                # "Ending Value", "Portfolio Value", "Total Net Worth", "Total Assets"
                import re
                # Regex for "Total Value $12,345.67" or "Ending Balance: 12,345.67"
                # This is a bit rough, but works for many statements
                patterns = [
                    r"Ending Value[:\s]+[\$]?([0-9,]+\.[0-9]{2})",
                    r"Portfolio Value[:\s]+[\$]?([0-9,]+\.[0-9]{2})",
                    r"Total Value[:\s]+[\$]?([0-9,]+\.[0-9]{2})",
                    r"Total Net Worth[:\s]+[\$]?([0-9,]+\.[0-9]{2})",
                    r"Ending Balance[:\s]+[\$]?([0-9,]+\.[0-9]{2})"
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        val_str = match.group(1).replace(',', '')
                        val_float = float(val_str)
                        
                        # Find a date?
                        date_match = re.search(r"(\d{2}/\d{2}/\d{4})", full_text)
                        date_val = date_match.group(1) if date_match else "Today"
                        if date_val != "Today":
                             date_val = str(pd.to_datetime(date_val)).split(' ')[0]
                        else:
                             # If we can't find a date, use today's date for the snapshot
                             from datetime import datetime
                             date_val = str(datetime.now().date())

                        transactions.append({
                            "date": date_val,
                            "description": "Portfolio Value Snapshot",
                            "amount": val_float,
                            "category": "Balance Update", # Special Category
                            "account": "Investment Portfolio", # Default name, dashboard can prompt?
                            "source_file": uploaded_file.name
                        })
                        break

    except Exception as e:
        print(f"PDF Parse Error: {e}")
        return []
    
    return transactions

def parse_file(uploaded_file):
    filename = uploaded_file.name.lower()
    if filename.endswith('.csv'):
        # Delegate to the robust CSV parser
        return csv_parser.parse_csv(uploaded_file)
    elif filename.endswith('.pdf'):
        return parse_pdf(uploaded_file)
    return []
