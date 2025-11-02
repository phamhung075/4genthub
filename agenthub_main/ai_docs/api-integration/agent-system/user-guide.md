# Agent Management User Guide

**Version**: 2.0.0
**Last Updated**: 2025-11-02

## Welcome

This guide helps you customize AI agents, share your configurations with others, and import agents created by the community. Whether you're tailoring an agent for your specific needs or discovering powerful configurations from other users, this guide will walk you through every step.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Customizing Your Agents](#customizing-your-agents)
3. [Sharing Your Agents](#sharing-your-agents)
4. [Importing Shared Agents](#importing-shared-agents)
5. [Managing Your Agents](#managing-your-agents)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### What is an Agent Instance?

An **agent instance** is your personal copy of an AI agent template. When you first use an agent (like `coding-agent` or `test-orchestrator-agent`), the system automatically creates an instance for you. You can then customize it to fit your specific needs.

**Key Concepts**:
- **Template**: The base agent definition (system-defined, read-only)
- **Instance**: Your personal copy that you can customize
- **Customization**: Changes you make to instructions, rules, or capabilities
- **Sharing**: Making your customized agent available to others
- **Importing**: Adding someone else's shared agent to your collection

### Accessing Your Agents

1. **Navigate to Agent Management**:
   - Open the AgentHub application
   - Click "My Agents" in the main navigation
   - You'll see a list of all your agent instances

2. **View Available Templates**:
   - Click "Browse Templates" to see all 42+ system agents
   - Click any template to automatically create your personal instance

---

## Customizing Your Agents

### Why Customize?

Customization lets you tailor agents to your specific workflow, coding standards, or domain expertise. For example:
- Make `coding-agent` an expert in your tech stack (Django + React)
- Configure `documentation-agent` to follow your company's style guide
- Tune `test-orchestrator-agent` for your testing frameworks

### Step 1: Select an Agent to Customize

1. Go to "My Agents"
2. Find the agent you want to customize
3. Click on it to open the configuration editor

### Step 2: Edit Configuration (Markdown Editor)

The configuration editor has 4 tabs:

#### **Instructions Tab**

Define what the agent does and how it behaves.

**Example - Python Django Expert**:

```markdown
# Python Django Expert

You are a senior Python developer specializing in Django web applications.

## Your Role
- Write production-ready Django code
- Follow Django best practices and conventions
- Use Django ORM efficiently
- Implement proper error handling

## Your Expertise
- Django 4.2+ framework
- Django REST Framework for APIs
- Celery for async tasks
- PostgreSQL database optimization
```

**Tips**:
- Use clear, directive language ("You are...", "You will...")
- Be specific about the agent's role and expertise
- Include relevant context (frameworks, versions, tools)

#### **Rules Tab**

Set standards and constraints the agent must follow.

**Example - Code Quality Rules**:

```markdown
## Code Standards

- Follow PEP 8 style guide
- Maximum line length: 100 characters
- Use type hints for all function signatures
- Write docstrings for all public methods

## Testing Requirements

- Write unit tests for all business logic
- Minimum 85% code coverage
- Use pytest framework
- Include edge case tests

## Security

- Never commit secrets or credentials
- Validate all user inputs
- Use Django's built-in security features
- Follow OWASP best practices
```

#### **Capabilities Tab**

List the agent's technical skills and tools.

**Example - Full-Stack Capabilities**:

```markdown
## Programming Languages

- Python 3.11+
- JavaScript (ES6+)
- TypeScript

## Frameworks & Libraries

- Django 4.2+
- Django REST Framework
- React 18+
- Tailwind CSS

## Tools & Platforms

- Git version control
- Docker containerization
- PostgreSQL database
- Redis caching
- Celery task queue

## Testing

- pytest
- Jest
- React Testing Library
```

#### **Output Format Tab**

Specify how the agent should format responses.

**Example - Structured Output**:

```markdown
## Response Format

Use markdown with clear section headers.

## Code Examples

- Always include complete, runnable code
- Add inline comments for complex logic
- Show imports at the top
- Include example usage

## Explanations

- Start with a brief summary
- Explain the "why" behind decisions
- Highlight potential gotchas
- Suggest alternatives when appropriate
```

### Step 3: Save Your Changes

1. Review all tabs to ensure everything is correct
2. Click "Save Configuration" button
3. Your agent instance is now marked as "Customized"
4. The system automatically converts markdown to structured JSON

**Visual Feedback**:
- ✅ **Green banner**: "Configuration saved successfully"
- 🔵 **Customized badge**: Shows on your agent card
- 📝 **Updated timestamp**: Reflects save time

### Step 4: Test Your Customization

1. Use the `call_agent` MCP tool with your agent
2. Verify it follows your customized instructions
3. Refine configuration as needed

**Example MCP Call**:

```python
response = call_agent("coding-agent")
# Your customized coding-agent will now follow your Django-specific rules
```

---

## Sharing Your Agents

### Why Share?

Share your customized agents to:
- Help teammates use consistent configurations
- Contribute to the community
- Showcase your expertise and best practices
- Build a library of specialized agents

### Step 1: Prepare Your Agent for Sharing

**Before sharing, ensure**:
1. ✅ Configuration is complete and tested
2. ✅ Instructions are clear and well-documented
3. ✅ No sensitive information (credentials, internal URLs)
4. ✅ Rules are generally applicable, not company-specific
5. ✅ Agent name is descriptive and professional

### Step 2: Generate a Share Link

1. Open your agent instance
2. Click the "Share" button (upper right)
3. Toggle "Make Public" to ON
4. System generates a secure share token

**You'll see**:
```
Share URL: https://agenthub.com/marketplace/agents/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
Token: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### Step 3: Distribute Your Share Link

**Share via**:
- Copy link to clipboard (click icon)
- QR code (for mobile sharing)
- Email or messaging apps
- Social media
- Documentation or wikis

### Step 4: Monitor Imports (Optional)

- View import count on your agent card
- See when it was last imported
- Agent appears in public marketplace automatically

### Revoking Sharing (Make Private Again)

1. Open the shared agent
2. Click "Share" button
3. Toggle "Make Public" to OFF
4. Confirm action

**What happens**:
- Share link becomes invalid
- Agent removed from marketplace
- Existing imports (copies) remain with other users
- You can re-share later with a new token

---

## Importing Shared Agents

### Why Import?

Importing lets you:
- Use expert configurations created by others
- Jumpstart your workflow with proven agents
- Learn from community best practices
- Customize imported agents further

### Method 1: Browse the Marketplace

1. Click "Marketplace" in main navigation
2. Browse or search for agents
3. Use filters:
   - **Category**: Development, Testing, Documentation, etc.
   - **Sort by**: Popular (most imported) or Recent (newest)
   - **Search**: Keywords in name or description

4. Click an agent card to preview
5. Review configuration preview
6. Click "Import" button

### Method 2: Use a Share Link

1. Receive a share link from a colleague or online
2. Click the link
3. Preview the agent configuration
4. Click "Import to My Agents"

### Import Dialog

**You'll see**:
```
┌─────────────────────────────────────────────┐
│  Import "Python Django Expert"              │
├─────────────────────────────────────────────┤
│  Creator: john@example.com                   │
│  Category: Development                       │
│  Imported 245 times                          │
│                                              │
│  Name (editable):                            │
│  [Python Django Expert                    ]  │
│                                              │
│  ⚠️ You already have "Python Django Expert"  │
│  Suggested name:                             │
│  "Python Django Expert - created by john"    │
│                                              │
│  [Cancel]              [Import Agent]        │
└─────────────────────────────────────────────┘
```

**Name Collision Handling**:
- If you already have an agent with the same name
- System suggests: `{name} - created by {creator}`
- You can accept or edit the suggested name

### After Import

**What you get**:
- ✅ Complete copy of the configuration
- ✅ Full edit permissions (it's your copy)
- ✅ Attribution to original creator (visible on card)
- ✅ Ability to further customize

**What you don't get**:
- ❌ Future updates from creator (it's a snapshot)
- ❌ Link to original (they're independent)

---

## Managing Your Agents

### View All Your Agents

**My Agents page shows**:
- Agent name
- Template type (e.g., coding-agent)
- Customization status (🔵 badge if customized)
- Visibility (🔒 Private or 🌐 Public)
- Creator (if imported)
- Last updated

**Actions**:
- **Edit**: Open configuration editor
- **Share**: Generate share link
- **Reset**: Restore to template defaults
- **Delete**: Remove from your account

### Reset to Defaults

If your customizations aren't working well:

1. Open the agent
2. Click "Reset to Defaults" button
3. Confirm action
4. Agent restored to original template

**Warning**: This permanently deletes your customizations. Consider exporting or copying important parts first.

### Delete an Agent Instance

1. Open agent or find in list
2. Click "Delete" button
3. Confirm action

**Notes**:
- Cannot delete if agent is currently in use (in a task)
- Deletion is soft (can be recovered by admin if needed within 30 days)
- If you shared this agent, the share link becomes invalid

---

## Best Practices

### Customization Best Practices

**Do**:
- ✅ Be specific about the agent's role and expertise
- ✅ Use clear, directive language in instructions
- ✅ Test customizations before sharing
- ✅ Document your rules and standards
- ✅ Keep capabilities list updated
- ✅ Use markdown formatting for readability

**Don't**:
- ❌ Include sensitive information (credentials, API keys)
- ❌ Make instructions too vague or generic
- ❌ Contradict the agent's base purpose
- ❌ Use company-specific jargon without explanation
- ❌ Forget to test after major changes

### Sharing Best Practices

**Before sharing**:
1. Review all configuration tabs
2. Remove internal/sensitive references
3. Add helpful comments and examples
4. Test the agent with typical use cases
5. Choose a clear, descriptive name

**Example - Good vs Bad Names**:
- ✅ Good: "Python Django Expert - REST APIs"
- ✅ Good: "React TypeScript Developer - Hooks & Testing"
- ❌ Bad: "My Agent"
- ❌ Bad: "Agent 1"
- ❌ Bad: "Test"

### Importing Best Practices

**Before importing**:
1. Preview the configuration carefully
2. Check creator reputation (import count)
3. Verify it matches your needs
4. Read instructions and rules thoroughly
5. Plan any additional customizations

**After importing**:
1. Test the agent with your workflows
2. Customize further if needed
3. Consider sharing your improved version
4. Provide feedback to original creator (if possible)

---

## Troubleshooting

### "Agent instance not found"

**Possible causes**:
- Agent was deleted
- Insufficient permissions
- Invalid agent ID in URL

**Solution**:
- Check "My Agents" page for correct agent
- Verify you're logged in with correct account
- Contact support if issue persists

### "Not authorized to access this agent"

**Possible causes**:
- Trying to access another user's private agent
- Insufficient permissions

**Solution**:
- Verify agent is shared (public)
- Check you're using correct share link
- Ask owner to re-share if link expired

### "Share token is invalid or expired"

**Possible causes**:
- Owner revoked sharing (made private)
- Incorrect share token
- Agent was deleted

**Solution**:
- Contact the person who shared the link
- Ask for a new share link
- Verify URL is complete and correct

### "Name collision detected"

**This is normal!** The system automatically suggests:
- Original name + " - created by [creator]"

**Options**:
1. Accept suggested name
2. Edit to your preference
3. Delete existing agent first (if you don't need it)

### Configuration not saving

**Possible causes**:
- Network connectivity issues
- Invalid markdown syntax
- Session expired

**Solution**:
1. Copy your changes to notepad (backup)
2. Refresh the page
3. Log in again if needed
4. Paste changes and save again
5. Check browser console for errors

### Imported agent behaves differently

**This is expected!** Remember:
- Import is a one-time snapshot
- Original agent may have been updated since
- You can customize your copy independently

**Solution**:
- Review and adjust the configuration
- Contact original creator for updates
- Re-import if creator shares updated version

---

## Frequently Asked Questions

### Q: How many agents can I customize?

**A**: Unlimited! You can have as many customized instances as needed.

### Q: Can I share the same agent multiple times?

**A**: Yes, but each share generates a new token. Old tokens are revoked when you unshare.

### Q: What happens if I import an agent I already have?

**A**: System detects name collision and suggests appending " - created by [creator]" to avoid conflicts.

### Q: Can I see who imported my shared agent?

**A**: You can see total import count, but not individual user details (privacy protection).

### Q: Do imported agents auto-update when the creator changes theirs?

**A**: No. Imports are snapshots. You'll need to re-import to get updates.

### Q: Can I export my agent configuration?

**A**: Yes, share it and use the share URL. You can also copy markdown content directly.

### Q: What's the difference between "Template" and "Instance"?

**A**: Templates are system-defined (read-only). Instances are your personal copies that you can customize.

### Q: Are there limits on customization?

**A**: Field length limits: Name (255 chars), Description (2000 chars), Instructions/Rules (no practical limit in markdown).

### Q: Can I collaborate on a shared agent?

**A**: Not directly. Sharing creates one-time copies. For collaboration, share updates via new share links.

### Q: How secure are share tokens?

**A**: Very secure! 32-character cryptographic tokens with 128-bit entropy. Practically impossible to guess.

---

## Getting Help

**Documentation**:
- API Reference: [api-reference.md](./api-reference.md)
- Developer Guide: [developer-guide.md](./developer-guide.md)

**Support**:
- GitHub Issues: https://github.com/example/agenthub/issues
- Community Forum: https://community.agenthub.com
- Email Support: support@agenthub.com

**Quick Tips**:
- Use search in marketplace to find specific agent types
- Check import count as a quality indicator
- Customize gradually - test after each major change
- Share early, get feedback, improve

---

## Next Steps

1. **Customize Your First Agent**: Pick a frequently-used agent and tailor it to your needs
2. **Explore the Marketplace**: See what the community has created
3. **Share Your Best Work**: Contribute your configurations to help others
4. **Join the Community**: Share tips, request features, help newcomers

**Happy Agent Customizing!** 🚀
