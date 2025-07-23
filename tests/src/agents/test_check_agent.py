from talk_with_fews.agents import FEWSConfigAgent, FEWSWebserviceAgent


def test_check_config_agent_import():
    """Basic check to see if agents import"""
    agent = FEWSConfigAgent(db_path="")
    # Ignore spelling for "FEWS"
    assert agent is not None, (
        "FEWSConfigAgent should be imported and instantiated successfully."
    )


def test_check_webservice_agent_import():
    """Basic check to see if agents import"""
    agent = FEWSWebserviceAgent(db_path="")
    # Ignore spelling for "FEWS"
    assert agent is not None, (
        "FEWSWebserviceAgent should be imported and instantiated successfully."
    )
