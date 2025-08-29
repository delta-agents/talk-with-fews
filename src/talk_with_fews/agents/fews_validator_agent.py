"""
FEWS Webservice Agent.

This module defines the agent that can answer questions about FEWS webservice.
"""

import os
from pydantic_ai import Agent, Tool
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.agent import AgentRunResult

from talk_with_fews.models.base import Deps

# Import logging utilities from the dedicated module
from talk_with_fews.utils.logging_utils import logger, setup_logging

from talk_with_fews.tools.validator.validate_xml import validate_xml
from talk_with_fews.tools.validator.generate_xml_template import generate_xml_template

from talk_with_fews.utils.utils import connect_to_database

from talk_with_fews.models.base import AgentResponse


class FEWSValidatorAgent:
    """
    Agent for querying and analyzing FEWS Validator.

    Initialize the FEWS Validator Agent.

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

        logger.info(f"Initialized FEWSValidatorAgent with database: {db_path}")
        logger.info(f"Using model: {self.model_name}")
        if log_dir:
            logger.info(f"Logging to directory: {log_dir}")

    def _create_agent(self):
        """Create the FEWS Validator Agent with tools."""
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

        # Create a simplified system prompt with the schema information
        system_prompt = (
            "You are the FEWS Validator Agent for analyzing Flood Early Warning System Validator. "
            "Your capabilities include validating XML against FEWS schemas. "
            "You can also generate XML templates from XSD schemas. "
            "Response Format:\n"
            "- You response shall be in English\n"
            "- Use available tools to gather accurate information first\n"
            "- Include explanatory text in markdown format\n"
            "- Include mermaid diagrams when visualizing relationships\n\n"
            "Always structure your response with text first, followed by diagrams if needed."
        )

        logger.info("Using comprehensive schema from schema_utils")
        # Set up the tools
        tools = [
            Tool(
                validate_xml,
                takes_ctx=True,
                name="validate_xml",
                description="Validate XML against FEWS schemas. This tool is used to validate XML against FEWS schemas.",
            ),
            Tool(
                generate_xml_template,
                takes_ctx=True,
                name="generate_xml_template",
                description="Generate XML templates from XSD schemas using xmlschema package. This tool creates valid XML templates based on schema definitions.",
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
        Ask the FEWS Validator Agent a question.

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
