import React, { createContext, useReducer, useContext } from 'react';

export const ResultsContext = createContext();

const initialState = {
  simulationResults: null,
  patchResults: null,
  replayData: null,
  marlResults: null,
  costRanking: null,
  explainabilityCards: null,
  topologyData: null,
  status: null,
  loading: false,
  error: null,
};

function resultsReducer(state, action) {
  switch (action.type) {
    case 'SET_SIMULATION_RESULTS':
      return { ...state, simulationResults: action.payload };
    case 'SET_PATCH_RESULTS':
      return { ...state, patchResults: action.payload };
    case 'SET_REPLAY_DATA':
      return { ...state, replayData: action.payload };
    case 'SET_MARL_RESULTS':
      return { ...state, marlResults: action.payload };
    case 'SET_COST_RANKING':
      return { ...state, costRanking: action.payload };
    case 'SET_EXPLAINABILITY':
      return { ...state, explainabilityCards: action.payload };
    case 'SET_TOPOLOGY_DATA':
      return { ...state, topologyData: action.payload };
    case 'SET_STATUS':
      return { ...state, status: action.payload };
    case 'START_LOADING':
      return { ...state, loading: true, error: null };
    case 'END_LOADING':
      return { ...state, loading: false };
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

export function ResultsProvider({ children }) {
  const [state, dispatch] = useReducer(resultsReducer, initialState);

  return (
    <ResultsContext.Provider value={{ ...state, dispatch }}>
      {children}
    </ResultsContext.Provider>
  );
}

export function useResults() {
  const context = useContext(ResultsContext);
  if (!context) {
    throw new Error('useResults must be used within ResultsProvider');
  }
  return context;
}
