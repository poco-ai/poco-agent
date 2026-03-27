import unittest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base
from app.models.deliverable import Deliverable
from app.models.deliverable_version import DeliverableVersion
from app.models.tool_execution import ToolExecution
from app.repositories.deliverable_repository import DeliverableRepository
from app.repositories.deliverable_version_repository import (
    DeliverableVersionRepository,
)
from app.schemas.deliverable import DeliverableResponse, DeliverableVersionResponse
from app.services.deliverable_service import DeliverableService


class _SQLiteHarness(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine)

    def setUp(self) -> None:
        self.db: Session = self.SessionLocal()

    def tearDown(self) -> None:
        self.db.rollback()
        self.db.close()


class DeliverableModelTests(_SQLiteHarness):
    def test_create_deliverable_with_phase1_fields(self) -> None:
        deliverable = Deliverable(
            session_id=uuid4(),
            kind="xlsx",
            logical_name="报价单",
            status="active",
        )

        self.db.add(deliverable)
        self.db.commit()

        self.assertIsNotNone(deliverable.id)
        self.assertEqual(deliverable.kind, "xlsx")
        self.assertEqual(deliverable.logical_name, "报价单")
        self.assertEqual(deliverable.status, "active")
        self.assertIsNone(deliverable.latest_version_id)

    def test_deliverable_natural_key_is_unique(self) -> None:
        session_id = uuid4()
        self.db.add(
            Deliverable(
                session_id=session_id,
                kind="docx",
                logical_name="实施方案",
                status="active",
            )
        )
        self.db.commit()

        self.db.add(
            Deliverable(
                session_id=session_id,
                kind="docx",
                logical_name="实施方案",
                status="active",
            )
        )

        with self.assertRaises(IntegrityError):
            self.db.commit()


class DeliverableVersionModelTests(_SQLiteHarness):
    def test_create_version_with_phase1_fields(self) -> None:
        deliverable = Deliverable(
            session_id=uuid4(),
            kind="xlsx",
            logical_name="报价单",
            status="active",
        )
        self.db.add(deliverable)
        self.db.commit()

        version = DeliverableVersion(
            session_id=deliverable.session_id,
            run_id=uuid4(),
            deliverable_id=deliverable.id,
            source_message_id=None,
            version_no=1,
            file_path="outputs/报价单_v1.xlsx",
            file_name="报价单_v1.xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            input_refs_json={"message_refs": [1]},
            related_tool_execution_ids_json={"strong": [], "moderate": []},
            detection_metadata_json={"confidence": 0.9},
        )

        self.db.add(version)
        self.db.commit()

        self.assertIsNotNone(version.id)
        self.assertEqual(version.version_no, 1)
        self.assertEqual(version.file_path, "outputs/报价单_v1.xlsx")

    def test_version_natural_key_is_unique(self) -> None:
        deliverable = Deliverable(
            session_id=uuid4(),
            kind="pptx",
            logical_name="汇报稿",
            status="active",
        )
        self.db.add(deliverable)
        self.db.commit()

        run_id = uuid4()
        self.db.add(
            DeliverableVersion(
                session_id=deliverable.session_id,
                run_id=run_id,
                deliverable_id=deliverable.id,
                version_no=1,
                file_path="outputs/汇报稿_v1.pptx",
            )
        )
        self.db.commit()

        self.db.add(
            DeliverableVersion(
                session_id=deliverable.session_id,
                run_id=run_id,
                deliverable_id=deliverable.id,
                version_no=2,
                file_path="outputs/汇报稿_v1.pptx",
            )
        )

        with self.assertRaises(IntegrityError):
            self.db.commit()


class DeliverableRepositoryTests(_SQLiteHarness):
    def test_get_or_create_uses_session_kind_logical_name(self) -> None:
        session_id = uuid4()

        created, created_flag = DeliverableRepository.get_or_create(
            self.db,
            session_id=session_id,
            kind="docx",
            logical_name="实施方案",
        )
        self.db.commit()

        existing, existing_flag = DeliverableRepository.get_or_create(
            self.db,
            session_id=session_id,
            kind="docx",
            logical_name="实施方案",
        )

        self.assertTrue(created_flag)
        self.assertFalse(existing_flag)
        self.assertEqual(created.id, existing.id)

    def test_list_by_session_returns_created_deliverables(self) -> None:
        session_id = uuid4()
        other_session_id = uuid4()

        self.db.add_all(
            [
                Deliverable(
                    session_id=session_id,
                    kind="xlsx",
                    logical_name="报价单",
                    status="active",
                ),
                Deliverable(
                    session_id=other_session_id,
                    kind="docx",
                    logical_name="方案",
                    status="active",
                ),
            ]
        )
        self.db.commit()

        items = DeliverableRepository.list_by_session(self.db, session_id)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].logical_name, "报价单")


class DeliverableVersionRepositoryTests(_SQLiteHarness):
    def test_get_by_session_run_path_returns_matching_version(self) -> None:
        deliverable = Deliverable(
            session_id=uuid4(),
            kind="xlsx",
            logical_name="报价单",
            status="active",
        )
        self.db.add(deliverable)
        self.db.commit()

        run_id = uuid4()
        version = DeliverableVersionRepository.create(
            self.db,
            session_id=deliverable.session_id,
            run_id=run_id,
            deliverable_id=deliverable.id,
            version_no=1,
            file_path="outputs/报价单_v1.xlsx",
            file_name="报价单_v1.xlsx",
        )
        self.db.commit()

        found = DeliverableVersionRepository.get_by_session_run_path(
            self.db,
            session_id=deliverable.session_id,
            run_id=run_id,
            file_path="outputs/报价单_v1.xlsx",
        )

        self.assertIsNotNone(found)
        self.assertEqual(found.id, version.id)

    def test_list_by_deliverable_is_ordered_by_version_number(self) -> None:
        deliverable = Deliverable(
            session_id=uuid4(),
            kind="docx",
            logical_name="实施方案",
            status="active",
        )
        self.db.add(deliverable)
        self.db.commit()

        self.db.add_all(
            [
                DeliverableVersion(
                    session_id=deliverable.session_id,
                    run_id=uuid4(),
                    deliverable_id=deliverable.id,
                    version_no=2,
                    file_path="outputs/实施方案_v2.docx",
                ),
                DeliverableVersion(
                    session_id=deliverable.session_id,
                    run_id=uuid4(),
                    deliverable_id=deliverable.id,
                    version_no=1,
                    file_path="outputs/实施方案_v1.docx",
                ),
            ]
        )
        self.db.commit()

        items = DeliverableVersionRepository.list_by_deliverable(
            self.db, deliverable.id
        )

        self.assertEqual([item.version_no for item in items], [1, 2])


class DeliverableSchemaTests(unittest.TestCase):
    def test_deliverable_response_reads_model_attributes(self) -> None:
        deliverable = Deliverable(
            id=uuid4(),
            session_id=uuid4(),
            kind="xlsx",
            logical_name="报价单",
            latest_version_id=uuid4(),
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        payload = DeliverableResponse.model_validate(deliverable)

        self.assertEqual(payload.id, deliverable.id)
        self.assertEqual(payload.logical_name, "报价单")

    def test_deliverable_version_response_reads_model_attributes(self) -> None:
        version = DeliverableVersion(
            id=uuid4(),
            session_id=uuid4(),
            run_id=uuid4(),
            deliverable_id=uuid4(),
            version_no=3,
            file_path="outputs/报价单_v3.xlsx",
            file_name="报价单_v3.xlsx",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        payload = DeliverableVersionResponse.model_validate(version)

        self.assertEqual(payload.id, version.id)
        self.assertEqual(payload.version_no, 3)


class DeliverableServiceTests(_SQLiteHarness):
    def setUp(self) -> None:
        super().setUp()
        self.service = DeliverableService()

    def test_list_by_session_returns_response_models(self) -> None:
        session_id = uuid4()
        self.db.add(
            Deliverable(
                session_id=session_id,
                kind="docx",
                logical_name="实施方案",
                status="active",
            )
        )
        self.db.commit()

        items = self.service.list_by_session(self.db, session_id=session_id)

        self.assertEqual(len(items), 1)
        self.assertIsInstance(items[0], DeliverableResponse)
        self.assertEqual(items[0].logical_name, "实施方案")

    def test_get_version_tool_executions_returns_linked_items(self) -> None:
        session_id = uuid4()
        deliverable = Deliverable(
            session_id=session_id,
            kind="xlsx",
            logical_name="报价单",
            status="active",
        )
        self.db.add(deliverable)
        self.db.flush()

        execution = ToolExecution(
            id=uuid4(),
            session_id=session_id,
            message_id=1,
            tool_use_id="tool-1",
            tool_name="Write",
            tool_input={"file_path": "outputs/报价单_v1.xlsx"},
            tool_output={"content": "ok"},
            is_error=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(execution)
        self.db.flush()

        version = DeliverableVersion(
            session_id=session_id,
            run_id=uuid4(),
            deliverable_id=deliverable.id,
            version_no=1,
            file_path="outputs/报价单_v1.xlsx",
            related_tool_execution_ids_json={
                "strong": [str(execution.id)],
                "moderate": [],
            },
        )
        self.db.add(version)
        self.db.commit()

        items = self.service.get_version_tool_executions(
            self.db,
            session_id=session_id,
            version_id=version.id,
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, execution.id)

    def test_list_versions_by_deliverable_returns_all_versions(self) -> None:
        session_id = uuid4()
        deliverable = Deliverable(
            session_id=session_id,
            kind="docx",
            logical_name="实施方案",
            status="active",
        )
        self.db.add(deliverable)
        self.db.flush()

        self.db.add_all(
            [
                DeliverableVersion(
                    session_id=session_id,
                    run_id=uuid4(),
                    deliverable_id=deliverable.id,
                    version_no=1,
                    file_path="outputs/实施方案_v1.docx",
                ),
                DeliverableVersion(
                    session_id=session_id,
                    run_id=uuid4(),
                    deliverable_id=deliverable.id,
                    version_no=2,
                    file_path="outputs/实施方案_v2.docx",
                ),
            ]
        )
        self.db.commit()

        items = self.service.list_versions_by_deliverable(
            self.db,
            session_id=session_id,
            deliverable_id=deliverable.id,
        )

        self.assertEqual([item.version_no for item in items], [1, 2])


if __name__ == "__main__":
    unittest.main()
