"""
FEWS Webservice Agent.

This module defines the agent that can answer questions about FEWS webservice.
"""

import os
from pydantic_ai import Agent, Tool
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.agent import AgentRunResult

from talk_with_fews.agents.fews_config_agent import FEWSConfigAgent
from talk_with_fews.models.base import Deps

# Import logging utilities from the dedicated module
from talk_with_fews.utils.logging_utils import logger, setup_logging

from talk_with_fews.tools import (
    get_parameters,
    get_locations,
    execute_query_webservice,
    get_series_statistics,
)

from talk_with_fews.utils.utils import connect_to_database

from talk_with_fews.utils.schema_utils import (
    extract_db_schema_as_dict,
    generate_llm_context,
)
from talk_with_fews.models.base import AgentResponse


class FEWSWebserviceAgent(FEWSConfigAgent):
    """
    Agent for querying and analyzing FEWS Webservice.

    Initialize the FEWS Webservice Agent.

    Args:
        db_path: Path to the SQLite database containing FEWS webservice data
        model: Optional model to use (defaults to PRIMARY_MODEL env var or gpt-4)
        api_key: Optional API key (will use OPENROUTER_API_KEY env var if not provided)
        base_url: Optional base URL (will use OPENROUTER_BASE_URL env var if not provided)
        log_level: Logging level (default is INFO)
        log_dir: Directory where log files will be stored (default is ~/.fews_agent/logs)
    """

    def __init__(
        self,
        db_path: str,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        log_level: str = "INFO",
        log_dir: str = None,
    ):
        self.db_path = db_path

        # Read model name from PRIMARY_MODEL env var if available
        primary_model = os.environ.get("PRIMARY_MODEL")
        default_model = "gpt-4"

        if primary_model:
            logger.info(f"Using model from PRIMARY_MODEL env: {primary_model}")
            default_model = primary_model

        self.model_name = model or default_model
        self.api_key = api_key
        self.base_url = base_url
        self.agent = None
        self.db_connection = None

        # Set up logging
        setup_logging(log_level=log_level, log_dir=log_dir)

        logger.info(f"Initialized FEWSWebserviceAgent with database: {db_path}")
        logger.info(f"Using model: {self.model_name}")
        if log_dir:
            logger.info(f"Logging to directory: {log_dir}")

    def _create_agent(self):
        """Create the FEWS Webservice Agent with tools."""
        if self.agent is not None:
            return

        db_path = self.db_path
        db_connection = self.db_connection

        if not db_connection:
            logger.warning("Database connection not established. Connecting now.")
            db_connection = connect_to_database(db_path)
            self.db_connection = db_connection

        # Set up dependencies for the agent
        deps = Deps(db_path=db_path, db_connection=db_connection)

        # Extract the database schema for the LLM
        logger.info("Extracting LLM-friendly schema information")
        schema = extract_db_schema_as_dict(db_path)
        llm_context = generate_llm_context(schema)

        # Set schema in deps for tools to access
        deps.schema = schema

        # Create a simplified system prompt with the schema information
        system_prompt = (
            "You are the FEWS Webservice Agent for analyzing Flood Early Warning System Webservices. "
            f"You have access to the database schema:\n{llm_context}\n\n"
            "Your capabilities include analyzing timeseriessets, transformations, workflows, and dependencies in FEWS. "
            "Common questions are about data flows of time series sets (even when mentioned as time series, it is a time series set). "
            "Time series sets shall be formatted using using a standard template, that returns by the description argument of the describe_timeseries tool (model TimeSeriesProperties). "
            "This template is: {modins}•{vtype}•{parid}•{qualifiers (if any)}•{tstype}•{timess}\n\n"
            "Time series sets are the input and output of transformations. "
            "To trace a data flow from an endpoint inspect which transformations has it as an output. "
            "Then check which time series sets are defined as an input for these transformations, "
            "and check which transformations has these time series sets defined as input. "
            "Continue this process until you have traced the data flow to the initial imports, "
            "until the corresponding time series sets are not an output of any transformations. "
            "This way you can trace the data flow of time series sets backwards and forwards."
            "You can visualize data flows only using mermaid diagram syntax.\n\n"
            "Response Format:\n"
            "- You response shall be in Dutch\n"
            "- Use available tools to gather accurate information first\n"
            "- Include explanatory text in markdown format\n"
            "- Add tables when appropriate (markdown format)\n"
            "- Include mermaid diagrams when visualizing relationships\n\n"
            "Always structure your response with text first, followed by tables and diagrams if needed."
        )

        logger.info("Using comprehensive schema from schema_utils")
        # Set up the tools
        tools = [
            Tool(
                get_parameters,
                takes_ctx=True,
                name="get_parameters",
                description="Get all the parameters available in the FEWS Webservice, including their attributes and relationships",
            ),
            Tool(
                get_locations,
                takes_ctx=True,
                name="get_locations",
                description="Get the locations from in the FEWS Webservice, including their attributes and relationships. Can be filtered by parameters and parameter groups obtainable from the tool get_parameters",
            ),
            Tool(
                execute_query_webservice,
                takes_ctx=True,
                name="execute_query_webservice",
                description="Execute a SQL query on the cached FewsWebService database which contains the locations and parameters from the FEWS web service. This is useful for quick access to parameter and location data.",
            ),
            Tool(
                get_series_statistics,
                takes_ctx=True,
                name="get_series_statistics",
                description="Get series statistics from the FEWS webservice with incremental caching. Requires either parameter_id or location_id.",
            ),
        ]

        # Create the model with OpenRouter Webservice
        api_key = self.api_key or os.environ.get("OPENROUTER_API_KEY")
        base_url = self.base_url or os.environ.get("OPENROUTER_BASE_URL")

        if not api_key:
            raise ValueError(
                "API key not provided. Either pass as api_key parameter or set OPENROUTER_API_KEY environment variable."
            )

        if not base_url:
            logger.warning(
                "No base_url provided. Using OpenAI API directly. Set OPENROUTER_BASE_URL for custom API."
            )

        # Update to match the template structure
        model = OpenAIModel(
            model_name=self.model_name,
            provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        )

        # Create the agent
        logger.info(f"Creating FEWS Webservice Agent using {self.model_name}")
        if base_url:
            logger.info(f"Using custom base URL: {base_url}")

        self.agent = Agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            deps_type=Deps,
            output_type=AgentResponse,
        )

        # Store deps for later use when calling the agent
        self.deps = deps

        return self

    async def ask(self, question: str) -> "AgentRunResult":
        """
        Ask the FEWS Webservice Agent a question.

        Args:
            question: The question to ask

        Returns:
            AgentRunResult: The agent's response object containing AgentResponse in its data property
        """
        if self.agent is None:
            self.connect()

        logger.info(f"Asking agent: {question}")

        try:
            # Use basic run method
            response = await self.agent.run(question, deps=self.deps)
            return response

        except Exception as e:
            logger.error(f"Error asking agent: {str(e)}")
            raise
