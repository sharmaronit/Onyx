import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "../lib/api";
import { useAppMode } from "../lib/app-mode";

export function useCapabilities() {
  return useQuery({
    queryKey: ["capabilities"],
    queryFn: api.fetchCapabilities,
    staleTime: 30000,
  });
}

export function useTopologies() {
  return useQuery({
    queryKey: ["topologies"],
    queryFn: api.fetchTopologies,
    staleTime: Infinity,
  });
}

export function useRealityOverview(topology: string = "enterprise_20n") {
  const { mode } = useAppMode();
  return useQuery({
    queryKey: ["reality-overview", topology],
    queryFn: () => api.fetchRealityOverview(topology),
    refetchInterval: 15000,
    refetchIntervalInBackground: false,
    staleTime: 10000,
    placeholderData: (previousData) => previousData,
    retry: false,
    enabled: mode === "reality",
  });
}

export function useRealityTopology(topology: string = "enterprise_20n") {
  const { mode } = useAppMode();
  return useQuery({
    queryKey: ["reality-topology", topology],
    queryFn: () => api.fetchRealityTopology(topology),
    refetchInterval: 15000,
    refetchIntervalInBackground: false,
    staleTime: 10000,
    placeholderData: (previousData) => previousData,
    retry: false,
    enabled: mode === "reality",
  });
}

export function useStatus(topology: string = "enterprise_20n") {
  const { mode } = useAppMode();
  return useQuery({
    queryKey: ["status", topology, mode],
    queryFn: () => api.fetchStatus(topology, mode),
    refetchInterval: 30000, // 30 seconds
    enabled: mode === "demo",
  });
}

export function useTopology(topology: string = "enterprise_20n") {
  const { mode } = useAppMode();
  return useQuery({
    queryKey: ["topology", topology, mode],
    queryFn: () => api.fetchTopology(topology, mode),
  });
}

export function useTelemetryStatus(topology: string = "enterprise_20n", enabled: boolean = true) {
  const { mode } = useAppMode();
  return useQuery({
    queryKey: ["telemetry-status", topology, mode],
    queryFn: () => api.fetchTelemetryStatus(topology, mode),
    refetchInterval: 3000, // 3 seconds
    refetchIntervalInBackground: false,
    placeholderData: (previousData) => previousData,
    enabled,
  });
}

export function useEndpoints(topology: string = "enterprise_20n", enabled: boolean = true) {
  const { mode } = useAppMode();
  return useQuery({
    queryKey: ["endpoints", topology, mode],
    queryFn: () => api.fetchEndpoints(topology, mode),
    refetchInterval: 3000,
    refetchIntervalInBackground: false,
    placeholderData: (previousData) => previousData,
    enabled,
  });
}

export function useTelemetryEvents(topology: string = "enterprise_20n", enabled: boolean = true) {
  const { mode } = useAppMode();
  return useQuery({
    queryKey: ["telemetry-events", topology, mode],
    queryFn: () => api.fetchTelemetryEvents(topology, 200, mode),
    refetchInterval: 3000,
    refetchIntervalInBackground: false,
    placeholderData: (previousData) => previousData,
    enabled,
  });
}

export function useEndpointCommand() {
  const queryClient = useQueryClient();
  const { mode } = useAppMode();
  return useMutation({
    mutationFn: (params: {
      endpointId: string;
      action: "quarantine" | "restore";
      reason: string;
      requestedBy: string;
      responseKey: string;
    }) =>
      api.sendEndpointCommand(
        params.endpointId,
        params.action,
        params.reason,
        params.requestedBy,
        params.responseKey,
        mode,
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["endpoints"] }),
  });
}

export function useResolveIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      incidentId: string;
      resolvedBy: string;
      reason: string;
      responseKey: string;
    }) =>
      api.resolveIncident(params.incidentId, params.resolvedBy, params.reason, params.responseKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["endpoints"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["reality-overview"] });
      queryClient.invalidateQueries({ queryKey: ["reality-topology"] });
    },
  });
}

export function useServerLink() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      endpointId: string;
      disconnected: boolean;
      requestedBy: string;
      reason: string;
      responseKey: string;
    }) =>
      api.setServerLink(
        params.endpointId,
        params.disconnected,
        params.requestedBy,
        params.reason,
        params.responseKey,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["endpoints"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: api.fetchNotifications,
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
    placeholderData: (previousData) => previousData,
  });
}

export function useReplayLatest(topology: string = "enterprise_20n") {
  const { mode } = useAppMode();
  return useQuery({
    queryKey: ["replay-latest", topology, mode],
    queryFn: () => api.fetchReplayLatest(topology, mode),
  });
}

export function useSimulation() {
  const queryClient = useQueryClient();
  const { mode } = useAppMode();
  return useMutation({
    mutationFn: (params: {
      topology?: string;
      data_source?: api.DataSource;
      telemetry_weight?: number;
      n_episodes?: number;
      seed?: number;
    }) =>
      api.runSimulation(
        params.topology,
        "simulation",
        params.telemetry_weight,
        params.n_episodes,
        mode,
        params.seed,
      ),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["status"] });
      queryClient.invalidateQueries({ queryKey: ["saved-simulations"] });
      queryClient.setQueryData(["replay-latest", result.replay.topology, mode], {
        replay: result.replay,
      });
    },
  });
}

export function useSavedSimulations() {
  return useQuery({
    queryKey: ["saved-simulations"],
    queryFn: api.fetchSavedSimulations,
    staleTime: 10_000,
  });
}

export function useSavedSimulation(simulationId: string | null) {
  return useQuery({
    queryKey: ["saved-simulation", simulationId],
    queryFn: () => api.fetchSavedSimulation(simulationId!),
    enabled: !!simulationId,
  });
}

export function useRealityExposure() {
  const { mode } = useAppMode();
  return useQuery({
    queryKey: ["reality-exposure"],
    queryFn: api.fetchRealityExposure,
    refetchInterval: 15_000,
    staleTime: 10_000,
    enabled: mode === "reality",
  });
}

export function useRealityPatchRoi() {
  const { mode } = useAppMode();
  return useQuery({
    queryKey: ["reality-patch-roi"],
    queryFn: api.fetchRealityPatchRoi,
    refetchInterval: 15_000,
    staleTime: 10_000,
    enabled: mode === "reality",
  });
}

export function usePatchResults(
  topology: string = "enterprise_20n",
  data_source: string = "simulation",
) {
  const { mode } = useAppMode();
  const modeSource = mode === "demo" ? "simulation" : "telemetry";
  return useQuery({
    queryKey: ["patch-results", topology, modeSource, mode],
    queryFn: () => api.fetchPatchResults(topology, modeSource, mode),
    enabled: mode === "demo",
  });
}

export function usePatchOptimize() {
  const queryClient = useQueryClient();
  const { mode } = useAppMode();
  return useMutation({
    mutationFn: (params: {
      topology?: string;
      data_source?: string;
      n_baseline?: number;
      n_eval_per_patch?: number;
      telemetry_weight?: number;
    }) =>
      api.runPatchOptimize(
        params.topology,
        mode === "demo" ? "simulation" : "telemetry",
        params.n_baseline,
        params.n_eval_per_patch,
        params.telemetry_weight,
        mode,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patch-results"] });
      queryClient.invalidateQueries({ queryKey: ["cost-ranking"] });
      queryClient.invalidateQueries({ queryKey: ["explainability"] });
    },
  });
}

export function useCostModel() {
  return useQuery({
    queryKey: ["cost-model"],
    queryFn: () => api.fetchCostModel(),
  });
}

export function useUpdateCostModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      model: Pick<api.CostModel, "node_type_effort_hours" | "critical_asset_multiplier">;
      responseKey: string;
    }) => api.updateCostModel(params.model, params.responseKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cost-model"] });
      queryClient.invalidateQueries({ queryKey: ["patch-results"] });
    },
  });
}

export function useCostRanking(topology: string = "enterprise_20n", top_k: number = 12) {
  return useQuery({
    queryKey: ["cost-ranking", topology, top_k],
    queryFn: () => api.runCostRanking(topology, top_k),
  });
}

export function useExplainability() {
  return useMutation({
    mutationFn: (params: { topology?: string; top_n?: number }) =>
      api.fetchExplainability(params.topology, params.top_n),
  });
}
