export interface PolicyControlledCapability {
  scope: string;
  default_enabled: boolean;
  force_enabled: boolean;
}

export interface CapabilityInstallRecord {
  id: number;
  enabled: boolean;
}

export interface EffectiveInstallState {
  autoEnabled: boolean;
  hasInstall: boolean;
  isInstalled: boolean;
  isEnabled: boolean;
}

export function getEffectiveInstallState(
  capability: PolicyControlledCapability,
  install?: CapabilityInstallRecord | null,
): EffectiveInstallState {
  const hasInstall = Boolean(install);
  const autoEnabled =
    !hasInstall &&
    capability.scope === "system" &&
    (capability.default_enabled || capability.force_enabled);

  return {
    autoEnabled,
    hasInstall,
    isInstalled: hasInstall || autoEnabled,
    isEnabled: install?.enabled ?? autoEnabled,
  };
}
