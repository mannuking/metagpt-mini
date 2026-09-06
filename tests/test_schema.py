"""Tests for the schema + pool. Pure-Python, no LLM calls required."""

from metagpt_mini.schema import Message, MessagePool


def test_message_roundtrip():
    m = Message(role="PM", content="hello", cause_by="WritePRD")
    assert m.role == "PM"
    assert m.content == "hello"
    assert m.cause_by == "WritePRD"
    assert len(m.msg_id) == 8
    assert "T" in m.created_at  # isoformat contains 'T'


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
    # by_action filters correctly across roles
    assert p.by_action("WriteCode")[0].role == "Eng"


def test_pool_ordering():
    p = MessagePool()
    p.publish(Message(role="A", content="1", cause_by="X"))
    p.publish(Message(role="B", content="2", cause_by="Y"))
    p.publish(Message(role="A", content="3", cause_by="Z"))
    assert [m.content for m in p.history()] == ["1", "2", "3"]