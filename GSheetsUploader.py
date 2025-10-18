import csv
import json
import datetime
from google.oauth2 import service_account
import gspread

CRED_FILE = ""
SPREADSHEET_FILE_ID = "1zfMflryncer60G9faftGMbGpNnnt24WQORy6CeIA6IQ"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def getCredentials():
    creds = service_account.Credentials.from_service_account_file(CRED_FILE).with_scopes(SCOPES)
    return creds
    
def uploadCsvFile(csvPath: str, date: datetime.date):
    creds = getCredentials()
    sheetsClient = gspread.authorize(creds)
    spreadsheet = sheetsClient.open_by_key(SPREADSHEET_FILE_ID)
    worksheet = spreadsheet.add_worksheet(title=date.isoformat(), rows=0, cols=0)
    with open(csvPath) as csvFile:
        content = list(csv.reader(csvFile))
        worksheet.append_rows(content)
