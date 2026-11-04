"""The one place that knows how to call the agent.

Both the CLI runner and the eval suite go through here, so there is a single
definition of what talking to the agent means. The call shape has already
changed once; when it changes again, exactly one function needs editing.
"""

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from agents.store_manager import AGENT_NAME
from config import settings


def ask(prompt: str) -> str:
    """Send one prompt to the deployed agent and return the raw reply text.

    Notes on the call shape, learned the hard way:
      * AIProjectClient needs allow_preview=True before get_openai_client will
        accept an agent_name.
      * What comes back is a plain openai.OpenAI client pointed at the agent
        endpoint, so instructions, reasoning effort, structured inputs and the
        output schema are all applied server-side.
      * model must equal the agent own model or the service rejects the call.
    """
    cfg = settings()
    project = AIProjectClient(
        endpoint=cfg.project_endpoint,
        credential=DefaultAzureCredential(),
        allow_preview=True,
    )
    agent = project.get_openai_client(agent_name=AGENT_NAME)
    response = agent.responses.create(model=cfg.model_deployment, input=prompt)
    return response.output_text
