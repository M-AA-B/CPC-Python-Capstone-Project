import csv
import io
from app.data_collection.services import create_activity_record


class CsvImporter:
    """Service class for batch processing and validating CSV activity files (UML S1 & Hometask 1)."""

    def __init__(self, encoding: str = 'utf-8'):
        """Constructor: Proper state initialization (Hometask 1)."""
        self._encoding = encoding
        self._error_log: list[str] = []
        self._valid_count: int = 0

    # --- Initialization Methods (Hometask 1) ---
    def initialize_session(self) -> None:
        """Resets import counters and error logs for a new upload session."""
        self._error_log.clear()
        self._valid_count = 0

    # --- Encapsulation: Getters & Setters (Hometask 1) ---
    @property
    def encoding(self) -> str:
        """Getter for file encoding."""
        return self._encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        """Setter for encoding."""
        if not value:
            raise ValueError("Encoding cannot be empty.")
        self._encoding = value

    @property
    def error_log(self) -> list[str]:
        """Accessor (getter) for error log list."""
        return list(self._error_log)

    @property
    def valid_count(self) -> int:
        """Accessor (getter) for number of successfully imported records."""
        return self._valid_count

    def process(self, file_storage, user_id: str) -> dict:
        """Parses, validates, and imports records from an uploaded CSV file stream."""
        self.initialize_session()

        # Handle file stream or bytes
        if hasattr(file_storage, 'stream'):
            stream = io.TextIOWrapper(file_storage.stream, encoding=self._encoding)
        elif isinstance(file_storage, (bytes, bytearray)):
            stream = io.StringIO(file_storage.decode(self._encoding))
        elif hasattr(file_storage, 'read'):
            raw = file_storage.read()
            if isinstance(raw, bytes):
                raw = raw.decode(self._encoding)
            stream = io.StringIO(raw)
        else:
            raise ValueError("Unsupported file format or stream.")

        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("CSV file is empty or missing headers.")

        for row_idx, row in enumerate(reader, start=1):
            try:
                self.validate_and_save_row(row, user_id)
                self._valid_count += 1
            except Exception as e:
                self._error_log.append(f"Row {row_idx}: {str(e)}")

        return {
            "inserted": self._valid_count,
            "errors": self.error_log,
            "total_rows": self._valid_count + len(self._error_log)
        }

    def validate_and_save_row(self, row: dict, user_id: str):
        """Validates and creates an individual activity record from a CSV row."""
        return create_activity_record(row, user_id)
