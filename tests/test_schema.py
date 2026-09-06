"""Tests for schema + manifest + run_id. Pure-Python, no LLM."""

from metagpt_mini.schema import (
    Message, MessagePool, Manifest, FileEntry, new_run_id,
)


def test_message_roundtrip():
    m = Message(role="PM", content="hello", cause_by="WritePRD")
    assert m.role == "PM"
    assert m.content == "hello"
    assert m.cause_by == "WritePRD"
    assert len(m.msg_id) == 8
    assert "T" in m.created_at
    assert m.round_num == 0


def test_message_with_round():
    m = Message(role="Engineer", content="revised", cause_by="WriteCode",
                round_num=2, extra={"file_paths": ["main.py"]})
    assert m.round_num == 2
    assert m.extra["file_paths"] == ["main.py"]


def test_pool_publish_and_filter():
    p = MessagePool()
    p.publish(Message(role="PM",   content="PRD",     cause_by="WritePRD"))
    p.publish(Message(role="Arch", content="Design",  cause_by="WriteDesign"))
    p.publish(Message(role="Eng",  content="Code",     cause_by="WriteCode"))
    p.publish(Message(role="QA",   content="Tests",    cause_by="WriteTest"))

    assert len(p.history()) == 4
    assert len(p.of_role("PM")) == 1
    assert len(p.of_role("Arch")) == 1
    assert [m.cause_by for m in p.by_action("WritePRD")] == ["WritePRD"]
    assert p.by_action("WriteCode")[0].role == "Eng"


def test_pool_latest_of():
    p = MessagePool()
    p.publish(Message(role="Eng", content="v1", cause_by="WriteCode", round_num=1))
    p.publish(Message(role="Eng", content="v2", cause_by="WriteCode", round_num=2))
    latest = p.latest_of("WriteCode")
    assert latest is not None
    assert latest.content == "v2"
    assert latest.round_num == 2


def test_run_id_is_unique_and_short():
    rid1 = new_run_id("Build a CLI todo app")
    rid2 = new_run_id("Build a CLI todo app")  # same input → same hash part
    rid3 = new_run_id("Something else")
    # Same requirement, within same second → same hash + same timestamp = same id
    assert rid1 == rid2
    # Different requirement → different hash
    assert rid1 != rid3
    # Format: 5-char hex + timestamp suffix
    assert "-" in rid1
    parts = rid1.split("-")
    assert len(parts[0]) == 5
    assert all(c in "0123456789abcdef" for c in parts[0])


def test_manifest_basic():
    m = Manifest(
        project_name="cli_todo_app",
        summary="A CLI todo app",
        files=[FileEntry(path="main.py", content="print('hi')", rationale="Entry")],
        dependencies=[],
        run_instructions="python main.py",
    )
    assert m.project_name == "cli_todo_app"
    assert len(m.files) == 1
    assert m.total_chars() == len("print('hi')")
    assert m.file_paths() == ["main.py"]