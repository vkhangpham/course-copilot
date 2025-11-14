"""Validation framework to prevent silent failures in the orchestration system."""

from __future__ import annotations

import functools
import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

# Type variables for generic validation
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class ValidationResult:
    """Result of a validation check."""

    valid: bool
    errors: List[str]
    warnings: List[str]
    data: Any = None

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def raise_if_invalid(self) -> None:
        """Raise ValidationError if validation failed."""
        if not self.valid:
            raise ValidationError(f"Validation failed: {'; '.join(self.errors)}")


class ValidationFramework:
    """Central validation framework for the CourseGen system."""

    def __init__(self, *, strict: bool = True, log_level: str = "INFO"):
        """Initialize validation framework.

        Args:
            strict: If True, raise exceptions on validation failure
            log_level: Logging level for validation messages
        """
        self.strict = strict
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))

    # ============== File Operations ==============

    def validate_file_exists(self, path: Path | str) -> ValidationResult:
        """Validate that a file exists and is readable."""
        errors = []
        warnings = []
        path_obj = Path(path)

        if not path_obj.exists():
            errors.append(f"File does not exist: {path}")
        elif not path_obj.is_file():
            errors.append(f"Path is not a file: {path}")
        elif not path_obj.stat().st_size:
            warnings.append(f"File is empty: {path}")

        try:
            # Test readability
            with path_obj.open("r", encoding="utf-8"):
                pass
        except PermissionError:
            errors.append(f"No read permission for file: {path}")
        except Exception as e:
            errors.append(f"Cannot read file {path}: {e}")

        result = ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            data=path_obj if not errors else None,
        )

        if not result.valid:
            self.logger.error(f"File validation failed: {result.errors}")
        elif result.has_warnings:
            self.logger.warning(f"File validation warnings: {result.warnings}")

        if self.strict and not result.valid:
            result.raise_if_invalid()

        return result

    def validate_json_file(self, path: Path | str) -> ValidationResult:
        """Validate and load a JSON file."""
        errors = []
        warnings = []
        data = None

        # First check file exists
        file_result = self.validate_file_exists(path)
        if not file_result.valid:
            return file_result

        path_obj = Path(path)
        try:
            content = path_obj.read_text(encoding="utf-8")
            if not content.strip():
                errors.append(f"JSON file is empty: {path}")
            else:
                data = json.loads(content)
                self.logger.info(f"Successfully loaded JSON from {path}")
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in {path}: {e}")
        except Exception as e:
            errors.append(f"Error reading JSON file {path}: {e}")

        result = ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, data=data)

        if not result.valid:
            self.logger.error(f"JSON validation failed: {result.errors}")

        if self.strict and not result.valid:
            result.raise_if_invalid()

        return result

    def validate_yaml_file(self, path: Path | str) -> ValidationResult:
        """Validate and load a YAML file."""
        errors = []
        warnings = []
        data = None

        # First check file exists
        file_result = self.validate_file_exists(path)
        if not file_result.valid:
            return file_result

        path_obj = Path(path)
        try:
            content = path_obj.read_text(encoding="utf-8")
            if not content.strip():
                errors.append(f"YAML file is empty: {path}")
            else:
                data = yaml.safe_load(content)
                if data is None:
                    warnings.append(f"YAML file contains only null/empty data: {path}")
                    data = {}
                self.logger.info(f"Successfully loaded YAML from {path}")
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML in {path}: {e}")
        except Exception as e:
            errors.append(f"Error reading YAML file {path}: {e}")

        result = ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, data=data)

        if not result.valid:
            self.logger.error(f"YAML validation failed: {result.errors}")
        elif result.has_warnings:
            self.logger.warning(f"YAML validation warnings: {result.warnings}")

        if self.strict and not result.valid:
            result.raise_if_invalid()

        return result

    # ============== Data Validation ==============

    def validate_dict_structure(self, data: Any, required_keys: List[str], optional_keys: Optional[List[str]] = None) -> ValidationResult:
        """Validate dictionary structure and keys."""
        errors = []
        warnings = []

        if not isinstance(data, dict):
            errors.append(f"Expected dict, got {type(data).__name__}")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # Check required keys
        missing = [key for key in required_keys if key not in data]
        if missing:
            errors.append(f"Missing required keys: {missing}")

        # Check for unknown keys
        if optional_keys is not None:
            allowed = set(required_keys) | set(optional_keys)
            unknown = [key for key in data if key not in allowed]
            if unknown:
                warnings.append(f"Unknown keys (will be ignored): {unknown}")

        # Check for None values in required keys
        null_required = [key for key in required_keys if key in data and data[key] is None]
        if null_required:
            errors.append(f"Required keys with null values: {null_required}")

        result = ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, data=data)

        if not result.valid:
            self.logger.error(f"Dict structure validation failed: {result.errors}")
        elif result.has_warnings:
            self.logger.warning(f"Dict structure warnings: {result.warnings}")

        if self.strict and not result.valid:
            result.raise_if_invalid()

        return result

    def validate_pydantic_model(self, data: Dict[str, Any], model_class: Type[BaseModel]) -> ValidationResult:
        """Validate data against a Pydantic model."""
        errors = []
        warnings = []
        validated_data = None

        try:
            validated_data = model_class(**data)
            self.logger.info(f"Successfully validated against {model_class.__name__}")
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                errors.append(f"{field}: {error['msg']}")
        except Exception as e:
            errors.append(f"Unexpected error validating {model_class.__name__}: {e}")

        result = ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, data=validated_data)

        if not result.valid:
            self.logger.error(f"Pydantic validation failed: {result.errors}")

        if self.strict and not result.valid:
            result.raise_if_invalid()

        return result

    # ============== Decorators ==============

    def validate_inputs(self, **validators: Callable[[Any], ValidationResult]) -> Callable[[F], F]:
        """Decorator to validate function inputs.

        Example:
            @validation.validate_inputs(
                path=lambda p: validation.validate_file_exists(p),
                config=lambda c: validation.validate_dict_structure(c, ["model", "temperature"])
            )
            def process_file(path: Path, config: dict) -> None:
                ...
        """

        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Map positional args to parameter names
                import inspect

                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()

                # Validate each parameter
                for param_name, validator in validators.items():
                    if param_name in bound.arguments:
                        value = bound.arguments[param_name]
                        result = validator(value)
                        if not result.valid:
                            self.logger.error(f"Validation failed for {func.__name__}.{param_name}: {result.errors}")
                            if self.strict:
                                raise ValueError(f"Invalid {param_name}: {result.errors}")

                return func(*args, **kwargs)

            return wrapper

        return decorator

    def retry_on_failure(self, max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0) -> Callable[[F], F]:
        """Decorator to retry function on failure with exponential backoff.

        Example:
            @validation.retry_on_failure(max_retries=3)
            def fetch_data() -> dict:
                ...
        """

        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                current_delay = delay

                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries:
                            self.logger.warning(
                                f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. Retrying in {current_delay}s..."
                            )
                            time.sleep(current_delay)
                            current_delay *= backoff
                        else:
                            self.logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")

                raise last_exception

            return wrapper

        return decorator

    # ============== Context Managers ==============

    @contextmanager
    def safe_file_operation(self, path: Path | str, mode: str = "r", encoding: str = "utf-8"):
        """Context manager for safe file operations with automatic cleanup.

        Example:
            with validation.safe_file_operation("data.json", "r") as f:
                data = json.load(f)
        """
        path_obj = Path(path)
        file_handle = None

        try:
            self.logger.debug(f"Opening file {path} in mode {mode}")
            file_handle = path_obj.open(mode, encoding=encoding)
            yield file_handle
        except FileNotFoundError:
            self.logger.error(f"File not found: {path}")
            raise
        except PermissionError:
            self.logger.error(f"Permission denied accessing file: {path}")
            raise
        except Exception as e:
            self.logger.error(f"Error accessing file {path}: {e}")
            raise
        finally:
            if file_handle:
                try:
                    file_handle.close()
                    self.logger.debug(f"Closed file {path}")
                except Exception as e:
                    self.logger.warning(f"Error closing file {path}: {e}")

    @contextmanager
    def timeout_protection(self, seconds: float, operation: str = "operation"):
        """Context manager for timeout protection.

        Example:
            with validation.timeout_protection(30.0, "LLM call"):
                response = llm.generate(prompt)
        """
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError(f"{operation} timed out after {seconds} seconds")

        # Set up timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(seconds))

        try:
            yield
        finally:
            # Disable alarm
            signal.alarm(0)
            # Restore old handler
            signal.signal(signal.SIGALRM, old_handler)

    # ============== Error Recovery ==============

    def with_fallback(self, primary: Callable[[], T], fallback: Callable[[], T], error_msg: str = "") -> T:
        """Execute primary function with fallback on failure.

        Example:
            data = validation.with_fallback(
                primary=lambda: load_from_api(),
                fallback=lambda: load_from_cache(),
                error_msg="API call failed, using cache"
            )
        """
        try:
            return primary()
        except Exception as e:
            if error_msg:
                self.logger.warning(f"{error_msg}: {e}")
            else:
                self.logger.warning(f"Primary operation failed, using fallback: {e}")
            return fallback()


# ============== Specialized Validators ==============


class OrchestrationValidator(ValidationFramework):
    """Specialized validator for orchestration components."""

    def validate_model_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate model configuration structure."""
        required = ["model", "temperature", "max_tokens"]
        optional = ["api_key", "api_base", "provider", "extra_kwargs"]
        return self.validate_dict_structure(config, required, optional)

    def validate_course_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate course configuration."""
        errors = []
        warnings = []

        # Check top-level structure
        result = self.validate_dict_structure(
            config, required_keys=["duration", "objectives"], optional_keys=["prerequisites", "topics", "format"]
        )

        if not result.valid:
            return result

        # Validate duration
        duration = config.get("duration")
        if isinstance(duration, str):
            if not duration.endswith(("weeks", "days", "hours")):
                warnings.append(f"Duration format unclear: {duration}")
        elif isinstance(duration, (int, float)):
            if duration <= 0:
                errors.append(f"Duration must be positive: {duration}")

        # Validate objectives
        objectives = config.get("objectives", [])
        if not isinstance(objectives, list):
            errors.append(f"Objectives must be a list, got {type(objectives).__name__}")
        elif len(objectives) == 0:
            errors.append("At least one objective is required")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, data=config)


# ============== Global Instance ==============

# Create a global validation instance for convenience
validation = ValidationFramework(strict=False)
strict_validation = ValidationFramework(strict=True)


__all__ = [
    "ValidationFramework",
    "ValidationResult",
    "OrchestrationValidator",
    "validation",
    "strict_validation",
]
