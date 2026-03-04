import xlsxwriter

# 1. Setup
file_name = 'Internal_Report.xlsx'
token_url = 'http://canarytokens.com/articles/0rmdxx6g0ah0ki7ouyeq9rug0/photo1.jpg'

# 2. Create workbook
workbook = xlsxwriter.Workbook(file_name)
worksheet = workbook.add_worksheet()

# 3. Add some data
worksheet.write('A1', 'Project Alpha - Confidential')

# 4. Write the IMAGE formula into a cell (e.g., A10)
# Note: Excel will only fetch this image when the file is opened by a user.
image_formula = f'=IMAGE("{token_url}")'
worksheet.write_formula('A10', image_formula)

# 5. Optional: Hide the cell
# Set the row height to a tiny value so the user doesn't see the logo
worksheet.set_row(9, 0.1) 

# 6. Finalize
workbook.close()

print(f"File '{file_name}' created. No network request was made to the token URL.")