"use client";

const MODEL_CATALOG_INVALIDATED_EVENT = "poco:model-catalog-invalidated";

export function invalidateModelCatalog(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(new Event(MODEL_CATALOG_INVALIDATED_EVENT));
}

export function getModelCatalogInvalidatedEventName(): string {
  return MODEL_CATALOG_INVALIDATED_EVENT;
}
