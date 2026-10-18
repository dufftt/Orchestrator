from abc import ABC, abstractmethod

class IWorkspaceManager(ABC):
    @abstractmethod
    async def provision_sandbox(self, task_id: str, branch_name: str) -> str:
        """Sets up an isolated environment (e.g., Git worktree) and returns its path."""
        pass

    @abstractmethod
    async def teardown_sandbox(self, task_id: str) -> None:
        """Cleans up the environment on failure."""
        pass

    @abstractmethod
    async def merge_to_main(self, task_id: str, branch_name: str) -> bool:
        """Merges successful work and cleans up the sandbox."""
        pass