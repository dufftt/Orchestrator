import aiohttp
import re
from pathlib import Path
from core.ports.agents import IAgentProvider

class CustomLlamaCppAdapter(IAgentProvider):
    def __init__(self, api_base: str = "http://127.0.0.1:8080/v1", timeout_seconds: int = 600):
        # Assumes llama-server is running locally on default port 8080
        self.api_base = api_base
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def execute(self, workspace_path: str, context_payload: str) -> bool:
        workspace = Path(workspace_path)
        
        # 1. The Strict System Prompt
        # Local LLMs need rigid, explicit formatting instructions to avoid outputting garbage.
        # We force it to use XML tags because regex parsing XML is much more reliable 
        # than trying to parse markdown code blocks where the file path is often omitted.
        system_prompt = """You are an autonomous AI software engineer. 
Your job is to read the task and generate the required code.
CRITICAL RULES:
1. You must output the COMPLETE, fully written code for any file you create or modify.
2. Never output partial diffs or placeholders like "// rest of code here".
3. You MUST wrap every generated file in strict XML tags exactly like this:

<file path="relative/path/from/root.py">
import os
print("Complete code goes here")
</file>

If the task asks for multiple files, output multiple <file> blocks."""

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_payload}
            ],
            "temperature": 0.1, # Keep creativity low for deterministic coding
            "stream": False
        }

        print(f"[Llama.cpp -> {workspace.name}] Prompting local model...")
        
        try:
            # 2. Communicate with the local llama-server
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    json=payload
                ) as response:
                    
                    if response.status != 200:
                        err = await response.text()
                        print(f"[Llama.cpp -> {workspace.name}] API Error: {err}")
                        return False
                        
                    data = await response.json()
                    llm_output = data["choices"][0]["message"]["content"]
                    
            # 3. Parse the XML and write files to the workspace
            return await self._apply_file_changes(workspace, llm_output)

        except asyncio.TimeoutError:
            print(f"[Llama.cpp -> {workspace.name}] Local LLM timed out after {self.timeout.total}s.")
            return False
        except Exception as e:
            print(f"[Llama.cpp -> {workspace.name}] Execution failed: {str(e)}")
            return False

    async def _apply_file_changes(self, workspace: Path, text: str) -> bool:
        """Extracts <file path="...">...</file> blocks and writes them to disk."""
        
        # Regex to capture the file path and the content inside the tags
        pattern = re.compile(r'<file path=["\'](.*?)["\']>(.*?)</file>', re.DOTALL)
        matches = pattern.findall(text)
        
        if not matches:
            print(f"[Llama.cpp -> {workspace.name}] Failed to parse LLM output. No <file> tags found.")
            # Print a snippet of what it actually returned for debugging
            snippet = text[:200].replace('\n', ' ')
            print(f"[Llama.cpp -> {workspace.name}] Raw output snippet: {snippet}...")
            return False
            
        for file_path, content in matches:
            # Ensure the path is strictly within the workspace to prevent directory traversal attacks
            safe_path = (workspace / file_path.strip()).resolve()
            if not str(safe_path).startswith(str(workspace.resolve())):
                print(f"[Llama.cpp -> {workspace.name}] Security warning: Attempted to write outside workspace: {file_path}")
                continue
                
            # Create subdirectories if they don't exist
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the file
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content.strip() + "\n")
                
            print(f"[Llama.cpp -> {workspace.name}] Wrote: {file_path}")
            
        return True