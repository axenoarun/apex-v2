import api from './client';

// --- Auth ---
export const login = (email: string, password: string) =>
  api.post('/auth/login', new URLSearchParams({ username: email, password }), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
export const getMe = () => api.get('/auth/me');
export const refreshToken = (token: string) => api.post('/auth/refresh', { refresh_token: token });

// --- Organizations ---
export const listOrganizations = () => api.get('/organizations/');

// --- Projects ---
export const listProjects = (orgId?: string) =>
  api.get('/projects/', { params: orgId ? { organization_id: orgId } : {} });
export const getProject = (id: string) => api.get(`/projects/${id}`);
export const createProject = (data: { organization_id: string; name: string; client_name: string; description?: string }) =>
  api.post('/projects/', data);
export const updateProject = (id: string, data: Record<string, unknown>) => api.put(`/projects/${id}`, data);
export const listProjectRoles = (projectId: string) => api.get(`/projects/${projectId}/roles`);
export const assignProjectRole = (projectId: string, data: { user_id: string; role_id: string }) =>
  api.post(`/projects/${projectId}/roles`, data);

// --- Phases ---
export const listPhaseDefinitions = () => api.get('/phases/definitions');
export const listProjectPhases = (projectId: string) => api.get(`/phases/project/${projectId}`);
export const getPhaseDetail = (phaseId: string) => api.get(`/phases/${phaseId}`);
export const evaluateGate = (phaseId: string) => api.post(`/phases/${phaseId}/evaluate-gate`);
export const advancePhase = (projectId: string) => api.post(`/phases/project/${projectId}/advance`);
export const overrideAdvance = (projectId: string, reason: string) =>
  api.post(`/phases/project/${projectId}/advance-override`, { reason });
export const rollbackPhase = (projectId: string) => api.post(`/phases/project/${projectId}/rollback`);

// --- Tasks ---
export const listTaskDefinitions = (phaseDefId?: string) =>
  api.get('/tasks/definitions', { params: phaseDefId ? { phase_definition_id: phaseDefId } : {} });
export const listTasks = (params: Record<string, string>) => api.get('/tasks/', { params });
export const getTask = (id: string) => api.get(`/tasks/${id}`);
export const updateTask = (id: string, data: Record<string, unknown>) => api.put(`/tasks/${id}`, data);
export const completeTask = (id: string, data: { ai_output?: Record<string, unknown>; human_feedback?: Record<string, unknown> }) =>
  api.post(`/tasks/${id}/complete`, data);
export const assignTask = (id: string, assignedTo: string) =>
  api.post(`/tasks/${id}/assign`, { assigned_to: assignedTo });

// --- Sources ---
export const listSourceDefinitions = () => api.get('/sources/definitions');
export const selectSources = (projectId: string, ids: string[]) =>
  api.post(`/sources/project/${projectId}/select`, { source_definition_ids: ids });
export const listProjectSources = (projectId: string) => api.get(`/sources/project/${projectId}`);
export const updateSource = (id: string, data: Record<string, unknown>) => api.put(`/sources/${id}`, data);

// --- Agents ---
export const listAgentDefinitions = () => api.get('/agents/definitions');
export const createExecution = (data: Record<string, unknown>) => api.post('/agents/executions', data);
export const listExecutions = (params: Record<string, string>) => api.get('/agents/executions', { params });
export const getExecution = (id: string) => api.get(`/agents/executions/${id}`);

// --- AI Execution ---
export const executeAITask = (taskInstanceId: string, asyncMode = true) =>
  api.post('/agents/execute-task', { task_instance_id: taskInstanceId, async_mode: asyncMode });
export const resumeExecution = (executionId: string, additionalInput: Record<string, unknown>) =>
  api.post(`/agents/executions/${executionId}/resume`, { additional_input: additionalInput });
export const generateQuestions = (projectId: string, phaseInstanceId: string, asyncMode = true) =>
  api.post('/agents/generate-questions', { project_id: projectId, phase_instance_id: phaseInstanceId, async_mode: asyncMode });
export const generateDocument = (data: { project_id: string; template_id: string; phase_instance_id: string; task_instance_id?: string; async_mode?: boolean }) =>
  api.post('/agents/generate-document', data);
export const analyzeFeedback = (projectId: string) =>
  api.post('/agents/analyze-feedback', { project_id: projectId });
export const extractKnowledge = (projectId: string) =>
  api.post('/agents/extract-knowledge', { project_id: projectId });
export const getTrustAdjustments = (projectId: string) =>
  api.post('/agents/trust-adjustments', { project_id: projectId });

// --- Documents ---
export const listDocumentTemplates = (phaseDefId?: string) =>
  api.get('/documents/templates', { params: phaseDefId ? { phase_definition_id: phaseDefId } : {} });
export const createDocument = (data: Record<string, unknown>) => api.post('/documents/', data);
export const listProjectDocuments = (projectId: string, phaseId?: string) =>
  api.get(`/documents/project/${projectId}`, { params: phaseId ? { phase_instance_id: phaseId } : {} });
export const getDocument = (id: string) => api.get(`/documents/${id}`);
export const updateDocument = (id: string, data: Record<string, unknown>) => api.put(`/documents/${id}`, data);
export const reviewDocument = (id: string, data: { approved: boolean }) => api.post(`/documents/${id}/review`, data);

// --- Questions ---
export const createQuestion = (data: Record<string, unknown>) => api.post('/questions/', data);
export const createQuestionBatch = (data: Record<string, unknown>) => api.post('/questions/batch', data);
export const listQuestions = (params: Record<string, string>) => api.get('/questions/', { params });
export const answerQuestion = (id: string, answer: string) => api.post(`/questions/${id}/answer`, { answer });
export const getQuestionStats = (projectId: string) => api.get(`/questions/stats/${projectId}`);

// --- Feedback ---
export const submitFeedback = (data: Record<string, unknown>) => api.post('/feedback/', data);
export const listFeedback = (params: Record<string, string>) => api.get('/feedback/', { params });

// --- Notifications ---
export const listNotifications = (unreadOnly?: boolean) =>
  api.get('/notifications/', { params: { unread_only: unreadOnly || false } });
export const markNotificationRead = (id: string) => api.post(`/notifications/${id}/read`);
export const markAllRead = () => api.post('/notifications/read-all');

// --- Evals ---
export const listEvalDefinitions = () => api.get('/evals/definitions');
export const listEvalResults = (params: Record<string, string>) => api.get('/evals/results', { params });
export const getEvalSummary = (projectId: string) => api.get(`/evals/summary/${projectId}`);

// --- Costs ---
export const getProjectCosts = (projectId: string) => api.get(`/costs/project/${projectId}`);

// --- Improvements ---
export const createImprovement = (data: Record<string, unknown>) => api.post('/improvements/', data);
export const listImprovements = (params: Record<string, string>) => api.get('/improvements/', { params });
export const reviewImprovement = (id: string, data: { approved: boolean; reviewer_notes?: string }) => api.post(`/improvements/${id}/review`, data);

// --- Knowledge ---
export const createKnowledge = (data: Record<string, unknown>) => api.post('/knowledge/', data);
export const listKnowledge = (params?: Record<string, string>) => api.get('/knowledge/', { params });

// --- Workflow ---
export const listWorkflowInstances = (params: Record<string, string>) => api.get('/workflow/instances', { params });
export const getTaskInputs = (taskId: string) => api.get(`/workflow/task/${taskId}/inputs`);
export const getTaskOutputs = (taskId: string) => api.get(`/workflow/task/${taskId}/outputs`);

// --- Audit ---
export const listAuditLogs = (params: Record<string, string>) => api.get('/audit/', { params });
export const getAuditSummary = (projectId: string) => api.get(`/audit/project/${projectId}/summary`);

// --- Users ---
export const listUsers = () => api.get('/users/');
export const listRoles = () => api.get('/roles/');
