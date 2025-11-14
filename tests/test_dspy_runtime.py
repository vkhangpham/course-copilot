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
        self.assertEqual(mock_dspy.OpenAI.call_count, 4)
        mock_dspy.settings.configure.assert_called_once_with(lm=mock_dspy.OpenAI.return_value)

    @mock.patch("ccopilot.core.dspy_runtime.dspy")
    def test_falls_back_to_generic_lm_when_openai_missing(self, mock_dspy) -> None:
        mock_dspy.OpenAI = None
        handles = configure_dspy_models(self.model_cfg, api_key="sk-test")

        self.assertIsInstance(handles, DSPyModelHandles)
        self.assertEqual(mock_dspy.LM.call_count, 4)
        mock_dspy.settings.configure.assert_called_once()

    def test_missing_api_key_raises(self) -> None:
        previous = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with self.assertRaises(DSPyConfigurationError):
                configure_dspy_models(self.model_cfg)
        finally:
            if previous is not None:
                os.environ["OPENAI_API_KEY"] = previous

    @mock.patch("ccopilot.core.dspy_runtime.dspy")
    def test_role_specific_api_key_envs(self, mock_dspy) -> None:
        mock_dspy.OpenAI = mock.Mock()
        cfg = ModelConfig(
            teacher={"provider": "openai", "model": "gpt-4o", "api_key_env": "OPENAI_API_KEY_TEACHER"},
            ta={"provider": "openai", "model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY_TA"},
            student={"provider": "openai", "model": "gpt-4o-mini"},
        )
        with mock.patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY_TEACHER": "sk-teacher",
                "OPENAI_API_KEY_TA": "sk-ta",
                "OPENAI_API_KEY": "sk-student",
            },
            clear=True,
        ):
            configure_dspy_models(cfg)

        teacher_kwargs = mock_dspy.OpenAI.call_args_list[0].kwargs
        ta_kwargs = mock_dspy.OpenAI.call_args_list[1].kwargs
        coder_kwargs = mock_dspy.OpenAI.call_args_list[2].kwargs
        student_kwargs = mock_dspy.OpenAI.call_args_list[3].kwargs
        self.assertEqual(teacher_kwargs["api_key"], "sk-teacher")
        self.assertEqual(ta_kwargs["api_key"], "sk-ta")
        self.assertEqual(coder_kwargs["api_key"], "sk-student")
        self.assertEqual(student_kwargs["api_key"], "sk-student")

    @mock.patch("ccopilot.core.dspy_runtime.dspy")
    def test_openai_api_base_env_applied(self, mock_dspy) -> None:
        mock_dspy.OpenAI = mock.Mock()
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk", "OPENAI_API_BASE": "https://proxy"}, clear=True):
            configure_dspy_models(self.model_cfg)

        self.assertEqual(len(mock_dspy.OpenAI.call_args_list), 4)
        for call in mock_dspy.OpenAI.call_args_list:
            self.assertEqual(call.kwargs.get("api_base"), "https://proxy")


if __name__ == "__main__":
    unittest.main()
