import unittest
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base
from app.services.deliverable_detection_service import (
    DeliverableCandidate,
    DeliverableDetectionService,
    normalize_logical_name,
)


class DeliverableDetectionNormalizationTests(unittest.TestCase):
    def test_normalize_strips_version_suffix(self) -> None:
        self.assertEqual(normalize_logical_name("报价单_v2.xlsx"), "报价单")

    def test_normalize_strips_revision_suffix(self) -> None:
        self.assertEqual(normalize_logical_name("方案_修订版.docx"), "方案")

    def test_normalize_strips_timestamp_suffix(self) -> None:
        self.assertEqual(normalize_logical_name("报价单_20260323.xlsx"), "报价单")


class DeliverableDetectionSelectionTests(unittest.TestCase):
    def test_non_deliverable_script_is_filtered_out(self) -> None:
        self.assertFalse(
            DeliverableDetectionService.is_deliverable_candidate(
                file_path="outputs/build_report.py",
                mime_type="text/x-python",
            )
        )

    def test_pdf_export_is_treated_as_deliverable_candidate(self) -> None:
        self.assertTrue(
            DeliverableDetectionService.is_deliverable_candidate(
                file_path="outputs/实施方案.pdf",
                mime_type="application/pdf",
            )
        )

    def test_materially_modified_uploaded_template_can_be_promoted(self) -> None:
        self.assertTrue(
            DeliverableDetectionService.should_promote_reference_input(
                ref_type="upload",
                materially_modified=True,
                presented_as_result=True,
            )
        )

    def test_same_group_keeps_highest_confidence_candidate(self) -> None:
        session_id = uuid4()
        run_id = uuid4()
        candidates = [
            DeliverableCandidate(
                session_id=session_id,
                run_id=run_id,
                source_message_id=1,
                kind="xlsx",
                logical_name="报价单",
                file_path="outputs/报价单_v1.xlsx",
                file_name="报价单_v1.xlsx",
                confidence=0.51,
            ),
            DeliverableCandidate(
                session_id=session_id,
                run_id=run_id,
                source_message_id=1,
                kind="xlsx",
                logical_name="报价单",
                file_path="outputs/报价单_final.xlsx",
                file_name="报价单_final.xlsx",
                confidence=0.88,
            ),
        ]

        selected = DeliverableDetectionService.select_primary_candidates(candidates)

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].file_path, "outputs/报价单_final.xlsx")
        self.assertEqual(
            selected[0].detection_metadata_json["same_run_candidates"][0]["file_path"],
            "outputs/报价单_v1.xlsx",
        )


class DeliverableDetectionPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine)

    def setUp(self) -> None:
        self.db: Session = self.SessionLocal()
        self.service = DeliverableDetectionService()

    def tearDown(self) -> None:
        self.db.rollback()
        self.db.close()

    def test_persist_candidates_is_idempotent_for_same_run_and_path(self) -> None:
        session_id = uuid4()
        run_id = uuid4()
        candidate = DeliverableCandidate(
            session_id=session_id,
            run_id=run_id,
            source_message_id=1,
            kind="docx",
            logical_name="实施方案",
            file_path="outputs/实施方案_v1.docx",
            file_name="实施方案_v1.docx",
            confidence=0.93,
        )

        first = self.service.persist_candidates(self.db, [candidate])
        self.db.commit()
        second = self.service.persist_candidates(self.db, [candidate])
        self.db.commit()

        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(first[0].id, second[0].id)

    def test_new_run_gets_next_version_number(self) -> None:
        session_id = uuid4()
        first = DeliverableCandidate(
            session_id=session_id,
            run_id=uuid4(),
            source_message_id=1,
            kind="pptx",
            logical_name="汇报稿",
            file_path="outputs/汇报稿_v1.pptx",
            file_name="汇报稿_v1.pptx",
            confidence=0.80,
        )
        second = DeliverableCandidate(
            session_id=session_id,
            run_id=uuid4(),
            source_message_id=2,
            kind="pptx",
            logical_name="汇报稿",
            file_path="outputs/汇报稿_v2.pptx",
            file_name="汇报稿_v2.pptx",
            confidence=0.95,
        )

        first_version = self.service.persist_candidates(self.db, [first])[0]
        self.db.commit()
        second_version = self.service.persist_candidates(self.db, [second])[0]
        self.db.commit()

        self.assertEqual(first_version.version_no, 1)
        self.assertEqual(second_version.version_no, 2)


if __name__ == "__main__":
    unittest.main()
