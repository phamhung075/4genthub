for each issue, give me prompt with detail for running on new session claude
fix issue on cause not symtome
tdd:
  description: "Complete test-driven development workflow for verifiable changes"
  prompt: |
    I want to implement a feature using Test-Driven Development (TDD). Follow this exact workflow:

    **Phase 1: Write Tests First**
    - Write comprehensive tests based on the expected input/output pairs I'll provide
    - This is TEST-DRIVEN DEVELOPMENT - do NOT create any mock implementations
    - Do NOT write any actual implementation code yet, even for functionality that doesn't exist
    - Focus only on writing thorough, realistic tests that capture the requirements
    - Ask clarifying questions about edge cases or test scenarios if needed

    **Phase 2: Verify Tests Fail**
    - Run the tests and confirm they fail as expected
    - Do NOT write any implementation code at this stage
    - Show me the test failures to verify we're starting from a clean slate

    **Phase 3: Commit Tests**
    - Once I'm satisfied with the tests, commit them with a clear message
    - The commit should only contain the test files

    **Phase 4: Implement Code**
    - Now write the minimal code needed to make ALL tests pass
    - Do NOT modify the tests during implementation
    - Run tests after each implementation attempt
    - Keep iterating: code → test → adjust → test until all tests pass
    - Show me the test results after each iteration

    **Phase 5: Verify Implementation**
    - Once all tests pass, verify the implementation isn't overfitting to the tests
    - Review the code for edge cases and potential issues
    - Run the tests one final time to confirm everything works

    **Phase 6: Commit Implementation**
    - Commit the implementation code with a descriptive message
    - The commit should only contain the implementation, not test changes

    Start with Phase 1. What feature would you like me to implement using TDD?

# Alternative shorter version for quick TDD cycles
tdd-quick:
  description: "Quick TDD cycle for smaller features"
  prompt: |
    Let's do a quick TDD cycle:
    1. I'll describe the feature - you write ONLY tests (no implementation)
    2. Run tests to confirm they fail
    3. Write minimal code to pass tests
    4. Iterate until all tests pass
    5. Commit when done

#Details : 
$ARGUMENTS