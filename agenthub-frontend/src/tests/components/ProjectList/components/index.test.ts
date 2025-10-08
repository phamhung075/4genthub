import * as exports from '../../../../components/ProjectList/components';

describe('ProjectList components index exports', () => {
  it('exports ProjectListHeader component', () => {
    expect(exports.ProjectListHeader).toBeDefined();
    expect(typeof exports.ProjectListHeader).toBe('function');
  });

  it('exports ProjectListContent component', () => {
    expect(exports.ProjectListContent).toBeDefined();
    expect(typeof exports.ProjectListContent).toBe('function');
  });

  it('exports ProjectDialogs component', () => {
    expect(exports.ProjectDialogs).toBeDefined();
    expect(typeof exports.ProjectDialogs).toBe('function');
  });

  it('exports BranchItem component', () => {
    expect(exports.BranchItem).toBeDefined();
    expect(typeof exports.BranchItem).toBe('function');
  });

  it('exports all expected components', () => {
    const expectedExports = [
      'ProjectListHeader',
      'ProjectListContent', 
      'ProjectDialogs',
      'BranchItem'
    ];

    const actualExports = Object.keys(exports).filter(key => !key.endsWith('Props'));
    
    expect(actualExports).toEqual(expect.arrayContaining(expectedExports));
    expect(actualExports.length).toBeGreaterThanOrEqual(expectedExports.length);
  });

  it('re-exports components from their respective files', () => {
    // This test ensures that the exports are coming from the expected modules
    // The actual component implementations are tested in their individual test files
    const exportedComponents = Object.keys(exports).filter(key => !key.endsWith('Props'));
    
    exportedComponents.forEach(componentName => {
      const component = exports[componentName as keyof typeof exports];
      expect(component).toBeDefined();
      expect(typeof component).toBe('function');
    });
  });
});