import React, { createContext, useReducer, useEffect } from 'react';

export const SimulationContext = createContext();

const initialState = {
  selectedTopology: 'enterprise_20n',
  selectedScenario: null,
  episodeCount: 1000,
  patchBaselineEpisodes: 200,
  patchEvalCVE: 50,
  executionHistory: [],
  currentResultsId: null,
  isRunning: false,
  error: null,
};

function simulationReducer(state, action) {
  switch (action.type) {
    case 'SET_TOPOLOGY':
      return { ...state, selectedTopology: action.payload };
    case 'SET_SCENARIO':
      return { ...state, selectedScenario: action.payload };
    case 'SET_EPISODES':
      return { ...state, episodeCount: action.payload };
    case 'SET_PATCH_BASELINE':
      return { ...state, patchBaselineEpisodes: action.payload };
    case 'SET_PATCH_EVAL':
      return { ...state, patchEvalCVE: action.payload };
    case 'START_EXECUTION':
      return { ...state, isRunning: true, error: null };
    case 'END_EXECUTION':
      return {
        ...state,
        isRunning: false,
        currentResultsId: action.payload,
        executionHistory: [
          ...state.executionHistory,
          { id: action.payload, timestamp: new Date().toISOString() },
        ],
      };
    case 'SET_ERROR':
      return { ...state, error: action.payload, isRunning: false };
    case 'LOAD_FROM_URL':
      return {
        ...state,
        selectedTopology: action.payload.topology || state.selectedTopology,
        selectedScenario: action.payload.scenario || state.selectedScenario,
        currentResultsId: action.payload.results || state.currentResultsId,
      };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

export function SimulationProvider({ children }) {
  const [state, dispatch] = useReducer(simulationReducer, initialState);

  // Save to sessionStorage whenever state changes
  useEffect(() => {
    sessionStorage.setItem('onyx_simulation', JSON.stringify(state));
  }, [state]);

  return (
    <SimulationContext.Provider value={{ ...state, dispatch }}>
      {children}
    </SimulationContext.Provider>
  );
}

export function useSimulation() {
  const context = React.useContext(SimulationContext);
  if (!context) {
    throw new Error('useSimulation must be used within SimulationProvider');
  }
  return context;
}
