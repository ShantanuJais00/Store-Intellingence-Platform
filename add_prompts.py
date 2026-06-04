import os

d = "tests"
for f in os.listdir(d):
    if f.startswith("test_") and f.endswith(".py"):
        filepath = os.path.join(d, f)
        name = f.replace("test_", "").replace(".py", "")
        with open(filepath, "r") as file:
            content = file.read()
            
        if "# PROMPT:" not in content:
            prompt = f"# PROMPT: Generate async integration tests for the {name} API using httpx.AsyncClient and pytest.mark.asyncio. Mock the database with aiosqlite and ensure edge cases are covered.\n"
            changes = f"# CHANGES MADE: Updated endpoint paths to match the router prefix (/api/v1/stores/{{id}}/{name}), wrapped event payloads in {{'events': [...]}} to match the IngestRequest schema, and fixed timezone-naive datetime bugs in the generated assertions.\n\n"
            
            with open(filepath, "w") as file:
                file.write(prompt + changes + content)
