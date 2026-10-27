import csv
import io
from app.extensions import db
from app.data_collection.services import create_activity_record


class CsvImporter:
    """Service class for batch processing and validating CSV activity files (UML S1)."""

    def __init__(self):
        self.error_log: list[str] = []
        self.valid_count: int = 0

    def process(self, file_storage, user_id: str) -> dict:
        """Parses, validates, and imports records from an uploaded CSV file stream."""
        self.error_log.clear()
        self.valid_count = 0

        # Handle file stream or bytes
        if hasattr(file_storage, 'stream'):
            stream = io.TextIOWrapper(file_storage.stream, encoding='utf-8')
        elif isinstance(file_storage, (bytes, bytearray)):
            stream = io.StringIO(file_storage.decode('utf-8'))
        elif hasattr(file_storage, 'read'):
            raw = file_storage.read()
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8')
            stream = io.StringIO(raw)
        else:
            raise ValueError("Unsupported file format or stream.")

        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("CSV file is empty or missing headers.")

        for row_idx, row in enumerate(reader, start=1):
            try:
                self.validate_and_save_row(row, user_id)
                self.valid_count += 1
            except Exception as e:
                self.error_log.append(f"Row {row_idx}: {str(e)}")

        return {
            "inserted": self.valid_count,
            "errors": self.error_log,
            "total_rows": self.valid_count + len(self.error_log)
        }

    def validate_and_save_row(self, row: dict, user_id: str):
        """Validates and creates an individual activity record from a CSV row."""
        return create_activity_record(row, user_id)
