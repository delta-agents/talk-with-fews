from talk_with_fews.routers import get_runtime_ctx
from talk_with_fews.routers.setup_connections import setup_env
from datetime import datetime


def initialise_docker():
    # TODO: build in a away to stop requests during a rollout
    # make a file: "runnning_initialisation"?
    environmental_vars = setup_env()
    for user in environmental_vars:
        print(
            f"Setting up environment for user: {environmental_vars[user]['client_id']} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        get_runtime_ctx(environmental_vars[user])
    # remove said file


if __name__ == "__main__":
    initialise_docker()
