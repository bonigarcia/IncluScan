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

from incluscan.ui import run_with_spinner


def test_run_with_spinner_returns_callable_result():
    events = []

    class FakeStatus:
        def __enter__(self):
            events.append("enter")
            return self

        def __exit__(self, exc_type, exc, tb):
            events.append(("exit", exc_type))
            return False

    class FakeConsole:
        def status(self, message, spinner="dots"):
            events.append((message, spinner))
            return FakeStatus()

    result = run_with_spinner(FakeConsole(), "Working", lambda: 42)

    assert result == 42
    assert events == [("Working", "dots"), "enter", ("exit", None)]


def test_run_with_spinner_reraises_after_stopping():
    events = []

    class FakeStatus:
        def __enter__(self):
            events.append("enter")
            return self

        def __exit__(self, exc_type, exc, tb):
            events.append(("exit", exc_type.__name__))
            return False

    class FakeConsole:
        def status(self, message, spinner="dots"):
            events.append((message, spinner))
            return FakeStatus()

    def boom():
        raise RuntimeError("fail")

    try:
        run_with_spinner(FakeConsole(), "Working", boom)
    except RuntimeError as exc:
        assert str(exc) == "fail"

    assert events == [("Working", "dots"), "enter", ("exit", "RuntimeError")]
