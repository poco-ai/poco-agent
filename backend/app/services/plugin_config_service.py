from sqlalchemy.orm import Session

from app.repositories.plugin_repository import PluginRepository
from app.repositories.user_plugin_install_repository import UserPluginInstallRepository


class PluginConfigService:
    """Service for building plugin configs used by the executor manager stager."""

    def resolve_user_plugin_files(
        self,
        db: Session,
        user_id: str,
        plugin_ids: list[int],
    ) -> dict:
        """Resolve plugins for a user given selected plugin ids.

        Returns a dict compatible with executor_manager PluginStager:
        {plugin_name: {"enabled": True, "entry": {...}, "manifest": {...}}, ...}
        """
        installs = UserPluginInstallRepository.list_by_user(db, user_id)
        installs_by_plugin_id = {install.plugin_id: install for install in installs}

        ordered_ids: list[int] = []
        seen: set[int] = set()
        for pid in plugin_ids:
            if pid in seen:
                continue
            seen.add(pid)
            ordered_ids.append(pid)

        selected: dict[str, tuple[str, dict, dict | None, str | None, str | None]] = {}
        for plugin_id in ordered_ids:
            plugin = PluginRepository.get_by_id(db, plugin_id)
            if not plugin or not isinstance(plugin.entry, dict):
                continue
            install = installs_by_plugin_id.get(plugin_id)
            is_enabled = bool(plugin.force_enabled) or bool(
                install.enabled if install is not None else plugin.default_enabled
            )
            if not is_enabled:
                continue

            existing = selected.get(plugin.name)
            if existing is None:
                selected[plugin.name] = (
                    plugin.scope,
                    plugin.entry,
                    plugin.manifest,
                    plugin.version,
                    plugin.description,
                )
                continue
            existing_scope, *_ = existing
            if existing_scope != "user" and plugin.scope == "user":
                selected[plugin.name] = (
                    plugin.scope,
                    plugin.entry,
                    plugin.manifest,
                    plugin.version,
                    plugin.description,
                )

        requested_ids = set(ordered_ids)
        for plugin in PluginRepository.list_visible(db, user_id=user_id):
            if plugin.scope != "system" or not isinstance(plugin.entry, dict):
                continue
            if plugin.id in requested_ids:
                continue
            install = installs_by_plugin_id.get(plugin.id)
            is_enabled = bool(plugin.force_enabled) or bool(
                install.enabled if install is not None else plugin.default_enabled
            )
            if not is_enabled:
                continue
            selected.setdefault(
                plugin.name,
                (
                    plugin.scope,
                    plugin.entry,
                    plugin.manifest,
                    plugin.version,
                    plugin.description,
                ),
            )

        return {
            name: {
                "enabled": True,
                "entry": entry,
                "manifest": manifest,
                "version": version,
                "description": description,
            }
            for name, (_, entry, manifest, version, description) in selected.items()
        }
