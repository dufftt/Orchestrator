import json
import os
import re
import aiohttp
import asyncio
import typer
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from core.domain.models import Pipeline, Task, TaskStatus

console = Console()

class SpecGenerator:
    def __init__(self, api_base: str = "http://127.0.0.1:8080/v1", model: str = "llama-3"):
        self.api_base = api_base
        self.model = model
        self.tasks_dir = Path("tasks")
        self.tasks_dir.mkdir(exist_ok=True)



    async def _call_llm(self, messages: list, expect_json: bool = True, max_retries: int = 3) -> dict:
        """Helper to call the local LLM and parse JSON output safely."""
        payload = {
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"} if expect_json else None
        }
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                async with session.post(f"{self.api_base}/chat/completions", json=payload) as response:
                    if response.status != 200:
                        raise RuntimeError(f"LLM API Error: {await response.text()}")
                    
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    
                    if not expect_json:
                        return content
                        
                    # Attempt 1: Direct JSON parse
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        pass
                        
                    # Attempt 2: Extract JSON using regex (strips out markdown and conversational fluff)
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        try:
                            return json.loads(match.group(0))
                        except json.JSONDecodeError:
                            pass
                            
                    # Attempt 3: If we reach here, the LLM completely failed to output JSON
                    if attempt < max_retries - 1:
                        console.print(f"[yellow]⚠️ LLM returned invalid JSON, forcing retry (Attempt {attempt + 1}/{max_retries})...[/yellow]")
                        # Feed the bad output back to the LLM and scold it
                        payload["messages"].append({"role": "assistant", "content": content})
                        payload["messages"].append({
                            "role": "user", 
                            "content": "ERROR: You did not return valid JSON. You MUST output strictly a JSON object matching the schema without any conversational text."
                        })
                    else:
                        console.print(f"[red]🚨 Fatal JSON Decode Error. Raw LLM Output:[/red]\n{content}")
                        raise ValueError("LLM failed to return valid JSON after multiple attempts.")

    async def phase_1_architect_loop(self, initial_idea: str) -> str:
        """Phase 1: Interrogate user until spec is unambiguous (Text-based for local LLM stability)."""
        
        system_prompt = """You are a Principal Software Architect. Your job is to analyze a project idea.
If there is ANY ambiguity regarding tech stack, database schema, authentication, or architecture, you MUST ask questions.

DO NOT OUTPUT JSON. You must use this exact text format:

[STATUS]
NEEDS_INFO (or APPROVED if everything is clear)

[QUESTIONS]
- Question 1 (if any)
- Question 2 (if any)

[SPECIFICATION]
Your complete markdown specification goes here (leave empty if NEEDS_INFO).
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Project Idea: {initial_idea}"}
        ]

        console.print("[bold cyan]🤖 Architect Analysis Started...[/bold cyan]")
        
        while True:
            # We pass expect_json=False so the LLM adapter just returns the raw string
            content = await self._call_llm(messages, expect_json=False)
            
            # 1. Parse Status
            status = "NEEDS_INFO"
            if "[STATUS]" in content:
                status_block = content.split("[STATUS]")[1].split("[QUESTIONS]")[0]
                if "APPROVED" in status_block.upper():
                    status = "APPROVED"
            
            # 2. Handle Approved State
            if status == "APPROVED":
                if "[SPECIFICATION]" in content:
                    master_spec = content.split("[SPECIFICATION]")[1].strip()
                    
                    if len(master_spec) > 20: # Sanity check that it actually wrote something
                        console.print("[bold green]✅ Specification Approved![/bold green]")
                        return master_spec
                
                console.print("[yellow]⚠️ Agent approved but forgot to write the specification. Retrying...[/yellow]")
                messages.append({"role": "assistant", "content": "I set status to APPROVED but forgot to output the [SPECIFICATION] block."})
                messages.append({"role": "user", "content": "Please provide the complete markdown specification under the [SPECIFICATION] tag."})
                continue
            
            # 3. Handle Needs Info State
            console.print("\n[bold yellow]⚠️  The Architect needs clarification:[/bold yellow]")
            
            questions = []
            if "[QUESTIONS]" in content:
                q_block = content.split("[QUESTIONS]")[1]
                if "[SPECIFICATION]" in q_block:
                    q_block = q_block.split("[SPECIFICATION]")[0]
                
                # Extract bullet points safely
                questions = [
                    line.strip("- *").strip() 
                    for line in q_block.split("\n") 
                    if line.strip().startswith(("-", "*", "1.", "2.", "3."))
                ]
                
            if not questions:
                console.print("[red]The LLM requested more info but provided no questions. Retrying...[/red]")
                messages.append({"role": "assistant", "content": "I need more info but forgot to list the questions."})
                messages.append({"role": "user", "content": "List your questions as bullet points under the [QUESTIONS] tag."})
                continue
                
            for i, q in enumerate(questions):
                console.print(f"{i+1}. {q}")
                
            user_reply = typer.prompt("\nYour Answers (or type 'abort' to cancel)")
            if user_reply.lower() == 'abort':
                raise typer.Exit()
                
            # Token Compression: Only remember the questions asked, not the whole verbose prompt
            assistant_memory = "I asked:\n" + "\n".join(questions)
            messages.append({"role": "assistant", "content": assistant_memory})
            messages.append({"role": "user", "content": f"User Answers: {user_reply}"})

            # Token Sliding Window: Keep system prompt & initial idea, drop old Q&As
            if len(messages) > 8:
                messages.pop(2)
                messages.pop(2)
                
            console.print("\n[bold cyan]🔄 Re-evaluating Architecture...[/bold cyan]")

    async def phase_2_decompose(self, master_spec: str, project_name: str):
        """Phase 2: Break spec into the Pipeline DAG and generate task markdown files."""
        
        system_prompt = """You are a Technical Project Manager. 
Break the provided Master Specification into a Directed Acyclic Graph (DAG) of technical tasks.
Rules:
1. Tasks must be small enough to complete in a single Git commit.
2. Dependencies must be explicit (e.g., Database task must happen before API task).
3. Output strictly in JSON format matching this schema:
{
  "tasks": [
    {
      "id": "T-01",
      "name": "Init Database",
      "dependencies": [],
      "task_doc_content": "# Objective\\nComplete setup details..."
    },
    {
      "id": "T-02",
      "name": "User Models",
      "dependencies": ["T-01"],
      "task_doc_content": "# Objective\\nCreate User models based on spec..."
    }
  ]
}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"SPECIFICATION:\n{master_spec}"}
        ]

        console.print("[bold cyan]🧩 Decomposing spec into Task DAG...[/bold cyan]")
        dag_response = await self._call_llm(messages)
        
        # 1. Write the MASTER_SPEC.md to root
        with open("MASTER_SPEC.md", "w", encoding="utf-8") as f:
            f.write(master_spec)
        console.print("[green]📝 Wrote MASTER_SPEC.md[/green]")

        # 2. Build the domain Pipeline object and write the isolated task files
        tasks = []
        for t_data in dag_response.get("tasks", []):
            task_id = t_data["id"]
            doc_path = f"tasks/{task_id}.md"
            
            # Write the self-contained task document to the filesystem
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(t_data["task_doc_content"])
                
            # Create domain Task object
            task = Task(
                id=task_id,
                name=t_data["name"],
                doc_path=doc_path,
                dependencies=t_data["dependencies"],
                status=TaskStatus.PENDING
            )
            tasks.append(task)
            
        pipeline = Pipeline(
            project_name=project_name,
            concurrency_limit=3,
            tasks=tasks
        )
        
        # 3. Save the pipeline JSON using our adapter interface
        from adapter.repository.json_pipeline import JsonPipelineRepository
        repo = JsonPipelineRepository("pipeline.json")
        repo.save(pipeline)
        
        console.print(f"[bold green]🎯 Successfully generated DAG with {len(tasks)} tasks in pipeline.json![/bold green]")