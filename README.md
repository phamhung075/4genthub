# 🚀 agenthub - AI-Human Collaboration Platform
Dai Hung PHAM
<div align="center">

[![Architecture Status](https://img.shields.io/badge/Architecture-Production%20NOT%20Ready-orange?style=for-the-badge)](https://github.com/agenthub/agenthub)
[![MCP Protocol](https://img.shields.io/badge/MCP%20Protocol-2.1.0-blue?style=for-the-badge&logo=protocol)](https://modelcontextprotocol.io)
[![Docker Support](https://img.shields.io/badge/Docker-Multi%20Config-success?style=for-the-badge&logo=docker)](https://docker.com)
[![AI Agents](https://img.shields.io/badge/AI%20Agents-32%20Core%20Agents-purple?style=for-the-badge&logo=robot)](https://github.com/agenthub/agenthub)

**The Future of Human-AI Collaboration in Software Development**

*Orchestrate 32 specialized AI agents through an intuitive web interface designed for humans who want to harness the power of AI without complexity. Recently optimized from 69 agents to 32 core agents for better maintainability and clearer specialization.*

[🎯 Quick Start](#-quick-start) • [🌟 Live Demo](#-live-demo) • [🤖 Agent Gallery](#-agent-gallery) • [📚 Documentation](#-documentation) • [📋 Version History](#-version-history) • [💬 Community](#-community)

</div>

---

## ✨ **What Makes agenthub Special?**

🎭 **Human-First AI Orchestration** — Control 32 specialized AI agents through a beautiful web interface
🧠 **Intelligent Context Management** — 4-tier hierarchy ensures AI agents never lose context between sessions
🔗 **MCP Protocol Native** — Built on the Model Context Protocol for seamless AI integration
🎯 **Visual Task Management** — See your AI agents working in real-time through our React dashboard
🚀 **Multi-Agent Workflows** — Chain specialized agents for complex development workflows
🌐 **Web-First Experience** — Designed for humans who prefer web interfaces over command lines
🧹 **Optimized Agent Library** — Streamlined from 69 to 32 agents for better maintainability and clearer specialization
🛍️ **Agent Marketplace** — Browse, customize, and share AI agents with your team and community
🎨 **Personal Agent Instances** — Create customized versions of agents tailored to your workflow

## 🎯 **Perfect For Teams Who Want To...**

- 🤝 **Collaborate with AI agents** like they're team members
- 📊 **Visualize AI workflows** through an intuitive web dashboard
- 🔄 **Maintain context** across multiple AI sessions and agents
- 🎭 **Specialize AI agents** for different development roles
- 🌟 **Scale development** without losing quality or oversight
- 📈 **Track progress** of both human and AI contributions
- 🛍️ **Share and discover** customized AI agents through the marketplace
- 🎨 **Customize agent behavior** to match their team's unique workflow

---

## 🌟 **Live Demo - See It In Action**

<table>
<tr>
<td width="50%">

### 📱 **Web Dashboard**
```
http://localhost:3800
```
- 🎯 **Real-time agent activity**
- 📊 **Visual task management**
- 🔄 **Context flow visualization**
- 👥 **Multi-agent coordination**
- 📈 **Progress tracking**
- 🛍️ **Agent marketplace** — Browse & import community agents
- 🎨 **My Agents** — Manage personal agent instances
- 📚 **Agent templates** — 60+ pre-configured agents

</td>
<td width="50%">

### 🔧 **MCP Server**
```
http://localhost:8000
```
- 🤖 **32 specialized AI agents**
- 🛠️ **15+ MCP tool categories**
- 📋 **4-tier context hierarchy**
- 🔌 **RESTful API endpoints**
- 🔍 **Health monitoring**

</td>
</tr>
</table>

### 🎬 **Experience Highlights**

🎭 **Agent Theater** — Watch AI agents collaborate on your tasks in real-time
📊 **Smart Dashboards** — Beautiful visualizations of project progress and agent activity
🧠 **Context Streams** — See how context flows between agents and sessions
🎯 **One-Click Orchestration** — Deploy complex multi-agent workflows with simple clicks
⚡ **Instant Feedback** — Real-time updates as agents complete tasks and make decisions
🛍️ **Community Marketplace** — Discover, share, and import customized agents from your team
🎨 **Personal Workspaces** — Create and manage your own agent instances with custom configurations
✨ **Smart Templates** — Browse 60+ ready-to-use agent templates across all specializations

---

## 🏗️ **Platform Architecture**

<div align="center">

```mermaid
graph TD
    A[👨‍💻 Human User] --> B[🪝 Claude Hook Client<br/>Python Enforcement System]
    B --> C[🌐 Web Dashboard<br/>React + TypeScript]
    B --> D[📁 File System<br/>Protection & Validation]
    B --> E[📚 Documentation<br/>ai_docs/ + index.json]
    B --> F[⏱️ Session Tracking<br/>2-hour Work Sessions]

    C --> G[🔗 MCP Server<br/>FastMCP + Python]
    G --> H[🤖 Agent Orchestra<br/>60+ Specialized Agents]
    G --> I[📊 4-Tier Context<br/>Global→Project→Branch→Task]
    G --> J[🗄️ Database Layer<br/>PostgreSQL + Redis]

    H --> K[🎭 Task Planning Agent]
    H --> L[💻 Coding Agent]
    H --> M[🔍 Debugger Agent]
    H --> N[🎨 UI Designer Agent]
    H --> O[🛡️ Security Auditor]
    H --> P[📚 Documentation Agent]
    H --> Q[🚀 And 54 More...]

    style A fill:#e1f5fe
    style B fill:#ffe0b2
    style C fill:#f3e5f5
    style G fill:#e8f5e8
    style H fill:#fff3e0
```

</div>

### 🧩 **Core Components**

- 🪝 **Claude Hook Client**: Python-based enforcement system with pre-tool file system protection, post-tool documentation indexing, and 2-hour session tracking. Located in `.claude/hooks/`, it provides selective documentation enforcement, automatic index.json generation, root directory restrictions, kebab-case folder validation, and non-disruptive workflow protection
- 🔗 **MCP Server**: FastMCP-based server with streamable HTTP transport and RESTful APIs
- 🎯 **Task Management**: Comprehensive DDD-compliant lifecycle management with visual tracking
- 🤖 **Agent Orchestration**: Multi-agent coordination with intelligent role-based switching
- 🛍️ **Agent Management**: Complete agent lifecycle — browse templates, create instances, customize, share via marketplace
- 📋 **Project Management**: Hierarchical organization with automatic context inheritance
- 🌐 **Web Dashboard**: React-based interface optimized for human-AI collaboration
- 🐳 **Docker Infrastructure**: Multi-mode containerized deployment with one-click setup

## 🤖 **Agent Gallery - Meet Your Optimized AI Team**

> **✨ Recently optimized from 69 to 32 agents** for better maintainability and clearer specialization. All 32 agent templates load successfully with the new agent management system, enabling instant agent instance creation and customization.

<table>
<tr>
<td width="33%">

### 🎭 **Creative & Design** (2 agents)
- `@ui_designer_expert_shadcn_agent` - UI/UX with shadcn/ui
- `@design_system_agent` - Design systems & consistency
- `@branding_agent` - Brand strategy
- ~~`@graphic_design_agent`~~ - *Merged into branding*

</td>
<td width="33%">

### 💻 **Development & Engineering** (8 agents)
- `@coding_agent` - Implementation
- `@debugger_agent` - Bug hunting
- `@system_architect_agent` - System design
- `@devops_agent` - Infrastructure
- `@code_reviewer_agent` - Code quality
- `@tech_spec_agent` - Technical specifications
- `@technology_advisor_agent` - Tech stack decisions
- `@prototyping_agent` - Interactive prototypes

</td>
<td width="33%">

### 🔍 **Analysis & Planning** (7 agents)
- `@task_planning_agent` - Project planning  
- `@deep_research_agent` - Investigation
- `@root_cause_analysis_agent` - Problem solving
- `master-orchestrator-agent` - Coordination
- `@project_initiator_agent` - Project setup
- `@elicitation_agent` - Requirements gathering
- `@prd_architect_agent` - Product requirements

</td>
</tr>
<tr>
<td width="33%">

### 🛡️ **Security & Compliance** (2 agents)
- `@security_auditor_agent` - Security review
- `@compliance_scope_agent` - Regulatory compliance
- ~~`@security_penetration_tester_agent`~~ - *Merged into security_auditor*

</td>
<td width="33%">

### 🧪 **Quality & Testing** (2 agents)
- `@test_orchestrator_agent` - Comprehensive QA coordination
- `@performance_load_tester_agent` - Performance testing
- ~~`@lead_testing_agent`~~ - *Merged into test_orchestrator*
- ~~`@functional_tester_agent`~~ - *Merged into test_orchestrator*

</td>
<td width="33%">

### 📈 **Business & Marketing** (2 agents)
- `@marketing_strategy_orchestrator_agent` - Marketing strategy
- `@content_strategy_agent` - Content planning
- ~~`@campaign_manager_agent`~~ - *Merged into marketing_strategy*
- ~~`@market_research_agent`~~ - *Merged into deep_research*

</td>
</tr>
</table>

**🎯 Agent Highlights:**
- **Smart Context Sharing** — Agents inherit knowledge from previous work
- **Role Specialization** — Each agent excels in their specific domain
- **Collaborative Workflows** — Agents work together seamlessly on complex tasks
- **Dynamic Assignment** — System automatically selects the best agent for each task
- **Personal Instances** — Create customized versions of any agent with your preferred settings
- **Community Sharing** — Share your customized agents with team via marketplace
- **Instant Access** — One-click bulk creation of all 32 agent instances

---

## 🚀 **Quick Start - Get Running in 3 Minutes**

### 🎯 **One-Line Setup**

```bash
# Clone → Setup → Run (that's it!)
git clone <repository-url> && cd agentic-project && ./docker-system/docker-menu.sh
```

### 📋 **Prerequisites** 
🐳 **Docker & Docker Compose** (that's all you need!)  
Optional: Python 3.8+, Node.js 18+, WSL2 (Windows)

### 🎬 **Interactive Docker Menu**

<div align="center">

```
╔════════════════════════════════════════════════════════╗
║             agenthub Docker Management               ║
║                  Build System v3.0                    ║
╚════════════════════════════════════════════════════════╝

🚀 Quick Start Options
────────────────────────────────────────────────────────
  1) 🐘 PostgreSQL Local (Recommended for beginners)
  2) ☁️  Supabase Cloud (Best for teams)  
  3) ☁️🔴 Supabase + Redis (Enterprise mode)
  P) ⚡ Performance Mode (Low-resource PCs)

🛠️  Management
────────────────────────────────────────────────────────
  4) 📊 Show Status     5) 🛑 Stop Services
  6) 📜 View Logs       7) 🗄️  Database Shell
  8) 🧹 Clean System    9) 🔄 Force Rebuild
```

</div>

### ⚡ **2-Minute Setup Guide**

1️⃣ **Launch the menu**: `./docker-system/docker-menu.sh`  
2️⃣ **Pick your setup**: Choose option `1` for local development  
3️⃣ **Access your dashboard**: Open http://localhost:3800  
4️⃣ **Start collaborating**: Your AI agents are ready to work!

---

## 🎯 **Your First AI Collaboration - A 5-Minute Journey**

### 🎬 **Scenario**: Build a Login System with AI Agents

<table>
<tr>
<td width="60%">

#### 👨‍💻 **What You Do** (Web Dashboard)
1. **Open dashboard** → http://localhost:3800
2. **Create project** → "User Authentication"
3. **Click "New Task"** → "Implement login system"
4. **Assign agents** → Select `@task_planning_agent`
5. **Watch magic happen** → Agents collaborate automatically

</td>
<td width="40%">

#### 🤖 **What AI Agents Do** (Behind the Scenes)
1. `@task_planning_agent` → Breaks down requirements
2. `@system_architect_agent` → Designs architecture  
3. `@coding_agent` → Implements code
4. `@test_orchestrator_agent` → Creates tests
5. `@documentation_agent` → Writes ai_docs

</td>
</tr>
</table>

### 💡 **Power User: MCP Protocol Integration**

Transform any AI tool into a collaborative agent with our MCP protocol:

```python
# 🎭 1. Load agent configuration from your personal instance
agent = mcp__agenthub_http__call_agent(name_agent="coding-agent")

# 📋 2. Create collaborative workspace  
project = mcp__agenthub_http__manage_project(
    action="create",
    name="user-authentication-system",
    description="Complete JWT-based authentication with React frontend"
)

# 🌿 3. Set up development branch
branch = mcp__agenthub_http__manage_git_branch(
    action="create",
    project_id=project["project"]["id"],
    git_branch_name="feature/auth-system",
    git_branch_description="Authentication system implementation"
)

# 🎯 4. Define AI-human collaborative task
task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id=branch["git_branch"]["id"],
    title="Build complete authentication system",
    description="JWT backend + React frontend + tests + ai_docs",
    priority="high"
)

# 🧠 5. Share context across AI sessions (the magic!)
mcp__agenthub_http__manage_context(
    action="create",
    level="task",
    context_id=task["task"]["id"],
    git_branch_id=branch["git_branch"]["id"],
    data={
        "requirements": {
            "backend": "Node.js with JWT and bcrypt",
            "frontend": "React with auth context",
            "database": "User profiles and sessions",
            "testing": "Unit + integration tests"
        },
        "human_preferences": {
            "ui_framework": "Material-UI",
            "validation": "Yup schema validation",
            "state_management": "React Context API"
        }
    }
)

# 🎊 Result: Agents now know your preferences and work together!
```

### 🌟 **The Context Magic**

**🧠 Context Inheritance**: Every agent automatically knows what previous agents discovered  
**📈 Progress Tracking**: Watch tasks evolve from idea to completion  
**🔄 Session Continuity**: Stop and resume work - agents remember everything  
**👥 Team Collaboration**: Multiple humans can collaborate with the same agent team

---

## 📚 **Documentation**

| Resource | Description | Link |
|----------|-------------|------|
| 🏗️ **Architecture Guide** | Deep dive into system design | `ai_docs/CORE_ARCHITECTURE/` |
| 🔧 **Development Guide** | Setup and contribution guide | `ai_docs/DEVELOPMENT_GUIDES/` |
| 🛠️ **Operations Manual** | Deployment and maintenance | `ai_docs/OPERATIONS/` |
| 🔍 **Troubleshooting** | Common issues and solutions | `ai_docs/TROUBLESHOOTING/` |
| ✨ **Vision System** | AI enhancement documentation | `ai_docs/vision/` |
| 📋 **Changelog** | Version history and release notes | [CHANGELOG.md](CHANGELOG.md) |

---

## 🌈 **Human-AI Collaboration Patterns**

### 🔄 **Collaborative Workflows**

<table>
<tr>
<td width="50%">

#### 🎯 **Feature Development**
```
Human: Define requirements
  ↓
@task_planning_agent: Break down tasks
  ↓  
@system_architect_agent: Design system
  ↓
@coding_agent: Implement code
  ↓
@test_orchestrator_agent: Create tests
  ↓
Human: Review and approve
```

</td>
<td width="50%">

#### 🐛 **Bug Resolution**
```
Human: Report issue
  ↓
@debugger_agent: Investigate problem
  ↓
@root_cause_analysis_agent: Find cause
  ↓
@coding_agent: Implement fix
  ↓
@test_orchestrator_agent: Verify fix
  ↓
Human: Validate solution
```

</td>
</tr>
</table>

### 🧠 **Context Intelligence**

**🌐 Global Context** → Organization-wide patterns and standards  
**📋 Project Context** → Project-specific decisions and architecture  
**🌿 Branch Context** → Feature-specific implementation details  
**🎯 Task Context** → Granular work progress and discoveries

**The Magic**: Every AI agent automatically inherits relevant context, ensuring consistency and eliminating repetitive explanations.

---

## 🛠️ **MCP Tools & Capabilities**

<div align="center">

### **15+ Tool Categories • 50+ Individual Tools • Endless Possibilities**

</div>

<table>
<tr>
<td width="33%">

#### 🎯 **Task & Project Management**
- Task lifecycle orchestration
- Subtask creation & tracking  
- Project hierarchy management
- Git branch coordination
- Dependency management

</td>
<td width="33%">

#### 🤖 **Agent Orchestration**
- Dynamic agent role switching
- Multi-agent collaboration
- Agent registration & management
- Personal agent instances
- Agent marketplace with sharing
- Bulk agent creation
- Workflow coordination
- Context sharing between agents

</td>
<td width="33%">

#### 🧠 **Context Intelligence**
- 4-tier context hierarchy
- Automatic inheritance  
- Cross-session persistence
- Real-time synchronization
- Context validation

</td>
</tr>
<tr>
<td width="33%">

#### 🛡️ **Security & Compliance**
- Authentication & authorization
- Compliance tracking
- Security validation
- Connection management
- Audit logging

</td>
<td width="33%">

#### 📊 **Analytics & Monitoring**
- Performance metrics
- Health monitoring  
- Usage analytics
- Progress tracking
- System diagnostics

</td>
<td width="33%">

#### 🔧 **Developer Tools**
- Rule management
- Configuration handling
- Debugging utilities
- Testing frameworks
- Documentation generation

</td>
</tr>
</table>

---

## 🚀 **Performance & Scale**

<table>
<tr>
<td width="50%">

### ⚡ **Current Performance**
- **Response Time**: <200ms average
- **Concurrent Users**: 10-50 users  
- **Agent Coordination**: Real-time
- **Context Sync**: <5ms overhead
- **Database**: PostgreSQL + Redis

</td>
<td width="50%">

### 📈 **Scaling Roadmap**
- **MVP** (Current): 100 RPS
- **Tier 1** (Q2 2025): 1K RPS + Microservices
- **Tier 2** (Q3 2025): 10K RPS + Service Mesh
- **Enterprise** (Q4 2025): 1M+ RPS + Global Edge

</td>
</tr>
</table>

---

## 📋 **Version History**

### 📚 **Changelog & Release Notes**

Track all changes, releases, and improvements to the agenthub platform through our comprehensive changelog.

| Resource | Description | Link |
|----------|-------------|------|
| 📋 **Main Changelog** | Complete version history and release notes | [CHANGELOG.md](CHANGELOG.md) |
| 🏷️ **Release Format** | Follows Keep a Changelog specification | [keepachangelog.com](https://keepachangelog.com/) |
| 🔢 **Versioning** | Semantic Versioning (MAJOR.MINOR.PATCH) | [semver.org](https://semver.org/) |
| 🎯 **Current Version** | v0.0.2 - Production NOT Ready | [Latest Release](CHANGELOG.md#unreleased) |

### 🚀 **Latest Releases**

**Recent highlights from our development journey:**

- **[2025-09-19] - Iteration 107** - 🏆 Septuple Centenarian Perfection
  - 541 tests passing with 100% success rate
  - 107 consecutive perfect iterations achieved
  - Self-healing system with zero maintenance required

- **Agent Library Optimization** - Streamlined from 69 to 32 specialized agents
  - Better maintainability and clearer role specialization
  - Enhanced performance and reduced complexity
  - Comprehensive cleanup with maintained functionality

### 📈 **Version Migration Guides**

When upgrading between versions, refer to our migration documentation:

- **Breaking Changes** - Documented in each release with migration steps
- **API Updates** - Version-specific changes to MCP protocol integration
- **Agent Changes** - Updates to agent capabilities and tool permissions
- **Configuration Updates** - Environment and setup requirement changes

### 🔄 **Release Process**

Our release process follows industry best practices:

1. **Development** → Feature branches with comprehensive testing
2. **Integration** → Merge to main with full test suite validation
3. **Documentation** → Update changelog with Keep a Changelog format
4. **Release** → Semantic versioning with clear release notes
5. **Migration Support** → Upgrade guides and backward compatibility notes

---

## 💬 **Community**

<div align="center">

### **Join the Human-AI Collaboration Revolution**

🌟 **Star us on GitHub** • 🐛 **Report Issues** • 💡 **Suggest Features** • 📚 **Contribute Docs**

[**GitHub Issues**](https://github.com/agenthub/agenthub/issues) • [**Discussions**](https://github.com/agenthub/agenthub/discussions) • [**Contributing Guide**](CONTRIBUTING.md)

</div>

---

## 🎉 **Why agenthub Will Transform Your Development**

<div align="center">

### **Stop Fighting AI Tools. Start Collaborating With Them.**

</div>

<table>
<tr>
<td width="50%">

#### 😫 **Before agenthub**
- Switching between multiple AI tools
- Losing context between sessions  
- Repeating the same explanations
- Managing complex prompts manually
- No visibility into AI work progress
- Isolated AI interactions

</td>
<td width="50%">

#### 🚀 **With agenthub**
- One platform, 32 optimized + 60+ customizable agents
- Persistent context across all sessions
- Agents remember your preferences
- Visual dashboard shows everything
- Track AI work like team members
- Collaborative AI workflows
- Personal agent instances with custom configs
- Community marketplace for sharing agents

</td>
</tr>
</table>

### 🎯 **The agenthub Promise**

> **"What if working with AI felt as natural as working with your best teammate?"**

✅ **Context that Never Dies** — Agents remember everything, forever
✅ **Visual AI Collaboration** — See your AI team working in real-time
✅ **Specialized AI Experts** — 32 core agents + 60+ customizable instances, each mastering their craft
✅ **Human-First Design** — Built for people who love web interfaces
✅ **Personal Agent Workspaces** — Create, customize, and manage your own agent instances
✅ **Community Marketplace** — Share and discover agents customized by your team
✅ **Enterprise Ready** — Scales from solo dev to global teams

---

<div align="center">

## 🌟 **Ready to Experience the Future?**

### Get started in 3 minutes and transform how you collaborate with AI

```bash
git clone <repository-url> && cd agentic-project && ./docker-system/docker-menu.sh
```

**Then visit:** http://localhost:3800 **and watch the magic happen** ✨

</div>

---

<div align="center">

**agenthub v0.0.2** • **Production NOT Ready** • **Built with ❤️ for Human-AI Collaboration**

</div>
