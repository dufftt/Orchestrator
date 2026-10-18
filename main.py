import asyncio
import typer
from pathlib import Path
from core.config import AppConfig
from core.use_cases.scheduler import DAGScheduler
from adapter.workspace.git_worktree import GitWorktreeAdapter
from adapter.repository.json_pipeline import JsonPipelineRepository
from adapter.verification.cli_command import CommandVerificationEngine
from adapter.agents.aider_adapter import AiderCLIAdapter
from adapter.agents.custom_llm_adapter import CustomLlamaCppAdapter
from cli.generator import SpecGenerator

app = typer.Typer(name="orchestrator", add_completion=False)

@app.command()
def run(config_file: str = typer.Option("config.yaml", "--config", "-c")):
    """Executes the pipeline using settings from the config file."""
    # 1. Load and validate configuration
    try:
        config = AppConfig.load(config_file)
    except Exception as e:
        typer.secho(f"Configuration Error: {str(e)}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # 2. Instantiate Adapters based on config
    workspace = GitWorktreeAdapter(
        base_dir=config.workspace.base_dir, 
        base_branch=config.workspace.base_branch
    )
    repository = JsonPipelineRepository(file_path=config.orchestrator.pipeline_file)
    verification = CommandVerificationEngine(timeout_seconds=config.orchestrator.timeout_seconds)
    
    # Dynamic Agent Injection (The Factory Pattern)
    if config.agent.provider == "aider":
        agent = AiderCLIAdapter(model=config.agent.model)
    elif config.agent.provider == "llama_cpp":
        agent = CustomLlamaCppAdapter(
            api_base=config.agent.api_base,
            timeout_seconds=config.orchestrator.timeout_seconds
        )
    else:
        typer.secho(f"Unknown agent provider: {config.agent.provider}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    scheduler = DAGScheduler(agent, workspace, verification, repository)

    typer.secho(f"🚀 Booting Orchestrator (Provider: {config.agent.provider})...", fg=typer.colors.GREEN)
    asyncio.run(scheduler.execute_pipeline())


@app.command()
def generate(
    name: str = typer.Argument(...),
    input_file: Path = typer.Option(None, "--input", "-i"),
    config_file: str = typer.Option("config.yaml", "--config", "-c")
):
    """Generates the DAG pipeline using the configured LLM API."""
    config = AppConfig.load(config_file)
    
    if input_file and input_file.exists():
        initial_idea = input_file.read_text(encoding="utf-8")
    else:
        initial_idea = typer.prompt("Describe your project idea in detail")
    
    generator = SpecGenerator(api_base=config.agent.api_base, model=config.agent.model)
    
    master_spec = asyncio.run(generator.phase_1_architect_loop(initial_idea))
    asyncio.run(generator.phase_2_decompose(master_spec, name))


# Add this at the absolute bottom of your python file
if __name__ == "__main__":
    app()
