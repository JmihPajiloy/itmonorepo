"""Сверить исходное задание и сохранённые результаты перед сборкой отчёта."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
assert sha256((root / "task.pdf").read_bytes()).hexdigest() == "f33b16ce50f67c11b974c0ae5f50114a3bd3761b9c72836a468025e0c513d757", "Изменилось исходное задание"
suites = ET.parse(root / "verification/pytest.xml").getroot()
cases = suites.findall(".//testcase")
assert len(cases) >= 5 and not suites.findall(".//failure") and not suites.findall(".//error")
assert not suites.findall(".//skipped"), "Есть пропущенные тесты"
names = {case.attrib["name"] for case in cases}
assert {"test_duplicate_login", "test_owner_grants_reader_and_outsider_is_denied",
        "test_revocation_takes_effect_for_existing_token"} <= names
ui = json.loads((root / "verification/ui.json").read_text())
assert ui["checks"] and all(check["passed"] for check in ui["checks"])
assert ui["browser_errors"] == []
statuses = {row["status"] for row in ui["network"]}
assert {200, 201, 204, 403, 409, 422} <= statuses
log = (root / "verification/backend.txt").read_text()
events = [json.loads(line) for line in log.splitlines() if line.startswith("{")]
assert {row["event"] for row in events} >= {"registration_success", "registration_duplicate", "validation_failed", "access_denied"}
assert {row["level"] for row in events} >= {"INFO", "ERROR"}
assert "Lab4-DemoPass1!" not in log and "access_token" not in log
shots = {}
for file in sorted((root / "screenshots").iterdir()):
    if file.suffix not in {".png", ".jpg"}:
        continue
    data = file.read_bytes()
    signature = b"\x89PNG\r\n\x1a\n" if file.suffix == ".png" else b"\xff\xd8\xff"
    assert data.startswith(signature), file
    shots[file.name] = sha256(data).hexdigest()
assert len(shots) == 16 and "11-git-branch.jpg" in shots
result = {
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "task_sha256": sha256((root / "task.pdf").read_bytes()).hexdigest(),
    "pytest_passed": len(cases), "pytest_failed": 0,
    "ui_checks_passed": len(ui["checks"]), "ui_executed_at": ui["executed_at"],
    "screenshots_sha256": shots,
}
(root / "verification/summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(f"Материалы проверены: pytest {len(cases)}, UI {len(ui['checks'])}, скриншоты {len(shots)}")
