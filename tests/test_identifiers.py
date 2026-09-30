import pytest

from sql_server_mcp.identifiers import InvalidIdentifierError, validate_identifier


@pytest.mark.parametrize(
    "name",
    ["Sales", "my_table", "Table123", "_private", "ABC", "db-npprod", "db-npprod-dp"],
)
def test_accepts_alphanumeric_and_underscore_names(name):
    assert validate_identifier(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "",
        "foo bar",
        "foo'bar",
        'foo"bar',
        "foo]bar",
        "foo]; DROP TABLE bar; --",
        "foo;bar",
        "foo.bar",
        "foo--bar",
        "foo/*bar*/",
    ],
)
def test_rejects_anything_outside_the_allow_list(name):
    with pytest.raises(InvalidIdentifierError):
        validate_identifier(name)
