export const PROJECT_SCREEN_LIMIT = 12;

export function effectiveProjectId(state, reference) {
  return reference?.projectId || state?.projectId || null;
}

export function projectRegistry(state) {
  if (Array.isArray(state?.projects) && state.projects.length > 0) {
    return state.projects;
  }
  if (!state?.projectId) return [];
  return [{ projectId: state.projectId, title: state.projectTitle }];
}

export function ensureProjectRegistry(state) {
  const projects = projectRegistry(state);
  if (state.projects === projects) return state;
  return { ...state, projects };
}
