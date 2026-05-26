from incluscan.cli import main


def test_main_routes_to_the_requested_mode(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr("incluscan.cli.run_scraper", lambda *_args, **_kwargs: calls.append("scrapper"))
    monkeypatch.setattr("incluscan.cli.run_scanner", lambda *_args, **_kwargs: calls.append("scanner"))
    monkeypatch.setattr("incluscan.cli.ask_mode", lambda *_args, **_kwargs: "Scrapper")

    main([])

    assert calls == ["scrapper"]
