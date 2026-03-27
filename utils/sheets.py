import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import json
import streamlit as st

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly"
]

def get_gspread_client(service_account_info: dict):
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return gspread.authorize(creds)


def load_sheet(client, sheet_url: str, worksheet_name: str = None) -> pd.DataFrame:
    spreadsheet = client.open_by_url(sheet_url)
    if worksheet_name:
        ws = spreadsheet.worksheet(worksheet_name)
    else:
        ws = spreadsheet.get_worksheet(0)
    data = ws.get_all_records()
    return pd.DataFrame(data), spreadsheet, ws


def write_results_to_sheet(ws, df: pd.DataFrame, result_col_map: dict):
    """
    result_col_map: { 'generated_title': 'Col Header In Sheet', ... }
    Writes result columns back by matching row index.
    Assumes sheet has a header row and data starts at row 2.
    """
    headers = ws.row_values(1)

    for col_key, col_header in result_col_map.items():
        if col_header not in headers:
            # Append new column header
            headers.append(col_header)
            col_index = len(headers)
            ws.update_cell(1, col_index, col_header)
        else:
            col_index = headers.index(col_header) + 1

        # Write each row value
        for i, value in enumerate(df[col_key].tolist()):
            ws.update_cell(i + 2, col_index, str(value) if pd.notna(value) else "")
