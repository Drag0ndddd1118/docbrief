from docbrief.guard import COST, DailyLedger, Limits, SessionQuota, validate_upload


def make(tmp_path, budget=100, **kw):
    lim = Limits(daily_budget=budget, **kw)
    return lim, DailyLedger(budget, tmp_path / "u.json")


def test_ledger_spends_and_refuses_at_budget(tmp_path):
    led = DailyLedger(COST["analysis"] + COST["question"], tmp_path / "u.json")
    assert led.try_spend("analysis") and led.try_spend("question")
    assert not led.try_spend("question") and led.remaining() == 0
    assert led.used() == COST["analysis"] + COST["question"]


def test_ledger_persists_and_resets_on_new_day(tmp_path, monkeypatch):
    led = DailyLedger(100, tmp_path / "u.json")
    led.try_spend("deep")
    assert DailyLedger(100, tmp_path / "u.json").used() == COST["deep"]  # shared across instances/processes via the file
    monkeypatch.setattr(DailyLedger, "_today", staticmethod(lambda: "2099-01-01"))
    assert led.used() == 0


def test_session_quota_caps_each_kind(tmp_path):
    lim, led = make(tmp_path, max_questions=2, max_deep_questions=1)
    q = SessionQuota({}, lim, led)
    assert q.spend("question") is None and q.spend("question") is None
    assert "Session limit" in q.spend("question")
    assert q.left("question") == 0 and q.used("question") == 2
    assert q.spend("deep") is None and q.spend("deep") is not None


def test_session_quota_blocked_by_daily_budget_without_spending_session(tmp_path):
    lim, led = make(tmp_path, budget=1)
    q = SessionQuota({}, lim, led)
    assert "budget" in q.spend("question")
    assert q.used("question") == 0  # a refusal costs nothing


def test_sessions_are_independent(tmp_path):
    lim, led = make(tmp_path, max_factchecks=1)
    a, b = SessionQuota({}, lim, led), SessionQuota({}, lim, led)
    assert a.spend("factcheck") is None and a.spend("factcheck") is not None
    assert b.spend("factcheck") is None


def test_validate_upload():
    lim = Limits(max_pdf_mb=1, max_pages=10)
    assert validate_upload(500_000, 5, lim) is None
    assert "MB" in validate_upload(2 * 1024 * 1024, None, lim)
    assert "pages" in validate_upload(1000, 11, lim)


def test_limits_from_env(monkeypatch):
    monkeypatch.setenv("DOCBRIEF_MAX_QUESTIONS", "4")
    monkeypatch.setenv("DOCBRIEF_DAILY_BUDGET", "oops")  # invalid -> default
    lim = Limits.from_env()
    assert lim.max_questions == 4 and lim.daily_budget == Limits().daily_budget
