import logging
from typing import Any, List

import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

from telegram_bot.core.utils import create_keyfile_dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    def __init__(self, share_emails: List[str] = None):
        self.keyfile_dict = create_keyfile_dict()
        self.scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.creds = ServiceAccountCredentials.from_json_keyfile_dict(keyfile_dict=self.keyfile_dict, scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        self.share_emails = share_emails

    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert non-JSON serializable columns into strings."""
        for column in df.columns:
            df[column] = df[column].astype(str)
        return df

    def get_sheet(self, sheet_name: str) -> gspread.Spreadsheet:
        """Retrieve a Google Sheet by its name."""
        try:
            return self.client.open(sheet_name)
        except gspread.SpreadsheetNotFound:
            logger.error(f"Sheet '{sheet_name}' not found.")
            raise
        except Exception as e:
            logger.error(f"Error retrieving sheet '{sheet_name}': {e}")
            raise

    def create_sheet(self, sheet_name: str) -> gspread.Spreadsheet:
        """Create a new Google Sheet."""
        try:
            sheet = self.client.create(sheet_name)
            logger.info(f"Sheet '{sheet_name}' created.")
            sheet.share(None, perm_type="anyone", role="writer")
            if self.share_emails:
                for email in self.share_emails:
                    sheet.share(email, perm_type="user", role="writer")
            return sheet
        except Exception as e:
            logger.error(f"Error creating sheet '{sheet_name}': {e}")
            raise

    def create_worksheet(self, sheet: gspread.Spreadsheet, worksheet_name: str) -> gspread.Worksheet:
        """Create a new worksheet in the specified Google Sheet."""
        try:
            worksheet = sheet.add_worksheet(worksheet_name, rows=100, cols=10)
            logger.info(f"Worksheet '{worksheet_name}' created.")
            return worksheet
        except Exception as e:
            logger.error(f"Error creating worksheet '{worksheet_name}': {e}")
            raise

    def get_table_names(self, sheet: gspread.Spreadsheet) -> List[str]:
        """Get the names of the worksheets in the Google Sheet."""
        return [worksheet.title for worksheet in sheet.worksheets()]

    def get_header(self, sheet: gspread.Spreadsheet, worksheet_name: str) -> List[str]:
        """Get the headers of a specific worksheet."""
        worksheet = sheet.worksheet(worksheet_name)
        return worksheet.row_values(1)

    def import_dataframe(self, sheet: gspread.Spreadsheet, df: pd.DataFrame, worksheet_name: str) -> gspread.Worksheet:
        """Import a pandas DataFrame into a Google Sheet."""
        try:
            worksheet = sheet.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(worksheet_name, rows=1, cols=1)

        df = self._prepare_dataframe(df)
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        return worksheet

    def export_dataframe(self, sheet: gspread.Spreadsheet, worksheet_name: str) -> pd.DataFrame:
        """Export a Google Sheet into a pandas DataFrame."""
        try:
            worksheet = sheet.worksheet(worksheet_name)
            return pd.DataFrame(worksheet.get_all_records())
        except gspread.WorksheetNotFound:
            logger.error(f"Worksheet '{worksheet_name}' not found.")
            raise

    def add_row(self, sheet: gspread.Spreadsheet, worksheet_name: str, row_data: List[Any]) -> None:
        """Add a row to the specified worksheet in the Google Sheet."""
        try:
            worksheet = sheet.worksheet(worksheet_name)
            worksheet.append_row(row_data, value_input_option="USER_ENTERED")
        except Exception as e:
            logger.error(f"Error adding row to worksheet '{worksheet_name}': {e}")
            raise

    def get_public_link(self, sheet: gspread.Spreadsheet) -> str:
        """Get the public link to the specified worksheet in the Google Sheet."""
        try:
            return f"https://docs.google.com/spreadsheets/d/{sheet.id}/edit"
        except Exception as e:
            logger.error(f"Error retrieving public link for sheet '{sheet.title}': {e}")
            raise
