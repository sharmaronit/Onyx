const ROLE_CAPABILITIES = {
  executive: {
    canRunSimulation: false,
    canRunScenario: false,
    canRunPatchOptimization: false,
    canViewPatchTab: true,
    canViewMarlTab: true,
    canQueueTrainingJob: false,
    canManageCostModels: false,
    analysisTabs: ['simulation', 'attack', 'patch', 'marl', 'replay'],
    maxEpisodes: 1000,
    lockEpisodes: true,
  },
  analyst: {
    canRunSimulation: true,
    canRunScenario: true,
    canRunPatchOptimization: false,
    canViewPatchTab: true,
    canViewMarlTab: true,
    canQueueTrainingJob: false,
    canManageCostModels: false,
    analysisTabs: ['simulation', 'attack', 'patch', 'marl', 'replay'],
    maxEpisodes: 5000,
    lockEpisodes: false,
  },
  architect: {
    canRunSimulation: true,
    canRunScenario: true,
    canRunPatchOptimization: true,
    canViewPatchTab: true,
    canViewMarlTab: true,
    canQueueTrainingJob: true,
    canManageCostModels: true,
    analysisTabs: ['simulation', 'attack', 'patch', 'marl', 'replay'],
    maxEpisodes: 10000,
    lockEpisodes: false,
  },
  demo: {
    canRunSimulation: true,
    canRunScenario: true,
    canRunPatchOptimization: true,
    canViewPatchTab: true,
    canViewMarlTab: true,
    canQueueTrainingJob: true,
    canManageCostModels: true,
    analysisTabs: ['simulation', 'attack', 'patch', 'marl', 'replay'],
    maxEpisodes: 2000,
    lockEpisodes: false,
  },
};

export function getRoleCapabilities(role = 'executive') {
  return ROLE_CAPABILITIES[role] || ROLE_CAPABILITIES.executive;
}

export function getRoleLabel(role = 'executive') {
  const labels = {
    executive: 'Executive',
    analyst: 'SOC Analyst',
    architect: 'Security Architect',
    demo: 'Demo/Judge',
  };
  return labels[role] || 'Executive';
}

export function getPermissionReason(role, action) {
  if (role === 'executive' && ['runSimulation', 'runScenario', 'runPatchOptimization'].includes(action)) {
    return 'Executive role is view-only for analysis execution. Switch to SOC Analyst or Security Architect to run simulations.';
  }
  if (role === 'analyst' && action === 'runPatchOptimization') {
    return 'Patch optimization is restricted to Security Architect and Demo/Judge roles.';
  }
  if (['executive', 'analyst'].includes(role) && ['queueTrainingJob', 'manageCostModels'].includes(action)) {
    return 'Training and cost model management are restricted to Security Architect and Demo/Judge roles.';
  }
  return 'This action is not available for your current role.';
}
