from unittest.mock import patch

from readme_first_screen.input import load_readme


def test_load_readme_fetches_root_github_blob_readme_as_raw_url():
    with patch("readme_first_screen.input._fetch_url", return_value="# Demo") as fetch_url:
        text, source = load_readme("https://github.com/acme/demo/blob/main/README.md")

    raw_url = "https://raw.githubusercontent.com/acme/demo/main/README.md"
    assert text == "# Demo"
    assert source == raw_url
    fetch_url.assert_called_once_with(raw_url)


def test_load_readme_fetches_nested_github_blob_readme_as_raw_url():
    with patch("readme_first_screen.input._fetch_url", return_value="# Docs") as fetch_url:
        text, source = load_readme("https://github.com/acme/demo/blob/main/docs/README.md")

    raw_url = "https://raw.githubusercontent.com/acme/demo/main/docs/README.md"
    assert text == "# Docs"
    assert source == raw_url
    fetch_url.assert_called_once_with(raw_url)
