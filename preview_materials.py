from app.utils.excel_parser import preview_excel
import json

file_path = '/Users/dumessi/Library/Mobile Documents/com~apple~CloudDocs/macos-sharing/cursor-project/pricing-agent-ocr-dic/material-list/material-list-20241207.xlsx'
preview = preview_excel(file_path)

print('Columns:', json.dumps(preview['columns'], ensure_ascii=False, indent=2))
print('\nSample row:', json.dumps(preview['sample_rows'][0], ensure_ascii=False, indent=2))
print(f'\nTotal rows: {preview["total_rows"]}') 