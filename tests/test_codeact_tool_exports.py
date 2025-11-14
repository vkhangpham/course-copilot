import inspect

from apps.codeact import tools as exports
from apps.codeact.tools import data as data_module
from apps.codeact.tools import world_model as world_module


def _shape(signature: inspect.Signature) -> list[tuple[str, object, object]]:
    return [(param.name, param.kind, param.default) for param in signature.parameters.values()]


def test_wrappers_preserve_signatures_without_annotations() -> None:
    wrapped = exports.load_dataset_asset
    impl = data_module.load_dataset_asset

    wrapped_sig = inspect.signature(wrapped)
    impl_sig = inspect.signature(impl)

    assert _shape(wrapped_sig) == _shape(impl_sig)
    assert all(param.annotation is inspect._empty for param in wrapped_sig.parameters.values())
    assert wrapped_sig.return_annotation is inspect._empty
    assert wrapped.__annotations__ == {}


def test_world_model_wrapper_keeps_parameter_names_and_defaults() -> None:
    wrapped = exports.fetch_concepts
    impl = world_module.fetch_concepts

    wrapped_sig = inspect.signature(wrapped)
    impl_sig = inspect.signature(impl)

    assert _shape(wrapped_sig) == _shape(impl_sig)
    assert all(param.annotation is inspect._empty for param in wrapped_sig.parameters.values())
