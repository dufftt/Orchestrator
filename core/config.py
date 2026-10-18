import yaml
from pathlib import Path
from pydantic import BaseModel

class OrchestratorConfig(BaseModel):
    pipeline_file: str = "pipeline.json"
    concurrency_limit: int = 3
    timeout_seconds: int = 300

class WorkspaceConfig(BaseModel):
    base_dir: str = "."
    base_branch: str = "main"

class AgentConfig(BaseModel):
    provider: str  # e.g., 'aider', 'llama_cpp'
    model: str
    api_base: str

class AppConfig(BaseModel):
    orchestrator: OrchestratorConfig
    workspace: WorkspaceConfig
    agent: AgentConfig

    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "AppConfig":
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        return cls(**data)