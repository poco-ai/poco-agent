import tempfile
import unittest
from types import SimpleNamespace

from app.core.settings import Settings
from app.services.container_pool import ContainerPool
from app.services.local_mount_service import LocalMountService


class LocalMountServicePhaseOneTests(unittest.TestCase):
    def test_build_runtime_config_omits_cloud_runtime_metadata(self) -> None:
        service = LocalMountService(Settings())
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_config, resolution = service.build_runtime_config(
                {
                    "filesystem_mode": "local_mount",
                    "local_mounts": [
                        {
                            "id": "docs",
                            "name": "Docs",
                            "host_path": temp_dir,
                            "access_mode": "ro",
                        }
                    ],
                }
            )

        self.assertEqual(runtime_config["filesystem_mode"], "local_mount")
        self.assertEqual(len(runtime_config["resolved_local_mounts"]), 1)
        self.assertEqual(len(resolution.resolved_mounts), 1)
        self.assertIn("mount_fingerprint", runtime_config)
        self.assertNotIn("deployment_mode", runtime_config)
        self.assertNotIn("mount_provider_type", runtime_config)

    def test_container_reuse_mismatch_ignores_deployment_mode(self) -> None:
        pool = ContainerPool.__new__(ContainerPool)
        container = SimpleNamespace(
            labels={
                "filesystem_mode": "local_mount",
                "deployment_mode": "cloud",
                "mount_fingerprint": "same-fingerprint",
            }
        )

        reasons = pool._get_reuse_mismatch_reasons(
            container=container,
            browser_enabled=False,
            filesystem_mode="local_mount",
            mount_fingerprint="same-fingerprint",
        )

        self.assertEqual(reasons, [])

    def test_settings_drop_cloud_mount_bridge_fields(self) -> None:
        self.assertNotIn("deployment_mode", Settings.model_fields)
        self.assertNotIn("local_mount_bridge_root", Settings.model_fields)
        self.assertNotIn("local_mount_helper_status", Settings.model_fields)
        self.assertNotIn("local_mount_helper_message", Settings.model_fields)


if __name__ == "__main__":
    unittest.main()
