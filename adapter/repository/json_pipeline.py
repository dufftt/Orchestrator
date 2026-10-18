import os
from pathlib import Path
from core.domain.models import Pipeline
from core.ports.repository import IPipelineRepository

class JsonPipelineRepository(IPipelineRepository):
    def __init__(self, file_path: str = "pipeline.json"):
        self.file_path = Path(file_path).resolve()

    def load(self) -> Pipeline:
        """Reads and validates the pipeline state from JSON."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Pipeline state file not found at {self.file_path}. Please run the Spec Generator first.")
        
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Pydantic v2 validation automatically reconstructs nested Task objects and Enums
        return Pipeline.model_validate_json(content)

    def save(self, pipeline: Pipeline) -> None:
        """Serializes and atomically writes the pipeline state."""
        # Pydantic v2 serialization with indentation for human readability and easy git tracking
        json_data = pipeline.model_dump_json(indent=2)
        
        # Atomic write pattern: Write to a temporary file first, then swap.
        # This prevents generating an empty or half-written pipeline.json if the process
        # is killed (e.g., Ctrl+C) at the exact millisecond of file IO.
        temp_file = self.file_path.with_suffix('.tmp')
        
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(json_data)
            
            # replace() is atomic on POSIX systems and modern Windows
            temp_file.replace(self.file_path)
            
        except Exception as e:
            # Cleanup the temp file if something goes wrong to avoid clutter
            if temp_file.exists():
                temp_file.unlink()
            raise IOError(f"Failed to safely save pipeline state: {str(e)}")