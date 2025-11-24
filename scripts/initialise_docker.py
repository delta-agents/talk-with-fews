from talk_with_fews.routers import get_runtime_ctx
from talk_with_fews.routers.setup_connections import setup_env


def initialise_docker():
    environmental_vars = setup_env()
    for user in environmental_vars:
        print(
            f"Setting up environment for user: {environmental_vars[user]['client_id']}"
        )
        get_runtime_ctx(environmental_vars[user])


if __name__ == "__main__":
    initialise_docker()
