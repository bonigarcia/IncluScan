from pathlib import Path

REPORT_DIR = Path("docs")
SNAPSHOT_DIR = REPORT_DIR / "snapshots"
RUN_DIR = REPORT_DIR / "runs"
PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "review_prompt.md"
