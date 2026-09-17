import pytest

from forgetmegraph.context.namespace import dataset_urn_is_namespaced, parse_dataset_urn


@pytest.mark.parametrize(
    ("urn", "expected"),
    [
        (
            "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)",
            ("dataset", "duckdb", "forgetme.raw.customers", "PROD"),
        ),
        (
            "urn:li:dataset:(urn:li:dataPlatform:file,forgetme.export%2Carchive,DEV)",
            ("dataset", "file", "forgetme.export%2Carchive", "DEV"),
        ),
    ],
)
def test_parse_dataset_urn_returns_structural_components(
    urn: str,
    expected: tuple[str, str, str, str],
) -> None:
    parsed = parse_dataset_urn(urn)

    assert (
        parsed.entity_type,
        parsed.platform,
        parsed.name,
        parsed.environment,
    ) == expected
    assert parsed.platform_urn == f"urn:li:dataPlatform:{parsed.platform}"


@pytest.mark.parametrize(
    "urn",
    [
        "urn:li:mlModel:(urn:li:dataPlatform:duckdb,forgetme.model.customer,PROD)",
        "urn:li:dataset:(urn:li:dataFlow:duckdb,forgetme.raw.customers,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw,copy,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:,forgetme.raw.customers,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD))",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)trailing)",
        "urn:li:dataset:(urn:li:dataPlatform:urn:li:dataFlow:duckdb,forgetme.raw.customers,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw customers,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD\t)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.\ncustomers,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.\x00customers,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.\x1bcustomers,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.\x7fcustomers,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.\u200bcustomers,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.\u202ecustomers,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.(customers),PROD)",
    ],
)
def test_parse_dataset_urn_rejects_unsupported_or_ambiguous_shapes(urn: str) -> None:
    with pytest.raises(ValueError, match="unsupported or malformed"):
        parse_dataset_urn(urn)


@pytest.mark.parametrize(
    "urn",
    [
        "urn:li:dataset:(urn:li:dataPlatform:forgetme.duckdb,other.raw.customers,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,other.raw.customers,forgetme.PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,evil.%66orgetme.raw.customers,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,evil.forgetme.raw.customers,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.,PROD)",
    ],
)
def test_namespace_check_cannot_be_satisfied_outside_dataset_name_prefix(urn: str) -> None:
    assert dataset_urn_is_namespaced(urn, "forgetme.") is False


def test_namespace_check_accepts_valid_project_dataset_name() -> None:
    urn = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)"

    assert dataset_urn_is_namespaced(urn, "forgetme.") is True
    assert dataset_urn_is_namespaced(urn, "") is False
