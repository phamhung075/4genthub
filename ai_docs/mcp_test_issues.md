# MCP Tool Test Issues

This document summarizes the issues found during the MCP tool test.

## Issues

1.  **`manage_task` with `action='create'` fails without `user_id`**
    - **Description**: When calling `manage_task` with `action='create'`, the operation fails if `user_id` is not provided.
    - **Error Message**: `Cannot validate git_branch_id '...': Project repository creation requires user authentication. No user ID was provided.`
    - **Suggestion**: The error message could be more direct, for example: "`user_id` is required for this operation". Also, the documentation should clearly state that `user_id` is required for `create` action.

2.  **`manage_task` with `action='update'` and `status` change requires `details` field**
    - **Description**: When calling `manage_task` with `action='update'` and changing the `status`, the `details` field is required. This is not immediately obvious from the tool definition.
    - **Error Message**: `Missing required field: details (progress_notes). Status and progress updates must include progress description (minimum 5 characters).`
    - **Suggestion**: The tool definition should be updated to clearly state that the `details` field is required when changing the `status`. The error message is clear, but proactive documentation would be better.

## Fix Prompts

### Issue 1: `manage_task` create requires `user_id`

**Prompt:**

The `manage_task` tool with `action='create'` fails when the `user_id` is not provided. The current error message is a bit misleading. Please update the tool to:
1.  Return a clearer error message, such as "`user_id` is required for this operation".
2.  Update the tool's documentation to explicitly state that `user_id` is a required parameter for the `create` action.

### Issue 2: `manage_task` update requires `details`

**Prompt:**

The `manage_task` tool with `action='update'` requires a `details` field when the `status` is being changed. This requirement is not obvious to the user. Please update the tool to:
1.  Update the tool's documentation to clearly state that the `details` (or `progress_notes`) field is required when changing the `status` of a task. This will help users understand the requirement before they make a call.
