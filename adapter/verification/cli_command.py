import asyncio
from typing import Tuple
from core.ports.verification import IVerificationEngine

class CommandVerificationEngine(IVerificationEngine):
    def __init__(self, timeout_seconds: int = 300):
        # Default to a 5-minute timeout to prevent AI-generated infinite loops 
        # from permanently hanging the orchestration DAG.
        self.timeout_seconds = timeout_seconds

    async def run_check(self, workspace_path: str, command: str) -> Tuple[bool, str]:
        """Executes verification and returns (Passed, Output/Logs)."""
        process = None
        try:
            # Execute in the isolated Git worktree directory
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=workspace_path,
                stdout=asyncio.subprocess.PIPE,
                # Merge stderr into stdout so the LLM gets a unified log to read on failure
                stderr=asyncio.subprocess.STDOUT 
            )

            # Wait for the command to complete, bounded by the timeout
            stdout, _ = await asyncio.wait_for(
                process.communicate(), 
                timeout=self.timeout_seconds
            )
            
            # Use 'replace' to prevent crashing if the test framework outputs weird binary characters
            logs = stdout.decode('utf-8', errors='replace').strip()
            passed = (process.returncode == 0)
            
            return passed, logs

        except asyncio.TimeoutError:
            # If the process hangs, we must kill it and report failure to the agent
            if process:
                try:
                    process.kill()
                    await process.wait() # Ensure process is fully reaped
                except ProcessLookupError:
                    pass
            
            error_msg = (
                f"Timeout Error: Command '{command}' exceeded {self.timeout_seconds} seconds "
                "and was killed. You may have written an infinite loop or a hanging process."
            )
            return False, error_msg
            
        except Exception as e:
            # Catch OS-level configuration errors (e.g., missing binaries like 'npm' or 'go')
            return False, f"Execution Error: Failed to run command '{command}'. Details: {str(e)}"