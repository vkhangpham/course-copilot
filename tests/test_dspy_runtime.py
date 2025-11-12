import os
import unittest
from unittest import mock

from ccopilot.core.config import ModelConfig
from ccopilot.core.dspy_runtime import (
    DSPyConfigurationError,
    DSPyModelHandles,
    configure_dspy_models,
)


class ConfigureDSPyModelsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model_cfg = ModelConfig()

    @mock.patch("ccopilot.core.dspy_runtime.dspy")
    def test_configures_openai_models(self, mock_dspy) -> None:
        mock_dspy.OpenAI = mock.Mock()
        handles = configure_dspy_models(self.model_cfg, api_key="sk-test")

        self.assertIsInstance(handles, DSPyModelHandles)
        self.assertEqual(mock_dspy.OpenAI.call_count, 3)
        mock_dspy.settings.configure.assert_called_once_with(lm=mock_dspy.OpenAI.return_value)

    @mock.patch("ccopilot.core.dspy_runtime.dspy")
    def test_falls_back_to_generic_lm_when_openai_missing(self, mock_dspy) -> None:
        mock_dspy.OpenAI = None
        handles = configure_dspy_models(self.model_cfg, api_key="sk-test")

        self.assertIsInstance(handles, DSPyModelHandles)
        self.assertEqual(mock_dspy.LM.call_count, 3)
        mock_dspy.settings.configure.assert_called_once()

    def test_missing_api_key_raises(self) -> None:
        previous = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with self.assertRaises(DSPyConfigurationError):
                configure_dspy_models(self.model_cfg)
        finally:
            if previous is not None:
                os.environ["OPENAI_API_KEY"] = previous


if __name__ == "__main__":
    unittest.main()
