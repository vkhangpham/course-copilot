from pathlib import Path

from apps.orchestrator.ta_roles.timeline_synthesizer import TimelineSynthesizer

DATASET_TIMELINE = Path("data/handcrafted/database_systems/timeline.csv")


def test_timeline_synthesizer_with_real_dataset() -> None:
    synth = TimelineSynthesizer()
    events = synth.build(DATASET_TIMELINE, limit=3)

    assert events, "Expected timeline events from dataset"
    assert events[0].event.startswith("Codd"), events[0].event
    assert events[0].year == 1970


def test_timeline_synthesizer_filters_concepts(tmp_path: Path) -> None:
    csv_path = tmp_path / "timeline.csv"
    csv_path.write_text(
        """year,event,why_it_matters,related_concepts
1970,Codd publishes relational model,Defines relational model,relational_model
1980,ARIES recovery paper,Improves recovery algorithms,recovery;logging
        """.strip(),
        encoding="utf-8",
    )

    synth = TimelineSynthesizer()
    events = synth.build(csv_path, concepts=["recovery"])

    assert len(events) == 1
    assert "ARIES" in events[0].event
    assert events[0].concepts == ["recovery", "logging"]


def test_timeline_synthesizer_handles_missing_year(tmp_path: Path) -> None:
    csv_path = tmp_path / "timeline.csv"
    csv_path.write_text(
        """year,event,why_it_matters
,Critical milestone,Impact description
        """.strip(),
        encoding="utf-8",
    )

    synth = TimelineSynthesizer()
    events = synth.build(csv_path)

    assert len(events) == 1
    assert events[0].year is None


def test_timeline_synthesizer_handles_comma_delimited_concepts(tmp_path: Path) -> None:
    csv_path = tmp_path / "timeline.csv"
    csv_path.write_text(
        """year,event,why_it_matters,related_concepts
1985,Prototype release,Proof of concept,"distributed_transactions, recovery"
        """.strip(),
        encoding="utf-8",
    )

    synth = TimelineSynthesizer()
    events = synth.build(csv_path, concepts=["recovery"])

    assert len(events) == 1
    assert events[0].concepts == ["distributed_transactions", "recovery"]
