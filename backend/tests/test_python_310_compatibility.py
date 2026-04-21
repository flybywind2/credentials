from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[2]


def test_backend_does_not_use_datetime_utc_constant():
    offenders = []
    utc_import = "from datetime import " + "UTC"
    utc_attribute = "datetime." + "UTC"
    for path in (ROOT / "backend").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if utc_import in text or utc_attribute in text:
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []


def test_dockerfile_uses_python_310_19_base_image():
    dockerfile = (ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")

    assert dockerfile.splitlines()[0] == "FROM python:3.10.19-slim"


def test_python_version_file_pins_python_310_19():
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.10.19"


def test_backend_python_files_parse_with_python_310_grammar():
    for path in (ROOT / "backend").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path), feature_version=(3, 10))
