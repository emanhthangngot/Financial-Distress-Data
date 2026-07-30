from scripts.check_documentation import check_documentation


def test_reviewer_documentation_links_sizes_and_docstrings_are_valid():
    assert check_documentation(__import__("pathlib").Path.cwd(), 800) == []
