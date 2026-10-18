import asyncio
from typing import Set
from core.domain.models import Pipeline, Task, TaskStatus
from core.ports.agents import IAgentProvider
from core.ports.workspace import IWorkspaceManager
from core.ports.verification import IVerificationEngine
from core.ports.repository import IPipelineRepository

class DAGScheduler:
    def __init__(
        self,
        agent: IAgentProvider,
        workspace: IWorkspaceManager,
        verification: IVerificationEngine,
        repository: IPipelineRepository
    ):
        # Dependency Injection of our Hexagonal Ports
        self.agent = agent
        self.workspace = workspace
        self.verification = verification
        self.repository = repository

    async def execute_pipeline(self):
        """Main event loop traversing the DAG."""
        pipeline = self.repository.load()
        semaphore = asyncio.Semaphore(pipeline.concurrency_limit)
        active_tasks: Set[asyncio.Task] = set()

        print(f"🚀 Starting Pipeline: {pipeline.project_name} (Concurrency: {pipeline.concurrency_limit})")

        while True:
            # 1. Identify unblocked tasks
            ready_tasks = pipeline.get_ready_tasks()

            for task in ready_tasks:
                task.status = TaskStatus.IN_PROGRESS
                self.repository.save(pipeline)
                
                # 2. Dispatch worker as an async background task
                worker = asyncio.create_task(self._process_task(task, pipeline, semaphore))
                active_tasks.add(worker)

            # 3. Exit condition: No active tasks and no ready tasks
            if not active_tasks:
                print("🏁 Pipeline execution finished or deadlocked.")
                break

            # 4. Wait for at least one worker to finish before re-evaluating the DAG
            done, active_tasks = await asyncio.wait(
                active_tasks, 
                return_when=asyncio.FIRST_COMPLETED
            )

    async def _process_task(self, task: Task, pipeline: Pipeline, semaphore: asyncio.Semaphore):
        """The isolated task runner bound by the concurrency limit."""
        async with semaphore:  # Enforces max N parallel agents
            branch_name = task.branch_name or f"task/{task.id}"
            task.branch_name = branch_name
            self.repository.save(pipeline)
            
            print(f"[{task.id}] 🛠 Provisioning workspace...")
            workspace_path = ""
            
            try:
                # Phase 1: Isolation
                workspace_path = await self.workspace.provision_sandbox(task.id, branch_name)

                # Phase 2: Agent Execution
                print(f"[{task.id}] 🤖 Executing agent...")
                with open(task.doc_path, 'r') as f:
                    task_payload = f.read()
                
                agent_success = await self.agent.execute(workspace_path, task_payload)
                if not agent_success:
                    raise Exception("Agent returned a failure exit code.")

                # Phase 3: Verification Gate
                print(f"[{task.id}] 🧪 Running verification tests...")
                task.status = TaskStatus.VERIFYING
                self.repository.save(pipeline)

                # In a real scenario, this command is parsed from the task_payload frontmatter
                verify_cmd = "make verify" 
                passed, logs = await self.verification.run_check(workspace_path, verify_cmd)

                if passed:
                    # Phase 4a: Handover (Merge & Unblock)
                    print(f"[{task.id}] ✅ Passed! Merging to main.")
                    await self.workspace.merge_to_main(task.id, branch_name)
                    task.status = TaskStatus.COMPLETED
                else:
                    # Phase 4b: Failure Handling (Retries can be injected here)
                    print(f"[{task.id}] ❌ Failed verification.\n{logs}")
                    await self.workspace.teardown_sandbox(task.id)
                    task.status = TaskStatus.FAILED

            except Exception as e:
                print(f"[{task.id}] 🚨 System error: {str(e)}")
                if workspace_path:
                    await self.workspace.teardown_sandbox(task.id)
                task.status = TaskStatus.FAILED

            finally:
                # Always persist the state so the main loop can evaluate unblocked downstream tasks
                self.repository.save(pipeline)