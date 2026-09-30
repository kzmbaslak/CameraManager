"""Kamera insan yogunlugu analitigi repository testleri."""

import unittest
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.database.database import Base
from src.infrastructure.database.repositories.person_analytics_repository import SqlAlchemyPersonAnalyticsRepository
from src.infrastructure.time_utils import utc_now


class PersonAnalyticsRepositoryTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
        self.repo = SqlAlchemyPersonAnalyticsRepository(self.session)

    def tearDown(self):
        self.session.close()

    def test_record_detection_accumulates_same_hour_bucket(self):
        detected_at = utc_now().replace(minute=12, second=0, microsecond=0)

        first = self.repo.record_detection(7, detected_at, person_count=2, max_confidence=0.74)
        second = self.repo.record_detection(7, detected_at + timedelta(minutes=18), person_count=4, max_confidence=0.91)

        self.assertEqual(first.id, second.id)
        self.assertEqual(second.detection_samples, 2)
        self.assertEqual(second.total_person_count, 6)
        self.assertEqual(second.max_person_count, 4)
        self.assertEqual(second.max_confidence, 0.91)
        self.assertEqual(second.hour_start.minute, 0)

    def test_list_hourly_filters_camera_and_range(self):
        base = utc_now().replace(minute=0, second=0, microsecond=0)
        self.repo.record_detection(1, base - timedelta(hours=2), person_count=1, max_confidence=0.5)
        self.repo.record_detection(1, base - timedelta(hours=1), person_count=3, max_confidence=0.8)
        self.repo.record_detection(2, base - timedelta(hours=1), person_count=5, max_confidence=0.9)

        rows = self.repo.list_hourly(1, base - timedelta(hours=1), base, limit=24)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].camera_id, 1)
        self.assertEqual(rows[0].total_person_count, 3)


if __name__ == "__main__":
    unittest.main()
