from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_cli_adapters.config import UserConfig

from .ide_schema import IDE_DEFINITIONS
from .ide_schema import IdeDefinition

from .checks import ArtifactCheck
from .ide_diagnostics import IdeDiagnosticSnapshot
from .ide_extensions import check_ide_extension
from .ide_extensions import check_ide_extensions
from .ide_extensions import list_ide_extensions
from .ide_extensions import reconcile_ide_extensions
from .ide_installs import check_ide_install
from .ide_installs import check_ide_installs
from .ide_installs import reconcile_ide_install
from .ide_installs import reconcile_ide_installs
from .ide_settings import check_ide_setting
from .ide_settings import check_ide_settings
from .ide_settings import ide_settings_file
from .ide_settings import merge_ide_settings
from .ide_settings import read_ide_settings
from .ide_settings import reconcile_ide_settings
from .ide_settings import resolve_ide_settings
from .ide_settings import write_json_atomic
from .manifest import BaseManifest, IdeConfig


@dataclass(frozen=True)
class IdeMutationPlan:
    definition: IdeDefinition
    install: bool
    extensions: tuple[str, ...]
    settings: dict[str, object]
    settings_file: Path | None


# Compatibility exports for callers that imported IDE install, extension, and
# settings helpers from this module before the focused IDE modules existed.
__all__ = (
    "IDE_DEFINITIONS",
    "ArtifactCheck",
    "BaseManifest",
    "IdeConfig",
    "IdeDefinition",
    "IdeMutationPlan",
    "IdeDiagnosticSnapshot",
    "UserConfig",
    "check_ide_extension",
    "check_ide_extensions",
    "check_ide_install",
    "check_ide_installs",
    "check_ide_setting",
    "check_ide_settings",
    "effective_ide_config",
    "ide_preference_warning_checks",
    "ide_settings_file",
    "list_ide_extensions",
    "log_ide_preference_warnings",
    "log_project_ide_mutation_plan",
    "merge_ide_settings",
    "read_ide_settings",
    "reconcile_ide_extensions",
    "reconcile_ide_install",
    "reconcile_ide_installs",
    "reconcile_ide_settings",
    "resolve_ide_settings",
    "project_ide_mutation_plans",
    "write_json_atomic",
)


def effective_ide_config(project_ide: dict[str, IdeConfig], user_config: UserConfig) -> dict[str, IdeConfig]:
    if user_config.ide.enabled is False:
        return {}

    effective: dict[str, IdeConfig] = {}
    ide_names = sorted(set(project_ide) | set(user_config.ide.preferences))
    for ide_name in ide_names:
        user_preference = user_config.ide.preferences.get(ide_name)
        if user_preference is not None and user_preference.enabled is False:
            continue

        project_config = project_ide.get(ide_name, IdeConfig(install=False, extensions=(), settings={}))
        install = project_config.install
        if user_preference is not None and user_preference.install is not None:
            install = user_preference.install

        extensions = list(project_config.extensions)
        if user_preference is not None:
            for extension in user_preference.extra_extensions:
                if extension not in extensions:
                    extensions.append(extension)

        settings = {}
        if user_preference is not None:
            settings.update(user_preference.settings)
        settings.update(project_config.settings)

        if install or extensions or settings:
            effective[ide_name] = IdeConfig(
                install=install,
                extensions=tuple(extensions),
                settings=settings,
            )
    return effective


def project_ide_mutation_plans(
    project_manifest: BaseManifest,
    effective_manifest: BaseManifest,
) -> tuple[IdeMutationPlan, ...]:
    plans: list[IdeMutationPlan] = []
    for ide_name, project_config in sorted(project_manifest.ide.items()):
        effective_config = effective_manifest.ide.get(ide_name)
        if effective_config is None:
            continue
        if not (project_config.install or project_config.extensions or project_config.settings):
            continue
        resolved_settings = resolve_ide_settings(effective_manifest, effective_config.settings)
        plans.append(
            IdeMutationPlan(
                definition=IDE_DEFINITIONS[ide_name],
                install=effective_config.install,
                extensions=effective_config.extensions,
                settings=resolved_settings,
                settings_file=ide_settings_file(IDE_DEFINITIONS[ide_name]) if resolved_settings else None,
            )
        )
    return tuple(plans)


def log_project_ide_mutation_plan(
    ctx: base_cli.Context,
    project_manifest: BaseManifest,
    effective_manifest: BaseManifest,
) -> tuple[IdeMutationPlan, ...]:
    plans = project_ide_mutation_plans(project_manifest, effective_manifest)
    if not plans:
        return ()

    ctx.log.info("Project '%s' requests project-originated IDE mutations:", project_manifest.project_name)
    for plan in plans:
        if plan.install:
            ctx.log.info("  %s app: brew install --cask %s", plan.definition.label, plan.definition.cask)
        for extension in plan.extensions:
            ctx.log.info("  %s extension: %s", plan.definition.label, extension)
        if plan.settings_file is not None:
            ctx.log.info("  %s user settings file: %s", plan.definition.label, plan.settings_file)
            for key, value in plan.settings.items():
                ctx.log.info("    %s = %s", key, json.dumps(value, sort_keys=True))
    return plans


def ide_preference_warning_checks(manifest: BaseManifest, user_config: UserConfig) -> list[ArtifactCheck]:
    checks: list[ArtifactCheck] = []
    if user_config.ide.enabled is False and manifest.ide:
        checks.append(
            ArtifactCheck(
                name="user IDE config",
                ok=False,
                message="User config disables all IDE setup and checks for this machine.",
                fix="Remove or change 'ide.enabled: false' in ~/.base.d/config.yaml to re-enable IDE work.",
                status="warn",
                finding_id="BASE-P100",
            )
        )

    for ide_name, project_config in manifest.ide.items():
        user_preference = user_config.ide.preferences.get(ide_name)
        if user_preference is None:
            continue
        if user_preference.enabled is False:
            checks.append(
                ArtifactCheck(
                    name=f"user IDE config: {ide_name}",
                    ok=False,
                    message=f"User config disables {ide_name} IDE setup and checks for this machine.",
                    fix=f"Remove or change 'ide.{ide_name}.enabled: false' in ~/.base.d/config.yaml to re-enable it.",
                    status="warn",
                    finding_id="BASE-P101",
                )
            )
            continue
        conflicting_settings = sorted(set(project_config.settings) & set(user_preference.settings))
        for key in conflicting_settings:
            if project_config.settings[key] == user_preference.settings[key]:
                continue
            checks.append(
                ArtifactCheck(
                    name=f"user IDE setting: {ide_name}.{key}",
                    ok=False,
                    message=(
                        f"User config setting 'ide.{ide_name}.settings.{key}' is ignored because "
                        "the project manifest declares the same setting."
                    ),
                    fix=(
                        f"Remove 'ide.{ide_name}.settings.{key}' from ~/.base.d/config.yaml "
                        "or update the project manifest."
                    ),
                    status="warn",
                    finding_id="BASE-P102",
                )
            )
    return checks


def log_ide_preference_warnings(ctx: base_cli.Context, checks: list[ArtifactCheck]) -> None:
    for check in checks:
        ctx.log.warning(check.message)
        if check.fix:
            ctx.log.warning("Fix: %s", check.fix)
