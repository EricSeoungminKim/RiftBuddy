export interface ChampSelectVisibilityState {
  shouldShowDraft: boolean;
  wasInChampSelect: boolean;
}

export function nextChampSelectVisibilityState(
  inProgress: boolean,
  previousWasInChampSelect: boolean,
  draftVisible: boolean,
): ChampSelectVisibilityState {
  if (!inProgress) {
    return { shouldShowDraft: false, wasInChampSelect: false };
  }
  return {
    shouldShowDraft: !previousWasInChampSelect || !draftVisible,
    wasInChampSelect: true,
  };
}
