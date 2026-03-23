from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from nova_school_server.curriculum import CurriculumService
from nova_school_server.curriculum_catalog import get_course, list_courses
from nova_school_server.database import SchoolRepository


class _Session:
    def __init__(self, username: str, *, is_teacher: bool = False, permissions: dict | None = None, group_ids: list[str] | None = None) -> None:
        self.username = username
        self.is_teacher = is_teacher
        self.permissions = permissions or {}
        self.group_ids = group_ids or []


def _correct_answers(questions: list[dict]) -> dict[str, object]:
    answers: dict[str, object] = {}
    for question in questions:
        if question["type"] == "single":
            answers[question["id"]] = question["correct"][0]
        elif question["type"] == "multi":
            answers[question["id"]] = list(question["correct"])
        elif question["type"] == "text":
            answers[question["id"]] = question["accepted"][0]
    return answers


def _custom_course_payload() -> dict:
    return {
        "course_id": "python-werkstatt-eigenkurs",
        "title": "Python Werkstatt",
        "subtitle": "Eigener schulischer Aufbaukurs",
        "subject_area": "Python Projekte",
        "summary": "Lehrkraft-eigener Modullehrplan fuer Projektarbeit.",
        "audience": "Klasse 9/10",
        "estimated_hours": 4,
        "certificate_title": "Nova School Zertifikat Python Werkstatt",
        "pass_ratio": 0.6,
        "final_pass_ratio": 1.0,
        "certificate_theme": {
            "label": "Python Werkstatt",
            "accent": "#126d67",
            "accent_dark": "#0a4d49",
            "warm": "#8f412f",
            "paper": "#fbf3e5",
        },
        "modules": [
            {
                "module_id": "m01_funktionen",
                "title": "Funktionen in Projekten",
                "estimated_minutes": 35,
                "objectives": ["Funktionen planen", "Parameter einsetzen"],
                "lesson_markdown": "## Funktionen\n\nSchueler planen kleine Hilfsfunktionen fuer Projekte.",
                "quiz_pass_ratio": 0.5,
                "questions": [
                    {
                        "id": "f1",
                        "type": "single",
                        "prompt": "Welche Anweisung beendet eine Funktion mit einem Rueckgabewert?",
                        "options": [
                            {"id": "a", "label": "return"},
                            {"id": "b", "label": "yield"},
                        ],
                        "correct": ["a"],
                        "points": 1,
                        "explanation": "return gibt Werte an den Aufrufer zurueck.",
                    }
                ],
            }
        ],
        "final_assessment": {
            "assessment_id": "python-werkstatt-final",
            "title": "Abschlusspruefung Python Werkstatt",
            "instructions": "Alle Fragen muessen korrekt beantwortet werden.",
            "questions": [
                {
                    "id": "ff1",
                    "type": "single",
                    "prompt": "Welche Funktion gibt Text auf der Konsole aus?",
                    "options": [
                        {"id": "a", "label": "print"},
                        {"id": "b", "label": "input"},
                    ],
                    "correct": ["a"],
                    "points": 1,
                    "explanation": "print erzeugt die Ausgabe.",
                },
                {
                    "id": "ff2",
                    "type": "text",
                    "prompt": "Welches Stichwort startet eine Schleife ueber eine Liste in Python?",
                    "accepted": ["for"],
                    "points": 1,
                    "explanation": "for wird fuer Iterationen ueber Listen genutzt.",
                    "placeholder": "Antwort",
                },
            ],
        },
    }


class CurriculumServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repository = SchoolRepository(Path(self.tmp.name) / "school.db")
        self.service = CurriculumService(self.repository)
        self.repository.create_user("teacher", "Lehrkraft", "hash", "salt", "teacher", permissions={"curriculum.use": True, "curriculum.manage": True})
        self.repository.create_user("student", "Schueler", "hash", "salt", "student", permissions={"curriculum.use": True})
        self.repository.create_group("python-a", "Python A")
        self.repository.add_membership("student", "python-a")
        self.teacher = _Session("teacher", is_teacher=True, permissions={"curriculum.use": True, "curriculum.manage": True})
        self.student = _Session("student", permissions={"curriculum.use": True}, group_ids=["python-a"])

    def tearDown(self) -> None:
        self.repository.close()
        self.tmp.cleanup()

    def test_course_is_locked_until_released_for_student(self) -> None:
        dashboard = self.service.dashboard(self.student)
        course = next(item for item in dashboard["courses"] if item["course_id"] == "python-grundlagen")
        self.assertFalse(course["release"]["enabled"])
        self.assertEqual(course["modules"][0]["status"], "locked")

        release = self.service.set_release(self.teacher, "python-grundlagen", "user", "student", True, "Start nach Einstiegsstunde")
        self.assertTrue(release["enabled"])

        dashboard = self.service.dashboard(self.student)
        course = next(item for item in dashboard["courses"] if item["course_id"] == "python-grundlagen")
        self.assertTrue(course["release"]["enabled"])
        self.assertEqual(course["modules"][0]["status"], "available")
        self.assertEqual(course["modules"][1]["status"], "locked")

    def test_dashboard_exposes_multiple_courses(self) -> None:
        dashboard = self.service.dashboard(self.student)
        course_ids = {item["course_id"] for item in dashboard["courses"]}
        self.assertGreaterEqual(len(list_courses()), 5)
        self.assertIn("python-grundlagen", course_ids)
        self.assertIn("datenanalyse-mit-python", course_ids)
        self.assertIn("web-frontend-grundlagen", course_ids)
        self.assertIn("cpp-grundlagen", course_ids)
        self.assertIn("java-oop-grundlagen", course_ids)

    def test_group_release_enables_course_for_group_member(self) -> None:
        self.service.set_release(self.teacher, "python-grundlagen", "group", "python-a", True, "Freigabe fuer Kursgruppe")

        dashboard = self.service.dashboard(self.student)
        course = next(item for item in dashboard["courses"] if item["course_id"] == "python-grundlagen")
        self.assertTrue(course["release"]["enabled"])
        self.assertEqual(course["release"]["scope_type"], "group")
        self.assertEqual(course["modules"][0]["status"], "available")

    def test_module_progression_unlocks_next_module(self) -> None:
        self.service.set_release(self.teacher, "python-grundlagen", "user", "student", True)
        course = get_course("python-grundlagen")
        assert course is not None

        first_module = course["modules"][0]
        result = self.service.submit_assessment(
            self.student,
            "python-grundlagen",
            first_module["module_id"],
            "module",
            _correct_answers(first_module["questions"]),
        )

        self.assertTrue(result["passed"])
        course_payload = result["course"]
        self.assertTrue(next(item for item in course_payload["modules"] if item["module_id"] == first_module["module_id"])["passed"])
        self.assertEqual(course_payload["modules"][1]["status"], "available")
        self.assertFalse(course_payload["progress"]["final_unlocked"])

    def test_final_exam_issues_certificate_after_all_modules(self) -> None:
        self.service.set_release(self.teacher, "python-grundlagen", "user", "student", True)
        course = get_course("python-grundlagen")
        assert course is not None

        for module in course["modules"]:
            result = self.service.submit_assessment(
                self.student,
                "python-grundlagen",
                module["module_id"],
                "module",
                _correct_answers(module["questions"]),
            )
            self.assertTrue(result["passed"], module["module_id"])

        final_result = self.service.submit_assessment(
            self.student,
            "python-grundlagen",
            "",
            "final",
            _correct_answers(course["final_assessment"]["questions"]),
        )

        self.assertTrue(final_result["passed"])
        self.assertIsNotNone(final_result["certificate"])
        self.assertEqual(final_result["certificate"]["status"], "issued")

        dashboard = self.service.dashboard(self.student)
        course_payload = next(item for item in dashboard["courses"] if item["course_id"] == "python-grundlagen")
        self.assertTrue(course_payload["progress"]["certified"])
        self.assertTrue(course_payload["progress"]["final_passed"])

    def test_attempt_history_returns_all_submissions_for_teacher_view(self) -> None:
        self.service.set_release(self.teacher, "python-grundlagen", "user", "student", True)
        course = get_course("python-grundlagen")
        assert course is not None
        first_module = course["modules"][0]

        failed = self.service.submit_assessment(
            self.student,
            "python-grundlagen",
            first_module["module_id"],
            "module",
            {first_module["questions"][0]["id"]: "x"},
        )
        self.assertFalse(failed["passed"])

        passed = self.service.submit_assessment(
            self.student,
            "python-grundlagen",
            first_module["module_id"],
            "module",
            _correct_answers(first_module["questions"]),
        )
        self.assertTrue(passed["passed"])

        history = self.service.attempt_history("python-grundlagen", "student")
        self.assertEqual(history["learner"]["username"], "student")
        self.assertEqual(history["course"]["course_id"], "python-grundlagen")
        self.assertEqual(len(history["attempts"]), 2)
        self.assertEqual(history["attempts"][0]["module_title"], first_module["title"])
        self.assertIn("feedback", history["attempts"][0])

    def test_certificate_pdf_is_generated_with_school_branding(self) -> None:
        self.service.set_release(self.teacher, "python-grundlagen", "user", "student", True)
        course = get_course("python-grundlagen")
        assert course is not None

        for module in course["modules"]:
            self.service.submit_assessment(
                self.student,
                "python-grundlagen",
                module["module_id"],
                "module",
                _correct_answers(module["questions"]),
            )
        self.service.submit_assessment(
            self.student,
            "python-grundlagen",
            "",
            "final",
            _correct_answers(course["final_assessment"]["questions"]),
        )

        logo_path = Path(self.tmp.name) / "school-logo.png"
        Image.new("RGB", (24, 24), (18, 109, 103)).save(logo_path)
        certificate = self.service.prepare_certificate_metadata(
            "student",
            "python-grundlagen",
            verification_url="http://127.0.0.1:8877/certificate/verify?certificate_id=python-grundlagen:student",
            signatory_name="Claudia Beispiel",
            signatory_title="Fachschaft Informatik",
            logo_path=str(logo_path),
        )
        self.assertIsNotNone(certificate)

        payload = self.service.build_certificate_pdf(self.student, "python-grundlagen", "Nova Gesamtschule")
        self.assertEqual(payload["content_type"], "application/pdf")
        self.assertTrue(payload["filename"].endswith(".pdf"))
        self.assertTrue(payload["content"].startswith(b"%PDF-1.4"))
        self.assertIn("Nova Gesamtschule".encode("cp1252"), payload["content"])
        self.assertIn("Python Grundlagen".encode("cp1252"), payload["content"])
        self.assertIn("Claudia Beispiel".encode("cp1252"), payload["content"])
        self.assertIn("Pruefcode".encode("cp1252"), payload["content"])
        self.assertIn("Programmierung mit Python".encode("cp1252"), payload["content"])

    def test_course_specific_certificate_design_renders_subject_label(self) -> None:
        self.service.set_release(self.teacher, "datenanalyse-mit-python", "user", "student", True)
        course = get_course("datenanalyse-mit-python")
        assert course is not None

        for module in course["modules"]:
            self.service.submit_assessment(
                self.student,
                "datenanalyse-mit-python",
                module["module_id"],
                "module",
                _correct_answers(module["questions"]),
            )
        self.service.submit_assessment(
            self.student,
            "datenanalyse-mit-python",
            "",
            "final",
            _correct_answers(course["final_assessment"]["questions"]),
        )
        payload = self.service.build_certificate_pdf(self.student, "datenanalyse-mit-python", "Nova Gesamtschule")
        self.assertIn("Datenanalyse und Visualisierung".encode("cp1252"), payload["content"])

    def test_cpp_course_can_be_completed_and_renders_subject_label(self) -> None:
        self.service.set_release(self.teacher, "cpp-grundlagen", "user", "student", True)
        course = get_course("cpp-grundlagen")
        assert course is not None

        for module in course["modules"]:
            result = self.service.submit_assessment(
                self.student,
                "cpp-grundlagen",
                module["module_id"],
                "module",
                _correct_answers(module["questions"]),
            )
            self.assertTrue(result["passed"], module["module_id"])

        final_result = self.service.submit_assessment(
            self.student,
            "cpp-grundlagen",
            "",
            "final",
            _correct_answers(course["final_assessment"]["questions"]),
        )
        self.assertTrue(final_result["passed"])
        self.assertIsNotNone(final_result["certificate"])

        payload = self.service.build_certificate_pdf(self.student, "cpp-grundlagen", "Nova Gesamtschule")
        self.assertIn("Programmierung mit C++".encode("cp1252"), payload["content"])

    def test_java_course_can_be_completed_and_renders_subject_label(self) -> None:
        self.service.set_release(self.teacher, "java-oop-grundlagen", "user", "student", True)
        course = get_course("java-oop-grundlagen")
        assert course is not None

        for module in course["modules"]:
            result = self.service.submit_assessment(
                self.student,
                "java-oop-grundlagen",
                module["module_id"],
                "module",
                _correct_answers(module["questions"]),
            )
            self.assertTrue(result["passed"], module["module_id"])

        final_result = self.service.submit_assessment(
            self.student,
            "java-oop-grundlagen",
            "",
            "final",
            _correct_answers(course["final_assessment"]["questions"]),
        )
        self.assertTrue(final_result["passed"])
        self.assertIsNotNone(final_result["certificate"])

        payload = self.service.build_certificate_pdf(self.student, "java-oop-grundlagen", "Nova Gesamtschule")
        self.assertIn("Objektorientierte Programmierung mit Java".encode("cp1252"), payload["content"])

    def test_verification_page_renders_certificate_details(self) -> None:
        self.service.set_release(self.teacher, "python-grundlagen", "user", "student", True)
        course = get_course("python-grundlagen")
        assert course is not None

        for module in course["modules"]:
            self.service.submit_assessment(
                self.student,
                "python-grundlagen",
                module["module_id"],
                "module",
                _correct_answers(module["questions"]),
            )
        self.service.submit_assessment(
            self.student,
            "python-grundlagen",
            "",
            "final",
            _correct_answers(course["final_assessment"]["questions"]),
        )
        self.service.prepare_certificate_metadata(
            "student",
            "python-grundlagen",
            verification_url="http://127.0.0.1:8877/certificate/verify?certificate_id=python-grundlagen:student",
        )

        html = self.service.render_certificate_verification_page("python-grundlagen:student", "Nova Gesamtschule")
        self.assertIn("Zertifikat verifiziert", html)
        self.assertIn("Schueler", html)
        self.assertIn("Python Grundlagen", html)
        self.assertIn("python-grundlagen:student", html)

    def test_custom_course_is_persisted_and_visible_in_dashboard(self) -> None:
        payload = _custom_course_payload()
        saved = self.service.save_custom_course(self.teacher, payload)

        self.assertTrue(saved["is_custom"])
        self.assertEqual(saved["course_id"], payload["course_id"])
        self.assertEqual(saved["created_by"], "teacher")
        self.assertEqual(saved["updated_by"], "teacher")

        teacher_dashboard = self.service.dashboard(self.teacher)
        managed_ids = {item["course_id"] for item in teacher_dashboard["manager"]["course_definitions"]}
        visible_ids = {item["course_id"] for item in teacher_dashboard["courses"]}
        self.assertIn(payload["course_id"], managed_ids)
        self.assertIn(payload["course_id"], visible_ids)

        student_dashboard = self.service.dashboard(self.student)
        student_course = next(item for item in student_dashboard["courses"] if item["course_id"] == payload["course_id"])
        self.assertFalse(student_course["release"]["enabled"])
        self.assertEqual(student_course["modules"][0]["status"], "locked")

    def test_custom_course_uses_final_exam_threshold_and_issues_certificate(self) -> None:
        payload = _custom_course_payload()
        saved = self.service.save_custom_course(self.teacher, payload)
        self.service.set_release(self.teacher, saved["course_id"], "user", "student", True)

        module = saved["modules"][0]
        module_result = self.service.submit_assessment(
            self.student,
            saved["course_id"],
            module["module_id"],
            "module",
            _correct_answers(module["questions"]),
        )
        self.assertTrue(module_result["passed"])

        failed_final = self.service.submit_assessment(
            self.student,
            saved["course_id"],
            "",
            "final",
            {"ff1": "a", "ff2": "while"},
        )
        self.assertFalse(failed_final["passed"])
        self.assertIsNone(failed_final["certificate"])

        passed_final = self.service.submit_assessment(
            self.student,
            saved["course_id"],
            "",
            "final",
            _correct_answers(saved["final_assessment"]["questions"]),
        )
        self.assertTrue(passed_final["passed"])
        self.assertIsNotNone(passed_final["certificate"])
        self.assertEqual(passed_final["certificate"]["status"], "issued")


if __name__ == "__main__":
    unittest.main()
