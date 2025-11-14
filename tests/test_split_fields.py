from ccopilot.utils.split_fields import split_fields


def test_split_fields_handles_semicolons() -> None:
    assert split_fields("relational_model;query_planning") == ["relational_model", "query_planning"]


def test_split_fields_handles_comma_sequences() -> None:
    assert split_fields(["relational_model,storage", "transitions"]) == [
        "relational_model",
        "storage",
        "transitions",
    ]


def test_split_fields_handles_empty_values() -> None:
    assert split_fields(None) == []
    assert split_fields("") == []
    assert split_fields([None, ""]) == []
