export function isCurrentGeneration(requestGeneration, currentGeneration) {
  return requestGeneration === currentGeneration;
}

export function isCurrentSelection(request, current) {
  return request.generation === current.generation
    && request.modelKey === current.modelKey
    && request.tableRole === current.tableRole;
}
