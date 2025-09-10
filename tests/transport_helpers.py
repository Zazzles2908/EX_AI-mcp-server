from src.providers.registry import ModelProviderRegistry
from src.providers.kimi import KimiModelProvider
from src.providers.glm import GLMModelProvider


def inject_transport():
    """Register Kimi and GLM providers for tests that expect a working registry.

    Tests that depend on specific providers (e.g., OpenAI o3-pro replay) don't need real
    network. We register the core providers so ChatTool and others can resolve a default.
    """
    ModelProviderRegistry.reset_for_testing()
    ModelProviderRegistry.register_provider("kimi", KimiModelProvider("test"))
    ModelProviderRegistry.register_provider("glm", GLMModelProvider("test"))

