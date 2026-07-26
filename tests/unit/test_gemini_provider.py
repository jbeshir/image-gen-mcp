from unittest.mock import AsyncMock, MagicMock

import pytest

from image_gen_mcp.providers.base import LLMProvider, ProviderConfig
from image_gen_mcp.providers.gemini import GeminiProvider


@pytest.fixture
def provider():
    instance = GeminiProvider.__new__(GeminiProvider)
    LLMProvider.__init__(
        instance,
        ProviderConfig(api_key="/unused/service-account.json"),
    )
    instance.client = MagicMock()
    instance.client.aio.models.generate_content = AsyncMock()
    return instance


def test_supported_models_are_current_native_gemini_models(provider):
    assert provider.get_supported_models() == {
        "gemini-3.1-flash-image",
        "gemini-3.1-flash-lite-image",
        "gemini-3-pro-image",
        "gemini-2.5-flash-image",
    }


@pytest.mark.asyncio
async def test_generate_image_uses_generate_content(provider):
    part = MagicMock()
    part.inline_data.data = b"generated-png"
    response = MagicMock(parts=[part])
    provider.client.aio.models.generate_content.return_value = response

    result = await provider.generate_image(
        model="gemini-3.1-flash-image",
        prompt="A tiny banana spaceship",
        size="1536x1024",
    )

    assert result.image_data == b"generated-png"
    call = provider.client.aio.models.generate_content.await_args
    assert call.kwargs["model"] == "gemini-3.1-flash-image"
    assert call.kwargs["contents"] == "A tiny banana spaceship"
    assert call.kwargs["config"].response_modalities == ["IMAGE"]
    assert call.kwargs["config"].image_config.aspect_ratio == "4:3"


@pytest.mark.parametrize(
    ("model", "cost"),
    [
        ("gemini-3.1-flash-image", 0.067),
        ("gemini-3.1-flash-lite-image", 0.0336),
        ("gemini-3-pro-image", 0.134),
        ("gemini-2.5-flash-image", 0.039),
    ],
)
def test_current_model_pricing(provider, model, cost):
    estimate = provider.estimate_cost(model, "prompt")
    assert estimate["breakdown"]["per_image"] == cost
