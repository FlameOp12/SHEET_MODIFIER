from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import time
from threading import Thread

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://*", "https://*"]}}, supports_credentials=True)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

requests_sheet = client.open("Leave_record").worksheet("Sheet6")
tz = pytz.timezone('Asia/Kolkata')

def check_and_delete_rows():
    try:
        # Get all values including empty rows
        all_values = requests_sheet.get_all_values()
        headers = all_values[0]
        rows = all_values[1:]  # Skip header row
        
        today = datetime.now(tz).date()
        rows_to_delete = []
        
        for row_idx, row in enumerate(rows):
            # Skip empty rows
            if not any(row):
                continue
                
            # Map row data to headers
            record = dict(zip(headers, row))
            status = record.get('Status', '').strip()
            out_date_str = record.get('OutDate', '').strip()
            
            # Check conditions
            if status == 'OUT' and out_date_str:
                try:
                    in_date = datetime.strptime(out_date_str, '%d/%m/%Y').date()
                except ValueError:
                    print(f"Invalid date format in row {row_idx + 2}: {out_date_str}")
                    continue
                
                if in_date < today:
                    actual_row_num = row_idx + 2  # Sheet rows are 1-based
                    rows_to_delete.append(actual_row_num)
        
        # Delete rows from the end to avoid shifting issues
        for row_num in reversed(rows_to_delete):
            try:
                requests_sheet.delete_rows(row_num)
                print(f"Deleted row {row_num}")
            except gspread.exceptions.APIError as e:
                print(f"Failed to delete row {row_num}: {str(e)}")
        
        print(f"Deleted {len(rows_to_delete)} rows. Next check in 24 hour.")
    
    except Exception as e:
        print(f"Error occurred: {str(e)}")

def background_task():
    while True:
        check_and_delete_rows()
        time.sleep(86400)  # Check every hour

@app.route('/')
def index():
    return "Flask app is running with background task."

if __name__ == '__main__':
    thread = Thread(target=background_task)
    thread.daemon = True
    thread.start()
    app.run(debug=True, use_reloader=False, port=5000)