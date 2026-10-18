import os
import asyncio
from pathlib import Path
from core.ports.agents import IAgentProvider

class AiderCLIAdapter(IAgentProvider):
    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        # Allow injecting the target LLM (can also be a local model via litellm/ollama)
        self.model = model

    async def execute(self, workspace_path: str, context_payload: str) -> bool:
        workspace = Path(workspace_path)
        prompt_file = workspace / ".task_instructions.md"
        
        # 1. Write payload to file to bypass shell string limitations and escaping issues
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(context_payload)

        # 2. Build the headless CLI command
        # --yes: Auto-accept all edits without pausing for human Y/N input
        # --message-file: Read the prompt from disk
        # --no-auto-commits: Rely on our GitWorktreeAdapter's merge_to_main for safe commits
        cmd = (
            f"aider --model {self.model} "
            f"--yes --no-auto-commits "
            f"--message-file {prompt_file.name}"
        )

        try:
            # 3. Execute inside the isolated git worktree
            process = await asyncio.create_subprocess_shell(
                cmd,
                cwd=workspace_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            # 4. Stream logs live so you can watch multiple agents work in parallel
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                # Prefix the log line with the workspace name (e.g., [Agent -> T-01])
                clean_line = line.decode('utf-8', errors='replace').rstrip()
                print(f"[Agent -> {workspace.name}] {clean_line}")

            await process.wait()
            
            # Exit code 0 means Aider finished its edits successfully
            return process.returncode == 0

        except Exception as e:
            print(f"[Agent -> {workspace.name}] Critical Execution Error: {str(e)}")
            return False
            
        finally:
            # 5. Cleanup so the prompt doesn't get merged into your main branch repository
            if prompt_file.exists():
                prompt_file.unlink()