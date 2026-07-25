import pytest

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


def test_reset_refuses_nonempty_unmarked_directory(tmp_path) -> None:
    root = tmp_path / "not-the-project-fixture"
    root.mkdir()
    sentinel = root / "must-survive.txt"
    sentinel.write_text("not disposable")

    with pytest.raises(ValueError, match="unmarked"):
        seed_estate(root)

    assert sentinel.read_text() == "not disposable"
