"""Чтение JSONL: BOM, повторяющиеся ключи, физические номера строк. Сеть не используется."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from legal_agent_harness import (  # noqa: E402
    CaseValidationError,
    HarnessError,
    load_cases,
    load_responses,
)


def _case(case_id: str) -> dict:
    return {
        "case_id": case_id,
        "source": {
            "authority": "Федеральное Собрание РФ",
            "jurisdiction": "RU",
            "doc_type": "amending_act",
            "identifier": "ФЗ № 35-ФЗ",
            "coordinate": "ст. 1 п. 1",
            "effective_date": "2014-10-01",
        },
        "expected": {
            "norm_id": "GK-RF-1335.1",
            "predicate": "введена",
            "subject": "ГК РФ ст. 1335.1",
            "object": "право изготовителя базы данных",
            "confidence": 0.9,
        },
    }


def _response(case_id: str) -> dict:
    return {"case_id": case_id, "response": {"status": "ok", "expected": _case(case_id)["expected"]}}


def _line(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _write(path, text: str, encoding: str = "utf-8") -> str:
    with open(path, "w", encoding=encoding) as fh:
        fh.write(text)
    return str(path)


def test_utf8_bom_is_accepted_for_cases(tmp_path):
    path = _write(tmp_path / "cases.jsonl", _line(_case("a-1")) + "\n", encoding="utf-8-sig")
    assert [c["case_id"] for c in load_cases(path)] == ["a-1"]


def test_utf8_bom_is_accepted_for_responses(tmp_path):
    path = _write(tmp_path / "responses.jsonl", _line(_response("a-1")) + "\n", encoding="utf-8-sig")
    assert set(load_responses(path)) == {"a-1"}


def test_duplicate_key_inside_record_is_rejected(tmp_path):
    # Второе "predicate" молча подменило бы первое: json.loads берёт последнее значение.
    line = _line(_case("a-1")).replace(
        '"predicate": "введена"', '"predicate": "введена", "predicate": "изменена"'
    )
    path = _write(tmp_path / "cases.jsonl", line + "\n")
    with pytest.raises(HarnessError) as excinfo:
        load_cases(path)
    message = str(excinfo.value)
    assert "повторяющийся ключ 'predicate'" in message
    assert ":1:" in message


def test_duplicate_top_level_key_in_responses_is_rejected(tmp_path):
    line = '{"case_id": "a-1", "case_id": "a-2", "response": {"status": "ok"}}'
    path = _write(tmp_path / "responses.jsonl", line + "\n")
    with pytest.raises(HarnessError) as excinfo:
        load_responses(path)
    assert "повторяющийся ключ 'case_id'" in str(excinfo.value)


def test_error_points_to_physical_line_after_comments_and_blank_lines(tmp_path):
    broken = _case("a-2")
    broken["expected"]["predicate"] = "неизвестный тип"
    text = "# комментарий эксперта\n" + _line(_case("a-1")) + "\n\n" + _line(broken) + "\n"
    path = _write(tmp_path / "cases.jsonl", text)
    with pytest.raises(CaseValidationError) as excinfo:
        load_cases(path)
    # Битая запись — вторая по счёту, но в файле она на строке 4.
    assert f"{path}:4:" in str(excinfo.value)


def test_duplicate_case_id_reports_physical_lines(tmp_path):
    text = "# шапка\n" + _line(_case("a-1")) + "\n" + "\n" + _line(_case("a-1")) + "\n"
    path = _write(tmp_path / "cases.jsonl", text)
    with pytest.raises(CaseValidationError) as excinfo:
        load_cases(path)
    message = str(excinfo.value)
    assert f"{path}:4:" in message
    assert "строке 2" in message


def test_cli_validate_cases_reports_duplicate_key(tmp_path):
    line = _line(_case("a-1")).replace('"case_id": "a-1"', '"case_id": "a-1", "case_id": "a-1"')
    path = _write(tmp_path / "cases.jsonl", line + "\n")
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "run_harness.py"), "validate-cases", path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        check=False,
    )
    assert proc.returncode == 1
    assert "повторяющийся ключ" in proc.stderr
