"""Unit tests for admin.services.auth — fake session_state, no runtime."""

import pytest

import admin.services.auth as auth_module
from admin.services.auth import current_user, is_logged_in, logout


# ------------------------------------------------------------------
# Fake Streamlit session_state
# ------------------------------------------------------------------
class _FakeSessionState(dict):
    """Behaves like a dict but raises AttributeError for missing keys."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


class _FakeStreamlit:
    """Minimal `streamlit` stub for auth tests."""

    def __init__(self):
        self.session_state = _FakeSessionState()


@pytest.fixture
def fake_st(monkeypatch):
    """Replace admin.services.auth.st with a fake and return it."""
    fake = _FakeStreamlit()
    monkeypatch.setattr(auth_module, "st", fake)
    return fake


# ==================================================================
# is_logged_in
# ==================================================================
class TestIsLoggedIn:
    def test_default_is_false(self, fake_st):
        assert is_logged_in() is False

    def test_true_after_setting(self, fake_st):
        fake_st.session_state["admin_logged_in"] = True
        assert is_logged_in() is True

    def test_false_when_explicitly_false(self, fake_st):
        fake_st.session_state["admin_logged_in"] = False
        assert is_logged_in() is False

    def test_truthy_values_are_returned(self, fake_st):
        # .get() returns the raw value; caller must be ready for
        # non-bool truthy values too.
        fake_st.session_state["admin_logged_in"] = "yes"
        assert is_logged_in() == "yes"


# ==================================================================
# current_user
# ==================================================================
class TestCurrentUser:
    def test_default_is_anonymous(self, fake_st):
        assert current_user() == "anonymous"

    def test_returns_username(self, fake_st):
        fake_st.session_state["admin_user"] = "alice"
        assert current_user() == "alice"

    def test_none_becomes_anonymous(self, fake_st):
        fake_st.session_state["admin_user"] = None
        assert current_user() == "anonymous"

    def test_empty_string_becomes_anonymous(self, fake_st):
        fake_st.session_state["admin_user"] = ""
        assert current_user() == "anonymous"

    def test_returns_system_on_exception(self, monkeypatch):
        class _Broken:
            @property
            def session_state(self):
                raise RuntimeError("boom")

        monkeypatch.setattr(auth_module, "st", _Broken())
        assert current_user() == "system"


# ==================================================================
# logout
# ==================================================================
class TestLogout:
    def test_sets_logged_in_to_false(self, fake_st):
        fake_st.session_state["admin_logged_in"] = True
        logout()
        assert fake_st.session_state["admin_logged_in"] is False

    def test_sets_user_to_none(self, fake_st):
        fake_st.session_state["admin_user"] = "admin"
        logout()
        assert fake_st.session_state["admin_user"] is None

    def test_clears_both_keys(self, fake_st):
        fake_st.session_state["admin_logged_in"] = True
        fake_st.session_state["admin_user"] = "admin"
        logout()
        assert is_logged_in() is False
        assert current_user() == "anonymous"

    def test_idempotent(self, fake_st):
        logout()
        logout()
        assert is_logged_in() is False
        assert current_user() == "anonymous"
