from abc import ABC, abstractmethod

class IAgentProvider(ABC):
    @abstractmethod
    async def execute(self, workspace_path: str, context_payload: str) -> bool:
        """Hands the task document to the agent inside the designated workspace."""
        pass