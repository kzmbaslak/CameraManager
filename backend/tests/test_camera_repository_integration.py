"""Kamera repository SQLite entegrasyon testleri."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.domain.entities.camera import Camera, CameraStatus
from src.infrastructure.database.database import Base
from src.infrastructure.database.repositories.camera_repository import SqlAlchemyCameraRepository


class CameraRepositoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
        self.repo = SqlAlchemyCameraRepository(self.session)

    def tearDown(self):
        self.session.close()

    def test_add_get_and_update_preserve_ai_settings(self):
        camera = self.repo.add(Camera(
            id=None,
            name="Gate 1",
            host="10.0.0.11",
            rtsp_path="/main",
            status=CameraStatus.ACTIVE,
            ai_detection_enabled=True,
            ai_confidence_threshold=0.62,
            ai_iou_threshold=0.41,
            ai_alarm_cooldown_seconds=45,
            ai_frame_stride=2,
            ai_inference_width=512,
        ))

        loaded = self.repo.get_by_id(camera.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Gate 1")
        self.assertEqual(loaded.ai_confidence_threshold, 0.62)
        self.assertEqual(loaded.ai_frame_stride, 2)

        loaded.ai_confidence_threshold = 0.78
        loaded.ai_frame_stride = 3
        updated = self.repo.update(loaded)

        self.assertEqual(updated.ai_confidence_threshold, 0.78)
        self.assertEqual(updated.ai_frame_stride, 3)

    def test_paginated_search_status_and_ai_filters(self):
        self.repo.add(Camera(
            id=None,
            name="North Gate",
            host="10.0.0.21",
            rtsp_path="/main",
            status=CameraStatus.ACTIVE,
            ai_detection_enabled=True,
        ))
        self.repo.add(Camera(
            id=None,
            name="South Yard",
            host="10.0.0.22",
            rtsp_path="/sub",
            status=CameraStatus.INACTIVE,
            ai_detection_enabled=False,
        ))

        items, total = self.repo.list_paginated(
            page=1,
            page_size=10,
            search="gate",
            status="active",
            ai_filter="enabled",
            sort="name_asc",
        )

        self.assertEqual(total, 1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "North Gate")


if __name__ == "__main__":
    unittest.main()
