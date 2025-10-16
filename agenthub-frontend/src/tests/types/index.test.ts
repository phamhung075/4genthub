import { describe, it, expect } from "vitest";
import * as types from "../../types/index";

describe("types/index", () => {
  it("should export all type modules", () => {
    // Check that all expected exports exist
    expect(types).toBeDefined();
    
    // Since the index file re-exports from other modules,
    // we need to check that the re-exported types are available
    // This test ensures the barrel export is working correctly
    
    // The exact exports depend on what's in the individual type files
    // We're testing that the module loads without errors
    // and that it's not empty
    expect(Object.keys(types).length).toBeGreaterThan(0);
  });

  // Note: More specific tests for individual types should be in their respective test files
  // This test file primarily ensures the index barrel export is functioning correctly
});