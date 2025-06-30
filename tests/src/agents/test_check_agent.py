
from talk_with_fews.agents import FEWSConfigAgent

def test_check_agent_import():
    """Basic check to see if agents import"""
    agent = FEWSConfigAgent(db_path="")
    # Ignore spelling for "FEWS"
    assert agent is not None, "FEWSConfigAgent should be imported and instantiated successfully."
