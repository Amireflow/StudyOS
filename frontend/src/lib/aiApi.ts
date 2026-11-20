import type {
  AiActionProposal,
  AiContextScope,
  AiConversation,
  AiMessage,
  AiMessageRole,
  AiReport,
  AiReportType,
  AiToolSpec,
  ProposalStatus,
} from '../types/domain';
import { apiRequest } from './api-client';

interface ApiAiToolSpec {
  name: string;
  access: 'read' | 'proposal';
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
    label: dto.label,
    description: dto.description,
    requiresConfirmation: dto.requires_confirmation,
    parameterKeys: dto.parameter_keys,
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

export async function sendAiMessageApi(
  accessToken: string,
  conversationId: string,
  content: string,
  contextScopes?: AiContextScope[],
): Promise<{
  userMessage: AiMessage;
  assistantMessage: AiMessage;
  proposals: AiActionProposal[];
}> {
  const dto = await apiRequest<ApiAiTurn>(`/ai/conversations/${conversationId}/messages`, {
    method: 'POST',
    accessToken,
    body: {
      content: content.trim(),
      context_scopes: contextScopes ?? ['auto'],
    },
  });
  return {
    userMessage: mapMessage(dto.user_message),
    assistantMessage: mapMessage(dto.assistant_message),
    proposals: dto.proposals.map(mapProposal),
  };
}

export async function fetchProposalsApi(accessToken: string): Promise<AiActionProposal[]> {
  const dtos = await apiRequest<ApiAiProposal[]>('/ai/proposals', { accessToken });
  return dtos.map(mapProposal);
}

export async function acceptProposalApi(
  accessToken: string,
  proposalId: string,
  payloadOverrides?: Record<string, unknown>,
): Promise<AiActionProposal> {
  const dto = await apiRequest<ApiAiProposal>(`/ai/proposals/${proposalId}/accept`, {
    method: 'POST',
    accessToken,
    body: payloadOverrides ? { payload_overrides: payloadOverrides } : {},
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
