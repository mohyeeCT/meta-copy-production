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
    Writes result columns back to the sheet using batch updates.
    Uses a single API call per column instead of one per cell.

    result_col_map: { df_col_key: sheet_column_header, ... }
    Assumes sheet has a header row and data starts at row 2.
    """
    from gspread.utils import rowcol_to_a1

    headers = ws.row_values(1)
    updates = []

    for col_key, col_header in result_col_map.items():
        if col_key not in df.columns:
            continue

        # Find or create the column
        if col_header not in headers:
            headers.append(col_header)
            col_index = len(headers)
            # Write header in same batch
            updates.append({
                "range": rowcol_to_a1(1, col_index),
                "values": [[col_header]]
            })
        else:
            col_index = headers.index(col_header) + 1

        # Build column values as a vertical range (single batch call)
        col_letter = rowcol_to_a1(1, col_index)[:-1]  # e.g. "D"
        start_row  = 2
        end_row    = start_row + len(df) - 1
        range_str  = f"{col_letter}{start_row}:{col_letter}{end_row}"

        values = [
            [str(v) if pd.notna(v) and str(v) != "None" else ""]
            for v in df[col_key].tolist()
        ]

        updates.append({"range": range_str, "values": values})

    if updates:
        ws.spreadsheet.values_batch_update({
            "valueInputOption": "RAW",
            "data": updates
        })
