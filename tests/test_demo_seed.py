from forgetmegraph.demo.seed import inspect_presence, seed_estate


def test_seed_estate_proves_subject_presence_without_exposing_raw_records(tmp_path) -> None:
    root = tmp_path / "artifacts"

    before = seed_estate(root, selector_secret="a-test-secret-that-is-long-enough")
    repeated = inspect_presence(
        root,
        customer_id=42,
        selector_secret="a-test-secret-that-is-long-enough",
    )

    assert before == repeated
    assert before["artifacts"]["raw.customers"] == 1
    assert before["artifacts"]["raw.tickets"] == 2
    assert before["artifacts"]["vectors.ticket_embeddings"] == 2
    assert before["artifacts"]["model.customer_support_classifier"] == 1
    assert before["aggregate_exemption"]["status"] == "exempt"
    assert before["selector_token"].startswith("subj_")
