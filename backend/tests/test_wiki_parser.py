"""Tests for wiki parser - deadline table extraction."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime
from services.wiki_parser import _parse_table, _parse_date, _find_column, _clean_subject
from bs4 import BeautifulSoup


# Sample HTML from wiki.cs.hse.ru style page
SAMPLE_WIKI_HTML = """
<html>
<head><title>Test</title></head>
<body>
<h1 id="firstHeading">Математический Анализ 2 на ПМИ 2025/26 (пилотный поток)</h1>
<div id="mw-content-text">
<h2>Сроки сдачи</h2>
<p>Один раз за курс студент имеет право взять отсрочку на один дедлайн по ДЗ на три дня.</p>
<table class="wikitable">
<tr><th>Задание</th><th>Дедлайн</th></tr>
<tr><td>ДЗ 1</td><td>14.09, 23:59</td></tr>
<tr><td>ДЗ 2</td><td>21.09, 23:59</td></tr>
<tr><td>ДЗ 3</td><td>28.09, 23:59</td></tr>
<tr><td>ДЗ 4</td><td>12.10, 23:59</td></tr>
<tr><td>ДЗ 5</td><td>19.10, 23:59</td></tr>
<tr><td>ДЗ 6</td><td>26.10, 23:59</td></tr>
<tr><td>ДЗ 7</td><td>02.11, 23:59</td></tr>
<tr><td>ДЗ 8</td><td>09.11, 23:59</td></tr>
<tr><td>ДЗ 9</td><td>16.11, 23:59</td></tr>
<tr><td>ДЗ 10</td><td>30.11, 23:59</td></tr>
<tr><td>ДЗ 11</td><td>14.12, 23:59</td></tr>
<tr><td>ДЗ 12</td><td>21.12, 23:59</td></tr>
</table>
</div>
</body>
</html>
"""


class TestParseDate:
    def test_standard_date(self):
        result = _parse_date("14.09, 23:59")
        assert result is not None
        assert result.month == 9
        assert result.day == 14
        assert result.hour == 23
        assert result.minute == 59

    def test_date_with_year(self):
        result = _parse_date("14.09.2025, 23:59")
        assert result is not None
        assert result.year == 2025
        assert result.month == 9

    def test_date_short_year(self):
        result = _parse_date("14.09.25, 23:59")
        assert result is not None
        assert result.year == 2025

    def test_date_no_time(self):
        result = _parse_date("14.09")
        assert result is not None
        assert result.hour == 23
        assert result.minute == 59

    def test_invalid_date(self):
        result = _parse_date("not a date")
        assert result is None

    def test_empty_string(self):
        result = _parse_date("")
        assert result is None


class TestFindColumn:
    def test_find_task_column(self):
        headers = ["задание", "дедлайн"]
        assert _find_column(headers, ["задание", "задача"]) == 0

    def test_find_deadline_column(self):
        headers = ["задание", "дедлайн"]
        assert _find_column(headers, ["дедлайн", "срок"]) == 1

    def test_not_found(self):
        headers = ["имя", "оценка"]
        assert _find_column(headers, ["дедлайн"]) == -1

    def test_partial_match(self):
        headers = ["номер задания", "срок сдачи"]
        # "задани" is a substring of "задания" which is in "номер задания"
        assert _find_column(headers, ["задани"]) == 0
        assert _find_column(headers, ["срок"]) == 1
        # No match at all
        assert _find_column(headers, ["экзамен"]) == -1


class TestCleanSubject:
    def test_with_year(self):
        result = _clean_subject("Математический Анализ 2 на ПМИ 2025/26 (пилотный поток)")
        assert "Математический Анализ" in result
        assert "2025" not in result

    def test_plain_name(self):
        result = _clean_subject("Линейная алгебра")
        assert result == "Линейная алгебра"


class TestParseTable:
    def test_parses_all_deadlines(self):
        soup = BeautifulSoup(SAMPLE_WIKI_HTML, "html.parser")
        table = soup.find("table", class_="wikitable")
        deadlines = _parse_table(table, "Математический Анализ 2")

        assert len(deadlines) == 12
        assert deadlines[0]["task_name"] == "ДЗ 1"
        assert deadlines[0]["subject"] == "Математический Анализ 2"
        assert deadlines[0]["confidence"] == 0.95
        assert "09-14" in deadlines[0]["due_date"]

    def test_last_deadline(self):
        soup = BeautifulSoup(SAMPLE_WIKI_HTML, "html.parser")
        table = soup.find("table", class_="wikitable")
        deadlines = _parse_table(table, "Матан")

        assert deadlines[-1]["task_name"] == "ДЗ 12"
        assert "12-21" in deadlines[-1]["due_date"]

    def test_empty_table(self):
        html = '<table class="wikitable"><tr><th>Имя</th><th>Оценка</th></tr></table>'
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        deadlines = _parse_table(table, "Test")
        assert deadlines == []

    def test_table_with_different_headers(self):
        html = """
        <table class="wikitable">
        <tr><th>Название</th><th>Срок</th></tr>
        <tr><td>КР 1</td><td>15.10, 18:00</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        # "Название" won't match our keywords, but "Срок" will
        deadlines = _parse_table(table, "Алгебра")
        assert len(deadlines) == 1
        assert deadlines[0]["task_name"] == "КР 1"


class TestFullPageParsing:
    def test_subject_extraction(self):
        soup = BeautifulSoup(SAMPLE_WIKI_HTML, "html.parser")
        title_tag = soup.find("h1", id="firstHeading")
        subject = _clean_subject(title_tag.get_text(strip=True))
        assert "Математический Анализ" in subject

    def test_finds_wikitable(self):
        soup = BeautifulSoup(SAMPLE_WIKI_HTML, "html.parser")
        tables = soup.find_all("table", class_="wikitable")
        assert len(tables) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
