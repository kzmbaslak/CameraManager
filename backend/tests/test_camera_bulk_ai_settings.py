"""Kamera toplu AI ayarlari endpoint regresyon testleri."""

import os
import unittest

from fastapi import HTTPException

os.environ.setdefault("CAMERA_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")

from src.domain.entities.camera import Camera, CameraStatus
from src.presentation.api.routes import cameras as camera_routes
from src.presentation.api.schemas.camera_schema import CameraBulkAiSettingsRequest


class FakeCameraUseCases:
    def __init__(self, cameras):
        self.cameras = cameras
        self.updated_ids = []

    def get_camera(self, camera_id):
        return self.cameras.get(camera_id)

    def update_camera(self, camera, plain_password=None):
        self.updated_ids.append(camera.id)
        return camera


class FakeStreamManager:
    def __init__(self):
        self.refreshed_ids = []

    async def ensure_running_state(self, camera_id):
        self.refreshed_ids.append(camera_id)


class Client:
    host = "10.0.0.20"


class Request:
    client = Client()


def camera(camera_id: int) -> Camera:
    return Camera(
        id=camera_id,
        name=f"Camera {camera_id}",
        host=f"10.0.0.{camera_id}",
        rtsp_port=554,
        rtsp_path="/stream",
        status=CameraStatus.ACTIVE,
    )


class CameraBulkAiSettingsTests(unittest.IsolatedAsyncioTestCase):
    async def test_bulk_ai_settings_updates_all_cameras_and_refreshes_streams(self):
        use_cases = FakeCameraUseCases({1: camera(1), 2: camera(2)})
        stream_manager = FakeStreamManager()

        result = await camera_routes.bulk_update_camera_ai_settings(
            CameraBulkAiSettingsRequest(
                camera_ids=[1, 2, 2],
                ai_confidence_threshold=0.65,
                ai_iou_threshold=0.5,
                ai_alarm_cooldown_seconds=120,
                ai_frame_stride=3,
                ai_inference_width=640,
            ),
            Request(),
            use_cases,
            stream_manager,
            {"sub": "admin"},
        )

        self.assertEqual([item.id for item in result], [1, 2])
        self.assertEqual(use_cases.updated_ids, [1, 2])
        self.assertEqual(stream_manager.refreshed_ids, [1, 2])
        self.assertEqual(use_cases.cameras[1].ai_confidence_threshold, 0.65)
        self.assertEqual(use_cases.cameras[2].ai_frame_stride, 3)

    async def test_bulk_ai_settings_rejects_missing_camera_without_partial_update(self):
        use_cases = FakeCameraUseCases({1: camera(1)})
        stream_manager = FakeStreamManager()

        with self.assertRaises(HTTPException) as context:
            await camera_routes.bulk_update_camera_ai_settings(
                CameraBulkAiSettingsRequest(
                    camera_ids=[1, 99],
                    ai_confidence_threshold=0.35,
                    ai_iou_threshold=0.45,
                    ai_alarm_cooldown_seconds=30,
                    ai_frame_stride=1,
                    ai_inference_width=768,
                ),
                Request(),
                use_cases,
                stream_manager,
                {"sub": "admin"},
            )

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(use_cases.updated_ids, [])
        self.assertEqual(stream_manager.refreshed_ids, [])


if __name__ == "__main__":
    unittest.main()
