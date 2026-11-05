"""The one place that knows how to call the agent.

Both the CLI runner and the eval suite go through here, so there is a single
definition of what talking to the agent means. The call shape has already
changed twice; when it changes again, exactly one function needs editing.
"""

import sys
from functools import lru_cache

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from agents.store_manager import AGENT_NAME
from config import settings


@lru_cache(maxsize=1)
def _clients(endpoint: str, agent_name: str):
    """Create and retain the Azure clients for this process.

    Evaluations call ``ask`` once per case. Reusing the credential and clients
    avoids repeating authentication setup and connection-pool creation on each
    call. Configuration is read before this function is called, so a changed
    endpoint naturally gets a new cached client pair.
    """
    credential = DefaultAzureCredential()
    project = AIProjectClient(
        endpoint=endpoint,
        credential=credential,
        allow_preview=True,
    )
    return project, project.get_openai_client(agent_name=agent_name)


def _reply_text(response) -> str:
    """Return the text of the final message item in the response.

    Deliberately not response.output_text. That property concatenates every
    text item in the response, and the service sometimes emits more than one
    complete answer. Under a strict JSON schema, two valid JSON objects glued
    together is invalid JSON - an intermittent corruption found by the
    never_claims_untaken_action eval case rather than by a human.

    More than one message is worth knowing about, so it warns rather than
    quietly discarding the extras.
    """
    messages = [item for item in response.output
                if getattr(item, "type", None) == "message"]
    if not messages:
        raise RuntimeError("response contained no message item")
    if len(messages) > 1:
        print("warning: " + str(len(messages))
              + " message items in one response, using the last", file=sys.stderr)
    final = messages[-1]
    return "".join(part.text for part in final.content
                   if getattr(part, "type", None) == "output_text")


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
    _, agent = _clients(cfg.project_endpoint, AGENT_NAME)
    response = agent.responses.create(model=cfg.model_deployment, input=prompt)
    return _reply_text(response)
