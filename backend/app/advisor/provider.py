"""No network adapter or model credentials. Future providers require separate approval."""

from dataclasses import dataclass
from typing import Protocol

from app.advisor.schemas import Answer


@dataclass(frozen=True)
class ProviderBudget:
    max_context_characters: int = 24000
    timeout_seconds: int = 3
    max_output_tokens: int = 2500
    max_cost_minor_units: int = 0


class Provider(Protocol):
    def explain(self, prepared: Answer, budget: ProviderBudget) -> Answer: ...


class OfflineProvider:
    def explain(self, prepared: Answer, budget: ProviderBudget) -> Answer:
        if len(prepared.model_dump_json()) > budget.max_context_characters:
            raise ValueError("Offline context budget exceeded")
        return prepared.model_copy(deep=True)


def enforce(prepared: Answer, provider: Provider) -> Answer:
    result = Answer.model_validate(
        provider.explain(prepared.model_copy(deep=True), ProviderBudget())
    )
    # No provider-originated text, citation or verification assertion may bypass the composer.
    if result.model_dump() != prepared.model_dump():
        raise ValueError("Provider response differs from the evidence-approved deterministic plan")
    return result
