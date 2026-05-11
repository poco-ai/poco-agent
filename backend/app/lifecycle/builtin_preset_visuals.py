import hashlib
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.preset_visual import PresetVisual
from app.repositories.preset_visual_repository import PresetVisualRepository
from app.services.storage_service import S3StorageService

def _resolve_preset_visual_assets_root(module_file: Path | None = None) -> Path:
    current_file = module_file or Path(__file__).resolve()
    candidates = [
        # Source checkout layout: <repo>/backend/app/lifecycle/<file>.
        current_file.parents[3] / "assets" / "icons" / "presets",
        # Container layout: /app/app/lifecycle/<file> with assets copied to /app/assets.
        current_file.parents[2] / "assets" / "icons" / "presets",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


_PRESET_VISUAL_ASSETS_ROOT = _resolve_preset_visual_assets_root()
_LIFECYCLE_MANAGER = "lifecycle"


@dataclass(frozen=True, slots=True)
class BuiltinPresetVisualAsset:
    key: str
    name: str
    source: str
    storage_key: str
    hash: str
    version: str
    file_path: Path


class BuiltinPresetVisualBootstrapService:
    @classmethod
    def bootstrap_builtin_preset_visuals(cls, db: Session) -> None:
        storage_service = cls._build_storage_service()
        assets = cls._discover_assets()
        cls._cleanup_removed_assets(
            db,
            declared_keys={asset.key for asset in assets},
            storage_service=storage_service,
        )

        for asset in assets:
            existing = PresetVisualRepository.get_by_key(db, asset.key)
            cls._sync_asset(storage_service, asset, existing)
            cls._ensure_preset_visual(db, asset, existing)

    @classmethod
    def _discover_assets(cls) -> list[BuiltinPresetVisualAsset]:
        assets: list[BuiltinPresetVisualAsset] = []
        for file_path in sorted(_PRESET_VISUAL_ASSETS_ROOT.glob("*.svg")):
            if file_path.name == ".DS_Store":
                continue

            content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
            key = file_path.stem
            assets.append(
                BuiltinPresetVisualAsset(
                    key=key,
                    name=key.replace("-", " ").title(),
                    source=f"icons/presets/{file_path.name}",
                    storage_key=f"builtin/preset-visuals/{key}/asset.svg",
                    hash=content_hash,
                    version=content_hash,
                    file_path=file_path,
                )
            )
        return assets

    @classmethod
    def _cleanup_removed_assets(
        cls,
        db: Session,
        *,
        declared_keys: set[str],
        storage_service: S3StorageService | None,
    ) -> None:
        existing_visuals = PresetVisualRepository.list_managed(
            db,
            managed_by=_LIFECYCLE_MANAGER,
        )
        for visual in existing_visuals:
            if visual.key in declared_keys:
                continue
            visual.is_active = False
            if storage_service is not None:
                storage_service.delete_prefix(prefix=cls._storage_prefix(visual.key))
            db.flush()

    @classmethod
    def _sync_asset(
        cls,
        storage_service: S3StorageService | None,
        asset: BuiltinPresetVisualAsset,
        existing: PresetVisual | None,
    ) -> None:
        if storage_service is None:
            return

        existing_version = existing.version if existing is not None else None
        needs_upload = existing_version != asset.version or not storage_service.exists(
            asset.storage_key
        )
        if not needs_upload:
            return

        storage_service.upload_file(
            file_path=str(asset.file_path),
            key=asset.storage_key,
            content_type="image/svg+xml",
        )

    @classmethod
    def _ensure_preset_visual(
        cls,
        db: Session,
        asset: BuiltinPresetVisualAsset,
        existing: PresetVisual | None,
    ) -> PresetVisual:
        if existing is None:
            visual = PresetVisual(
                key=asset.key,
                name=asset.name,
                storage_key=asset.storage_key,
                hash=asset.hash,
                version=asset.version,
                source=asset.source,
                managed_by=_LIFECYCLE_MANAGER,
                is_active=True,
            )
            PresetVisualRepository.create(db, visual)
            db.flush()
            return visual

        existing.name = asset.name
        existing.storage_key = asset.storage_key
        existing.hash = asset.hash
        existing.version = asset.version
        existing.source = asset.source
        existing.managed_by = _LIFECYCLE_MANAGER
        existing.is_active = True
        db.flush()
        return existing

    @staticmethod
    def _build_storage_service() -> S3StorageService | None:
        try:
            return S3StorageService()
        except Exception:
            return None

    @staticmethod
    def _storage_prefix(key: str) -> str:
        return f"builtin/preset-visuals/{key}"
