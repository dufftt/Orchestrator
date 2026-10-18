from abc import ABC, abstractmethod
from typing import Tuple

class IVerificationEngine(ABC):
    @abstractmethod
    async def run_check(self, workspace_path: str, command: str) -> Tuple[bool, str]:
        """Executes verification and returns (Passed, Output/Logs)."""
        pass