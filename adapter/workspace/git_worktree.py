import os
import asyncio
from pathlib import Path
from typing import Tuple
from core.ports.workspace import IWorkspaceManager

class GitWorktreeAdapter(IWorkspaceManager):
    def __init__(self, base_dir: str = ".", base_branch: str = "main"):
        self.base_dir = Path(base_dir).resolve()
        self.base_branch = base_branch
        self.worktrees_dir = self.base_dir / ".worktrees"
        
        # Ensure the .worktrees directory exists
        self.worktrees_dir.mkdir(exist_ok=True)

    async def _run_cmd(self, cmd: str, cwd: Path = None, check: bool = True) -> Tuple[int, str, str]:
        """Helper to run async shell commands and capture output."""
        working_directory = cwd or self.base_dir
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            cwd=working_directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        out_str = stdout.decode().strip()
        err_str = stderr.decode().strip()
        
        if check and process.returncode != 0:
            raise RuntimeError(f"Git command failed: '{cmd}'\nError: {err_str}")
            
        return process.returncode, out_str, err_str

    async def provision_sandbox(self, task_id: str, branch_name: str) -> str:
        """Creates a new branch and links it to a dedicated worktree folder."""
        target_dir = self.worktrees_dir / task_id
        
        # If worktree already exists (e.g., from a previous failed run), clean it up first
        if target_dir.exists():
            await self.teardown_sandbox(task_id)

        # Create the worktree linked to a new branch branching off base_branch
        cmd = f"git worktree add -b {branch_name} {target_dir} {self.base_branch}"
        await self._run_cmd(cmd)
        
        return str(target_dir)

    async def teardown_sandbox(self, task_id: str) -> None:
        """Removes the worktree folder and prunes Git's internal tracking."""
        target_dir = self.worktrees_dir / task_id
        
        if not target_dir.exists():
            return
            
        # Force remove the worktree 
        await self._run_cmd(f"git worktree remove -f {target_dir}", check=False)
        # Ensure git cleans up its internal references
        await self._run_cmd("git worktree prune", check=False)

    async def merge_to_main(self, task_id: str, branch_name: str) -> bool:
        """Commits agent changes in the sandbox, merges to main, and cleans up."""
        target_dir = self.worktrees_dir / task_id
        
        if not target_dir.exists():
            raise FileNotFoundError(f"Worktree for {task_id} not found at {target_dir}")

        # 1. Auto-commit any raw file changes the agent left behind in its sandbox
        code, out, err = await self._run_cmd("git status --porcelain", cwd=target_dir)
        if out:  # If there are uncommitted changes
            await self._run_cmd("git add .", cwd=target_dir)
            await self._run_cmd(f'git commit -m "Auto-commit: resolve {task_id}"', cwd=target_dir)

        # 2. Merge the task branch into the base branch from the root repository
        # First ensure root is on base_branch
        await self._run_cmd(f"git checkout {self.base_branch}")
        
        try:
            await self._run_cmd(f"git merge {branch_name} --no-edit")
        except RuntimeError as e:
            # If a merge conflict occurs, abort the merge so the main branch stays clean
            await self._run_cmd("git merge --abort", check=False)
            raise RuntimeError(f"Merge conflict for {task_id}. Aborted merge. Details: {str(e)}")

        # 3. Cleanup sandbox and branch post-merge
        await self.teardown_sandbox(task_id)
        await self._run_cmd(f"git branch -d {branch_name}", check=False)
        
        return True