from aka.domain.events import InteractionLogged
from aka.domain.models import ChatContext, Chunk
from aka.observability.sink import MemoryEventSink
from aka.pipeline.container import build_chat_service
from aka.pipeline.stages import GroundingStage


def test_in_scope_question_is_grounded_and_cited(chat_service):
    result = chat_service.ask("How do I install the Acme Field app?")
    answer = result.context.answer
    assert answer is not None
    assert answer.grounded is True
    assert answer.citations, "a grounded answer must carry citations"
    # The Install section is retrieved (hit@k); citation selection is the LLM's job.
    assert any("Install" in c.section_path for c in result.context.chunks)


def test_guardrail_rejects_out_of_scope(chat_service):
    result = chat_service.ask("Should I invest in bitcoin this week?")
    ctx = result.context
    assert ctx.rejected is True
    assert ctx.answer.grounded is False
    assert ctx.metadata.get("reject_reason") == "guardrail"


def _chunk(score: float) -> Chunk:
    return Chunk(
        id="c1", doc_id="d", doc_title="T", text="x", section_path="S",
        metadata={"score": score},
    )


def test_grounding_escalates_when_no_chunks():
    ctx = GroundingStage(relevance_floor=0.25).execute(ChatContext(question="q"))
    assert ctx.rejected is True
    assert ctx.answer.grounded is False
    assert ctx.metadata["reject_reason"] == "low_relevance"


def test_grounding_escalates_below_floor():
    ctx = ChatContext(question="q", chunks=[_chunk(0.1)], metadata={"top_score": 0.1})
    ctx = GroundingStage(relevance_floor=0.25).execute(ctx)
    assert ctx.rejected is True
    assert ctx.answer.grounded is False


def test_grounding_passes_above_floor():
    ctx = ChatContext(question="q", chunks=[_chunk(0.9)], metadata={"top_score": 0.9})
    ctx = GroundingStage(relevance_floor=0.25).execute(ctx)
    assert ctx.rejected is False
    assert ctx.answer is None  # generation happens in a later stage


def test_recommendations_present_for_grounded_answer(chat_service):
    result = chat_service.ask("How do I authorize the app the first time?")
    assert result.context.recommendations, "expected related-topic suggestions"


def test_interaction_event_emitted(built_index):
    sink = MemoryEventSink()
    service = build_chat_service(built_index, sink=sink)
    service.ask("How do I start a visit?")
    assert len(sink.events) == 1
    event = sink.events[0]
    assert isinstance(event, InteractionLogged)
    assert event.grounded is True
    assert event.chunk_ids
