from pathlib import Path
from dotenv import load_dotenv
# from talk_with_fews.routers.setup_connections import get_runtime_ctx
# import asyncio

def setup_dot_env():
    env_template = Path(__file__).parent.parent / "env" / ".env.example"
    env_copy = Path(__file__).parent.parent / "env" / ".env"
    if not env_copy.exists():
        env_copy.write_text(env_template.read_text())
    load_dotenv(dotenv_path="env/.env")


# Call the function in an async context to ensure thread safety
# async def run_test_async(func, input_data):
#     ctx = get_runtime_ctx()
#     return await func(ctx, input_data)

# async def run_test_async(func, input_data):
#     """Run the test function in an async context."""
#     ctx = get_runtime_ctx()
#     return await func(ctx, input_data)