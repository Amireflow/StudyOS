import type {
  AiActionProposal,
  AiContextScope,
  AiConversation,
  AiMemory,
  AiMemoryUpdate,
  AiMessage,
  AiMessageRole,
  AiProviderCatalogItem,
  AiProviderConfig,
  AiProviderKind,
  AiProviderModel,
  AiReport,
  AiReportType,
  AiToolRiskLevel,
  AiToolSpec,
  ProposalStatus,
} from '../types/domain';
import { apiRequest } from './api-client';

interface ApiAiToolSpec {
  name: string;
  access: 'read' | 'proposal';
  risk_level?: AiToolRiskLevel;
  label: string;
  description: string;
  requires_confirmation: boolean;
  parameter_keys: string[];
}

interface ApiAiConversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ApiAiMessage {
  id: string;
  user_id: string;
  conversation_id: string;
  role: AiMessageRole;
  content: string;
  metadata: {
    provider?: string;
    model?: string;
    is_estimate?: boolean;
    missing_data?: string[];
    included_scopes?: string[];
    proposal_ids?: string[];
    rejected_proposals_count?: number;
    auto_executed_count?: number;
  };
  created_at: string;
}

interface ApiAiProposal {
  id: string;
  user_id: string;
  conversation_id: string;
  action_type: string;
  title: string;
  explanation: string;
  payload: Record<string, unknown>;
  status: ProposalStatus;
  expires_at: string | null;
  execution_result: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  resolved_at: string | null;
}

interface ApiAiConversationDetail {
  conversation: ApiAiConversation;
  messages: ApiAiMessage[];
  proposals: ApiAiProposal[];
}

interface ApiAiTurn {
  user_message: ApiAiMessage;
  assistant_message: ApiAiMessage;
  proposals: ApiAiProposal[];
  auto_executed_count?: number;
}

interface ApiAiMemory {
  user_id: string;
  academic_context: Record<string, unknown>;
  availability_preferences: Record<string, unknown>;
  learning_preferences: Record<string, unknown>;
  constraints: string[];
  long_term_goals: string[];
  recent_decisions: Array<{ action_type?: string; summary?: string; decided_at?: string }>;
  execution_history: Array<{
    proposal_id?: string;
    action_type?: string;
    summary?: string;
    entity?: string | null;
    executed_at?: string;
  }>;
  weekly_study_hours: number | null;
  default_session_minutes: number;
  auto_execute_simple_actions: boolean;
  updated_at: string;
}

interface ApiAiReport {
  id: string;
  user_id: string;
  type: AiReportType;
  period_start: string;
  period_end: string;
  content: string;
  metadata: {
    is_estimate?: boolean;
    missing_data?: string[];
    stats?: Record<string, unknown>;
  };
  created_at: string;
}

function mapTool(dto: ApiAiToolSpec): AiToolSpec {
  return {
    name: dto.name,
    access: dto.access,
    riskLevel: dto.risk_level,
    label: dto.label,
    description: dto.description,
    requiresConfirmation: dto.requires_confirmation,
    parameterKeys: dto.parameter_keys,
  };
}

function mapMemory(dto: ApiAiMemory): AiMemory {
  return {
    userId: dto.user_id,
    academicContext: dto.academic_context ?? {},
    availabilityPreferences: dto.availability_preferences ?? {},
    learningPreferences: dto.learning_preferences ?? {},
    constraints: Array.isArray(dto.constraints) ? dto.constraints : [],
    longTermGoals: Array.isArray(dto.long_term_goals) ? dto.long_term_goals : [],
    recentDecisions: Array.isArray(dto.recent_decisions) ? dto.recent_decisions : [],
    executionHistory: Array.isArray(dto.execution_history) ? dto.execution_history : [],
    weeklyStudyHours: dto.weekly_study_hours ?? null,
    defaultSessionMinutes: dto.default_session_minutes ?? 60,
    autoExecuteSimpleActions: Boolean(dto.auto_execute_simple_actions),
    updatedAt: dto.updated_at,
  };
}

function mapConversation(dto: ApiAiConversation): AiConversation {
  return {
    id: dto.id,
    userId: dto.user_id,
    title: dto.title,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapMessage(dto: ApiAiMessage): AiMessage {
  return {
    id: dto.id,
    userId: dto.user_id,
    conversationId: dto.conversation_id,
    role: dto.role,
    content: dto.content,
    metadata: {
      provider: dto.metadata?.provider,
      model: dto.metadata?.model,
      isEstimate: dto.metadata?.is_estimate,
      missingData: dto.metadata?.missing_data,
      includedScopes: dto.metadata?.included_scopes,
      proposalIds: dto.metadata?.proposal_ids,
      rejectedProposalsCount: dto.metadata?.rejected_proposals_count,
      autoExecutedCount: dto.metadata?.auto_executed_count,
    },
    createdAt: dto.created_at,
  };
}

function mapProposal(dto: ApiAiProposal): AiActionProposal {
  return {
    id: dto.id,
    userId: dto.user_id,
    conversationId: dto.conversation_id,
    actionType: dto.action_type,
    title: dto.title,
    explanation: dto.explanation,
    payload: dto.payload ?? {},
    status: dto.status,
    expiresAt: dto.expires_at,
    executionResult: dto.execution_result,
    errorMessage: dto.error_message,
    createdAt: dto.created_at,
    resolvedAt: dto.resolved_at,
  };
}

function mapReport(dto: ApiAiReport): AiReport {
  return {
    id: dto.id,
    userId: dto.user_id,
    type: dto.type,
    periodStart: dto.period_start,
    periodEnd: dto.period_end,
    content: dto.content,
    metadata: {
      isEstimate: dto.metadata?.is_estimate,
      missingData: dto.metadata?.missing_data,
      stats: dto.metadata?.stats,
    },
    createdAt: dto.created_at,
  };
}

export async function fetchAiToolsApi(accessToken: string): Promise<AiToolSpec[]> {
  const dtos = await apiRequest<ApiAiToolSpec[]>('/ai/tools', { accessToken });
  return dtos.map(mapTool);
}

export async function fetchConversationsApi(accessToken: string): Promise<AiConversation[]> {
  const dtos = await apiRequest<ApiAiConversation[]>('/ai/conversations', { accessToken });
  return dtos.map(mapConversation);
}

export async function createConversationApi(
  accessToken: string,
  title?: string,
): Promise<AiConversation> {
  const dto = await apiRequest<ApiAiConversation>('/ai/conversations', {
    method: 'POST',
    accessToken,
    body: { title: title?.trim() || null },
  });
  return mapConversation(dto);
}

export async function fetchConversationDetailApi(
  accessToken: string,
  conversationId: string,
): Promise<{
  conversation: AiConversation;
  messages: AiMessage[];
  proposals: AiActionProposal[];
}> {
  const dto = await apiRequest<ApiAiConversationDetail>(
    `/ai/conversations/${conversationId}`,
    { accessToken },
  );
  return {
    conversation: mapConversation(dto.conversation),
    messages: dto.messages.map(mapMessage),
    proposals: dto.proposals.map(mapProposal),
  };
}

export async function deleteConversationApi(
  accessToken: string,
  conversationId: string,
): Promise<void> {
  await apiRequest<void>(`/ai/conversations/${conversationId}`, {
    method: 'DELETE',
    accessToken,
  });
}

export async function fetchAiMemoryApi(accessToken: string): Promise<AiMemory> {
  const dto = await apiRequest<ApiAiMemory>('/ai/memory', { accessToken });
  return mapMemory(dto);
}

export async function updateAiMemoryApi(
  accessToken: string,
  patch: AiMemoryUpdate,
): Promise<AiMemory> {
  const body: Record<string, unknown> = {};
  if (patch.academicContext !== undefined) body.academic_context = patch.academicContext;
  if (patch.availabilityPreferences !== undefined) {
    body.availability_preferences = patch.availabilityPreferences;
  }
  if (patch.learningPreferences !== undefined) {
    body.learning_preferences = patch.learningPreferences;
  }
  if (patch.constraints !== undefined) body.constraints = patch.constraints;
  if (patch.longTermGoals !== undefined) body.long_term_goals = patch.longTermGoals;
  if (patch.weeklyStudyHours !== undefined) body.weekly_study_hours = patch.weeklyStudyHours;
  if (patch.defaultSessionMinutes !== undefined) {
    body.default_session_minutes = patch.defaultSessionMinutes;
  }
  if (patch.autoExecuteSimpleActions !== undefined) {
    body.auto_execute_simple_actions = patch.autoExecuteSimpleActions;
  }
  const dto = await apiRequest<ApiAiMemory>('/ai/memory', {
    method: 'PATCH',
    accessToken,
    body,
  });
  return mapMemory(dto);
}

export async function sendAiMessageApi(
  accessToken: string,
  conversationId: string,
  content: string,
  contextScopes?: AiContextScope[],
  options?: { idempotencyKey?: string; autoExecuteSimple?: boolean },
): Promise<{
  userMessage: AiMessage;
  assistantMessage: AiMessage;
  proposals: AiActionProposal[];
  autoExecutedCount: number;
}> {
  const headers: Record<string, string> = {};
  if (options?.idempotencyKey) {
    headers['Idempotency-Key'] = options.idempotencyKey;
  }
  const dto = await apiRequest<ApiAiTurn>(`/ai/conversations/${conversationId}/messages`, {
    method: 'POST',
    accessToken,
    headers,
    body: {
      content: content.trim(),
      context_scopes: contextScopes ?? ['auto'],
      idempotency_key: options?.idempotencyKey ?? null,
      auto_execute_simple: options?.autoExecuteSimple ?? null,
    },
  });
  return {
    userMessage: mapMessage(dto.user_message),
    assistantMessage: mapMessage(dto.assistant_message),
    proposals: dto.proposals.map(mapProposal),
    autoExecutedCount: Number(dto.auto_executed_count ?? 0),
  };
}

export async function fetchProposalsApi(accessToken: string): Promise<AiActionProposal[]> {
  const dtos = await apiRequest<ApiAiProposal[]>('/ai/proposals', { accessToken });
  return dtos.map(mapProposal);
}

export async function updateProposalApi(
  accessToken: string,
  proposalId: string,
  payloadOverrides: Record<string, unknown>,
  recalculateSlots = false,
): Promise<AiActionProposal> {
  const dto = await apiRequest<ApiAiProposal>(`/ai/proposals/${proposalId}`, {
    method: 'PATCH',
    accessToken,
    body: {
      payload_overrides: payloadOverrides,
      recalculate_slots: recalculateSlots,
    },
  });
  return mapProposal(dto);
}

export async function acceptProposalApi(
  accessToken: string,
  proposalId: string,
  payloadOverrides?: Record<string, unknown>,
  idempotencyKey?: string,
): Promise<AiActionProposal> {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }
  const dto = await apiRequest<ApiAiProposal>(`/ai/proposals/${proposalId}/accept`, {
    method: 'POST',
    accessToken,
    headers,
    body: {
      ...(payloadOverrides ? { payload_overrides: payloadOverrides } : {}),
      ...(idempotencyKey ? { idempotency_key: idempotencyKey } : {}),
    },
  });
  return mapProposal(dto);
}

export async function rejectProposalApi(
  accessToken: string,
  proposalId: string,
  reason?: string,
): Promise<AiActionProposal> {
  const dto = await apiRequest<ApiAiProposal>(`/ai/proposals/${proposalId}/reject`, {
    method: 'POST',
    accessToken,
    body: { reason: reason?.trim() || null },
  });
  return mapProposal(dto);
}

export async function generateDailyBriefingApi(accessToken: string): Promise<AiReport> {
  const dto = await apiRequest<ApiAiReport>('/ai/briefing', {
    method: 'POST',
    accessToken,
  });
  return mapReport(dto);
}

export async function generateWeeklyReviewApi(accessToken: string): Promise<AiReport> {
  const dto = await apiRequest<ApiAiReport>('/ai/weekly-review', {
    method: 'POST',
    accessToken,
  });
  return mapReport(dto);
}

export async function fetchReportsApi(accessToken: string): Promise<AiReport[]> {
  const dtos = await apiRequest<ApiAiReport[]>('/ai/reports', { accessToken });
  return dtos.map(mapReport);
}

export async function ensureAiReportsApi(accessToken: string): Promise<{
  dailyBriefing: AiReport;
  weeklyReview: AiReport;
  createdDaily: boolean;
  createdWeekly: boolean;
}> {
  const dto = await apiRequest<{
    daily_briefing: ApiAiReport;
    weekly_review: ApiAiReport;
    created_daily: boolean;
    created_weekly: boolean;
  }>('/ai/reports/ensure', {
    method: 'POST',
    accessToken,
  });
  return {
    dailyBriefing: mapReport(dto.daily_briefing),
    weeklyReview: mapReport(dto.weekly_review),
    createdDaily: Boolean(dto.created_daily),
    createdWeekly: Boolean(dto.created_weekly),
  };
}

interface ApiAiProviderCatalogItem {
  id: AiProviderKind;
  label: string;
  console_url: string | null;
  default_base_url: string;
  requires_api_key: boolean;
}

interface ApiAiProviderModelInfo {
  id: string;
  label: string;
  owned_by: string | null;
  context_window: number | null;
}

interface ApiAiProviderConfig {
  provider: AiProviderKind;
  base_url: string;
  model: string;
  has_api_key: boolean;
  api_key_preview: string | null;
  source: 'user' | 'server_env' | 'default';
  available_providers: ApiAiProviderCatalogItem[];
}

interface ApiFetchProviderModelsResponse {
  provider: AiProviderKind;
  base_url: string;
  models: ApiAiProviderModelInfo[];
  count: number;
}

function mapProviderCatalogItem(dto: ApiAiProviderCatalogItem): AiProviderCatalogItem {
  return {
    id: dto.id,
    label: dto.label,
    consoleUrl: dto.console_url,
    defaultBaseUrl: dto.default_base_url,
    requiresApiKey: dto.requires_api_key,
  };
}

function mapProviderModel(dto: ApiAiProviderModelInfo): AiProviderModel {
  return {
    id: dto.id,
    label: dto.label,
    ownedBy: dto.owned_by ?? null,
    contextWindow: dto.context_window ?? null,
  };
}

function mapProviderConfig(dto: ApiAiProviderConfig): AiProviderConfig {
  const provider: AiProviderKind =
    dto?.provider === 'river' ||
    dto?.provider === 'openai_compatible' ||
    dto?.provider === 'gemini' ||
    dto?.provider === 'local'
      ? dto.provider
      : 'local';
  return {
    provider,
    baseUrl: typeof dto?.base_url === 'string' ? dto.base_url : '',
    model: typeof dto?.model === 'string' && dto.model ? dto.model : 'local-coach-v1',
    hasApiKey: Boolean(dto?.has_api_key),
    apiKeyPreview: typeof dto?.api_key_preview === 'string' ? dto.api_key_preview : null,
    source:
      dto?.source === 'user' || dto?.source === 'server_env' || dto?.source === 'default'
        ? dto.source
        : 'default',
    availableProviders: Array.isArray(dto?.available_providers)
      ? dto.available_providers.map(mapProviderCatalogItem)
      : [],
  };
}

export async function fetchAiProviderConfigApi(accessToken: string): Promise<AiProviderConfig> {
  const dto = await apiRequest<ApiAiProviderConfig>('/ai/provider/config', { accessToken });
  return mapProviderConfig(dto);
}

export async function updateAiProviderConfigApi(
  accessToken: string,
  payload: {
    provider: AiProviderKind;
    baseUrl?: string | null;
    model?: string | null;
    apiKey?: string | null;
    clearApiKey?: boolean;
  },
): Promise<AiProviderConfig> {
  const dto = await apiRequest<ApiAiProviderConfig>('/ai/provider/config', {
    method: 'PUT',
    accessToken,
    body: {
      provider: payload.provider,
      base_url: payload.baseUrl?.trim() || null,
      model: payload.model?.trim() || null,
      api_key: payload.apiKey?.trim() || null,
      clear_api_key: Boolean(payload.clearApiKey),
    },
  });
  return mapProviderConfig(dto);
}

export async function fetchAiProviderModelsApi(
  accessToken: string,
  payload: {
    provider: AiProviderKind;
    apiKey?: string | null;
    baseUrl?: string | null;
  },
): Promise<{
  provider: AiProviderKind;
  baseUrl: string;
  models: AiProviderModel[];
  count: number;
}> {
  const dto = await apiRequest<ApiFetchProviderModelsResponse>('/ai/provider/models', {
    method: 'POST',
    accessToken,
    body: {
      provider: payload.provider,
      api_key: payload.apiKey?.trim() || null,
      base_url: payload.baseUrl?.trim() || null,
    },
  });
  return {
    provider: dto.provider,
    baseUrl: dto.base_url,
    models: (dto.models ?? []).map(mapProviderModel),
    count: dto.count,
  };
}
