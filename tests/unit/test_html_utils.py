from core.html_utils import clean_html_text, clean_html_url


def test_fitnesse_link_values_are_normalized():
    assert clean_html_url('<a href="https://example.test/path">https://example.test/path</a>') == "https://example.test/path"
    assert clean_html_text('<a href="https://example.test/path">Example page</a>') == "Example page"


def test_plain_values_and_other_html_are_normalized():
    assert clean_html_url("https://example.test/path") == "https://example.test/path"
    assert clean_html_text("<span>Example &amp; page</span>") == "Example &amp; page"


def test_link_normalization_preserves_text_around_embedded_link():
    assert clean_html_text(
        '{"url":"<a href="https://example.test/path">https://example.test/path</a>",'
        '"username":"admin"}'
    ) == '{"url":"https://example.test/path","username":"admin"}'


def test_url_keeps_the_path_that_follows_a_rendered_base_url_link():
    # ${API_BASE_URL}/users/1 reaches Slim as a link to the base URL followed by the path
    assert clean_html_url('<a href="https://api.test">https://api.test</a>/users/1') == "https://api.test/users/1"
    assert clean_html_url('<a href="http://localhost:8080/">http://localhost:8080/</a>home') == "http://localhost:8080/home"
    assert clean_html_url('prefix <a href="https://a.test/x">https://a.test/x</a> suffix') == "prefix https://a.test/x suffix"
    assert clean_html_url('<a href="https://a.test/x">label') == "https://a.test/x"      # unclosed link: href wins
