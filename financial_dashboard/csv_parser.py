import pandas as pd
import io

def detect_format(df):
    # Normalize col names: lowercase, remove ($) and spaces for checking
    cols = [str(c).lower().replace(' ($)', '').replace('($)', '').strip() for c in df.columns]
    
    # Fidelity usually has 'run date', 'action', 'symbol', 'description', 'amount'
    # "price" or "price ($)" -> become "price" in our normalized check
    if any("fidelity" in str(c).lower() for c in df.columns) or \
       ("action" in cols and "symbol" in cols):
        return "Fidelity"
    
    # BMO usually has 'transaction date', 'posting date', 'transaction amount', 'description'
    # BMO CSVs sometimes have no headers, or specific headers.
    # Let's assume standard BMO export: Card #, Transaction Type, Date, Amount, Description
    if "transaction date" in cols or "posting date" in cols:
        return "BMO"
    
    return "Unknown"

def parse_fidelity(file):
    """
    Parses Fidelity CSV export.
    Expected columns: Run Date,Account,Action,Symbol,Description,Type,Quantity,Price ($),Commission ($),Fees ($),Accrued Interest ($),Amount ($),Settlement Date
    """
    try:
        df = pd.read_csv(file)
        # Drop rows that are just info text at bottom
        # Locate correct header row if needed, but for now assume standard
        
        # Helper to find col regardless of ' ($)' suffix
        def get_val(row, bases):
            for col in df.columns:
                norm = col.lower().replace(' ($)', '').replace('($)', '').strip()
                if norm in bases:
                    return row[col]
            return None

        transactions = []
        for _, row in df.iterrows():
            # Amount might be "Amount ($)" or just "Amount"
            amt_val = get_val(row, ['amount'])
            date_val = get_val(row, ['date', 'run date'])
            desc_val = get_val(row, ['description']) or 'Fidelity Transaction'
            
            if pd.isna(amt_val) or pd.isna(date_val):
                continue

            amt = str(amt_val).replace('$', '').replace(',', '')
            try:
                amt_float = float(amt)
            except:
                continue
                
            transactions.append({
                "date": str(pd.to_datetime(date_val)).split(' ')[0],
                "description": desc_val,
                "amount": amt_float,
                "category": "Investment" if amt_float > 0 else "Expense", 
                "account": "Fidelity",
                "source_file": "csv_import"
            })
        return transactions
    except Exception as e:
        return []

def parse_bmo(file):
    """
    Parses BMO CSV export.
    BMO offers different exports. One common format for specialized Credit Cards / Banking:
    first line might be account info.
    Let's try a robust approach reading with pandas.
    """
    try:
        # BMO sometimes has 3-4 lines of header junk.
        # We'll try to find the header row.
        content = file.getvalue().decode('utf-8')
        lines = content.split('\n')
        header_row = 0
        for i, line in enumerate(lines):
            if "Transaction Date" in line or "Date" in line:
                header_row = i
                break
        
        file.seek(0)
        df = pd.read_csv(file, skiprows=header_row)
        
        transactions = []
        for _, row in df.iterrows():
            # Find date column
            date_val = row.get('Transaction Date') or row.get('Date')
            
            # Find amount
            amt_val = row.get('Transaction Amount') or row.get('Amount')
            if isinstance(amt_val, str):
                amt_val = amt_val.replace(',', '').replace('$', '')
            
            desc_val = row.get('Description') or row.get('Transaction Description')
            
            try:
                amt_float = float(amt_val)
            except:
                continue

            transactions.append({
                "date": str(pd.to_datetime(date_val)).split(' ')[0],
                "description": desc_val,
                "amount": amt_float,
                "category": "Expense" if amt_float < 0 else "Income",
                "account": "BMO",
                "source_file": "csv_import"
            })
        return transactions
    except Exception as e:
        return []

def parse_csv(uploaded_file):
    """
    Main entry point. Detects format and routes to specific parser.
    Returns list of dicts: {date, description, amount, category, account}
    """
    # Peek at first few bytes to sniff, or just try reading
    try:
        df_peek = pd.read_csv(uploaded_file)
        uploaded_file.seek(0) # Reset
        
        fmt = detect_format(df_peek)
        
        if fmt == "Fidelity":
            return parse_fidelity(uploaded_file)
        elif fmt == "BMO":
            return parse_bmo(uploaded_file)
        else:
            # Fallback: Try generic parsing
            # Look for 'date', 'amount', 'description' columns
            cols = [c.lower() for c in df_peek.columns]
            # More robust keyword check
            date_keywords = ['date', 'time', 'day']
            amt_keywords = ['amount', 'amt', 'value', 'cost', 'price', 'total']
            
            has_date = any(any(k in c for k in date_keywords) for c in cols)
            has_amt = any(any(k in c for k in amt_keywords) for c in cols)
            
            if has_date and has_amt:
                # Generic Parser
                return parse_generic(df_peek)
            return []
    except:
        return []

def parse_generic(df):
    # Simplistic mapper
    txs = []
    # Identify col names
    cols = df.columns
    
    date_keywords = ['date', 'time', 'day']
    amt_keywords = ['amount', 'amt', 'value', 'cost', 'price', 'total']
    desc_keywords = ['desc', 'memo', 'detail', 'narrative', 'name']

    date_col = next((c for c in cols if any(k in c.lower() for k in date_keywords)), None)
    amt_col = next((c for c in cols if any(k in c.lower() for k in amt_keywords)), None)
    desc_col = next((c for c in cols if any(k in c.lower() for k in desc_keywords)), None)
    
    if not date_col or not amt_col:
        return []

    for _, row in df.iterrows():
        try:
            val = str(row[amt_col]).replace('$', '').replace(',', '')
            amt = float(val)
            txs.append({
                "date": str(pd.to_datetime(row[date_col])).split(' ')[0],
                "description": row[desc_col] if desc_col else "Imported Transaction",
                "amount": amt,
                "category": "Uncategorized",
                "account": "Imported"
            })
        except:
            continue
    return txs
