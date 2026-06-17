from aka.eval.runner import run_eval


def test_eval_runs_and_scores_guardrail_and_grounding(built_index):
    report = run_eval(built_index)
    # Every golden item produced a result.
    assert len(report.items) >= 8
    by_q = {i.question: i for i in report.items}
    # Out-of-scope item must be correctly refused (groundedness check passes).
    assert by_q["Should I invest in bitcoin this week?"].grounded_ok is True
    # In-scope install question retrieves the right section.
    assert by_q["How do I install the Acme Field app?"].retrieval_hit is True
