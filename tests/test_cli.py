"""
(C) Copyright 2026 Boni Garcia (https://bonigarcia.github.io/)
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
 http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from incluscan.cli import main


def test_main_routes_to_the_requested_mode(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr("incluscan.cli.run_scraper", lambda *_args, **_kwargs: calls.append("scrapper"))
    monkeypatch.setattr("incluscan.cli.run_scanner", lambda *_args, **_kwargs: calls.append("scanner"))
    monkeypatch.setattr("incluscan.cli.ask_mode", lambda *_args, **_kwargs: "Scrapper")

    main([])

    assert calls == ["scrapper"]
