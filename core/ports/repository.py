from abc import ABC, abstractmethod
from core.domain.models import Pipeline

class IPipelineRepository(ABC):
    @abstractmethod
    def load(self) -> Pipeline:
        """Loads state from pipeline.json or a DB."""
        pass
        
    @abstractmethod
    def save(self, pipeline: Pipeline) -> None:
        """Persists state updates."""
        pass