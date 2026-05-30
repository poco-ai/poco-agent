export interface PersistentRuntimeSummary {
  id: string;
  runtimeKey: string;
  ownerType: string;
  ownerId: string;
  agentIdentityId?: string | null;
  assignmentId?: string | null;
  sessionId?: string | null;
  containerId?: string | null;
  lifecycleState: string;
  autoResume: boolean;
  idleTimeoutSeconds: number;
  warmRetentionSeconds: number;
  keepaliveUntil?: string | null;
  lastActivityAt?: string | null;
  lastStartedAt?: string | null;
  lastStoppedAt?: string | null;
  lastStopReason?: string | null;
  workerId?: string | null;
  browserEnabled: boolean;
  filesystemFingerprint?: string | null;
}
