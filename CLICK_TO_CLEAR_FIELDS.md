# Click-to-Clear Fields Implementation

## Summary
All numeric input fields across dashboard_demo.py now use the "click-to-clear" pattern where:
- Fields display with `value=None` (empty on focus)
- Placeholders show the current/default value
- When user clicks, field is empty and ready for new input
- If user doesn't enter anything, the previous value is preserved

## Updated Fields

### 1. Personal Details Tab (Profile)
- ✅ **Target Retirement Age** - Placeholder shows saved value or "65"
- ✅ **Plan Until Age (Life Expectancy)** - Placeholder shows saved value or "95"

### 2. Government Benefits (Profile Tab)
- ✅ **CPP Amount ($/mo)** - Placeholder shows "0.00"
- ✅ **OAS Amount ($/mo)** - Placeholder shows "0.00"

### 3. Inheritance Section (Profile Tab)
- ✅ **Inheritance Age** - Placeholder shows "0"
- ✅ **Amount ($)** - Placeholder shows "0.00"
- ✅ **Sell Age** (conditional) - Placeholder shows calculated default age

### 4. How Long Will It Last? Tab
- ✅ **Total Monthly Income (Base)** - Placeholder shows budget total
- ✅ **Monthly Expenses** - Placeholder shows budget total
- ✅ **Retirement Plan Balance** - Placeholder shows current net worth
- ✅ **For your savings to last (Years)** - Placeholder shows "30"

## Implementation Pattern

```python
# Before (old pattern)
value = st.number_input("Label", value=saved_value, ...)

# After (click-to-clear pattern)
input_var = st.number_input("Label", value=None, placeholder=str(saved_value), ...)
value = input_var if input_var is not None else saved_value
```

## User Experience

1. **First Time Users**: See placeholders with suggested defaults
2. **Returning Users**: See placeholders with their saved values
3. **Editing**: Click field → Empty and ready for new input
4. **Skipping**: Leave empty → Previous value is preserved
5. **Clearing**: Can truly clear by entering 0 or deleting

## Benefits

- ✅ No accidental edits from pre-filled values
- ✅ Clear visual indication of current values (in placeholder)
- ✅ Easy to enter new values without selecting/deleting
- ✅ Preserves data if user doesn't make changes
- ✅ Consistent behavior across all numeric inputs

## Testing Checklist

- [ ] Personal Details - Retirement Age
- [ ] Personal Details - Life Expectancy
- [ ] Government Benefits - CPP Amount
- [ ] Government Benefits - OAS Amount
- [ ] Inheritance - Age
- [ ] Inheritance - Amount
- [ ] Inheritance - Sell Age (when applicable)
- [ ] How Long Will It Last - Income
- [ ] How Long Will It Last - Expenses
- [ ] How Long Will It Last - Balance
- [ ] Reverse Calculator - Target Years

All fields should:
1. Show placeholder text when empty
2. Clear completely when clicked
3. Preserve previous value if left empty on save
4. Accept new values when entered
