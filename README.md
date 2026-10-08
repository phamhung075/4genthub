# 🚀 agenthub - AI-Human Collaboration Platform
Dai Hung PHAM
<div align="center">

[![Architecture Status](https://img.shields.io/badge/Architecture-Production%20NOT%20Ready-orange?style=for-the-badge)](https://github.com/agenthub/agenthub)
[![MCP Protocol](https://img.shields.io/badge/MCP%20Protocol-2024--11--05-blue?style=for-the-badge&logo=protocol)](https://modelcontextprotocol.io)
[![Docker Support](https://img.shields.io/badge/Docker-Multi%20Config-success?style=for-the-badge&logo=docker)](https://docker.com)
[![MCP Tools](https://img.shields.io/badge/MCP%20Tools-10%20Published-purple?style=for-the-badge&logo=robot)](https://github.com/agenthub/agenthub)

**The Future of Human-AI Collaboration in Software Development**

*Orchestrate human and AI work through a Model Context Protocol (MCP) native platform. The Python agent library's 32 role templates were retired; agents are now registry rows managed through the `manage_agent` MCP tool.*

[☁️ Cloud Platform](https://www.4genthub.com/) • [🎯 Quick Start](#-quick-start) • [🌟 Live Demo](#-live-demo) • [🤖 Agent Registry](#-agent-registry--seat-model) • [📚 Documentation](#-documentation) • [📋 Version History](#-version-history) • [💬 Community](#-community)

</div>

---

## ✨ **What Makes agenthub Special?**

🎭 **Human-First AI Orchestration** — Drive human and AI work through a beautiful web interface
🧠 **Composable Seats** — each seat renders its own guidance, skills and MCP servers from inherited company → room → seat overlays
🔗 **MCP Protocol Native** — Built on the Model Context Protocol for seamless AI integration
🎯 **Visual Task Management** — See your AI agents working in real-time through our React dashboard
🚀 **Multi-Agent Workflows** — Chain agent registry entries for complex development workflows
🌐 **Web-First Experience** — Designed for humans who prefer web interfaces over command lines
🧹 **Agent Registry** — Register, assign and update agents through the `manage_agent` MCP tool
🪑 **Seat Model** — The durable seat (room + seat key) is resolved with `manage_seat` / `call_seat`
🎨 **Per-Seat Tool Scope** — Each seat's tools and permissions are scoped to its role

## 🎯 **Perfect For Teams Who Want To...**

- 🤝 **Collaborate with AI agents** like they're team members
- 📊 **Visualize AI workflows** through an intuitive web dashboard
- 🔄 **Maintain context** across multiple AI sessions and agents
- 🎭 **Specialize AI agents** for different development roles
- 🌟 **Scale development** without losing quality or oversight
- 📈 **Track progress** of both human and AI contributions
- 🎭 **Assign agent registry entries** to tasks and branches
- 🎨 **Scope tools per seat** to match each role's workflow

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
- 🎭 **Seat management** — List seats and switch occupants
- 🧠 **Contexts** — four-level context records via `POST /api/v2/contexts/{level}`
- 🔍 **Health & status** — MCP registrations and metrics

</td>
<td width="50%">

### 🔧 **MCP Server**
```
http://localhost:8000
```
- 🤖 **10 published MCP tools**
- 🛠️ **Task, project, branch, context, agent, seat tools**
- 📋 **Contexts API** — `/api/v2/contexts/{level}` with inheritance
- 🔌 **`POST /mcp` JSON-RPC + `GET /mcp` SSE**
- 🔍 **Health monitoring (`GET /health`)**

</td>
</tr>
</table>

### 🎬 **Experience Highlights**

🎭 **Agent Theater** — Watch AI agents collaborate on your tasks in real-time
📊 **Smart Dashboards** — Beautiful visualizations of project progress and agent activity
🧠 **Context Streams** — See how context flows between agents and sessions
🎯 **One-Click Orchestration** — Deploy complex multi-agent workflows with simple clicks
⚡ **Instant Feedback** — Real-time updates as agents complete tasks and make decisions
🎭 **Seat Management** — List seats, resolve one, and switch its occupant
🧠 **Contexts** — Four-level context records with inheritance (`/api/v2/contexts`)
✨ **Agent Registry** — Register, assign and update agents through `manage_agent`

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

    C --> G[🔗 MCP Server<br/>Go (agenthub_go)]
    G --> H[🤖 Agent Registry<br/>manage_agent]
    G --> I[📊 Contexts API<br/>/api/v2/contexts]
    G --> J[🗄️ Database Layer<br/>PostgreSQL]
    G --> R[🪑 Seat Model<br/>manage_seat / call_seat]

    style A fill:#e1f5fe
    style B fill:#ffe0b2
    style C fill:#f3e5f5
    style G fill:#e8f5e8
    style H fill:#fff3e0
    style R fill:#fff3e0
```

</div>

### 🧩 **Core Components**

- 🪝 **Claude Hook Client**: Python-based enforcement system with pre-tool file system protection, post-tool documentation indexing, and 2-hour session tracking. Located in `.claude/hooks/`, it provides selective documentation enforcement, automatic index.json generation, root directory restrictions, kebab-case folder validation, and non-disruptive workflow protection
- 🔗 **MCP Server**: Go server (`agenthub_go`) with `POST /mcp` (JSON-RPC) and `GET /mcp` (SSE)
- 🎯 **Task Management**: Comprehensive DDD-compliant lifecycle management with visual tracking
- 🤖 **Agent Registry**: Register, assign and update agents through the `manage_agent` tool
- 🪑 **Seat Management**: Seats (room + seat key) resolved with `manage_seat` / `call_seat`
- 📋 **Project Management**: Hierarchical organization with automatic context inheritance
- 🌐 **Web Dashboard**: React-based interface optimized for human-AI collaboration
- 🐳 **Docker Infrastructure**: Multi-mode containerized deployment with one-click setup

### 🔌 **Rig and OpenRig workflow**

**OpenRig is the client and runtime; 4genthub is the cloud data for orchestration.** The installed `rig` CLI launches and supervises seats on your machine; this service stores the state they report and serves the configuration they pull. **The client initiates every exchange — the server never reaches into a user's machine.**

Three client-side scripts carry the traffic. Each holds `AGENTHUB_TOKEN` (never a value in this repository) and talks to this API:

| Script | What it does |
|---|---|
| `scripts/openrig_seat_sync.py` | **Pulls** a room's resolved seats and lays each one out on disk for OpenRig from an immutable snapshot — `<out>/<room>/<seat>/<hash>/…` plus `policy.json` and `pinned.json`. A pull is pinned by default; `--update` adopts a newer snapshot. |
| `scripts/openrig_bridge.py` | **Pushes observations up**: OpenRig seat status and herdr agent status, built from an allow-list, enums clamped to `unknown`, free text scrubbed. Status goes up only — it never receives commands and never reads terminal content. |
| `scripts/openrig_team_setup.py` | **Applies** a team definition (modules, room, seats, links, overlays) through the same publish path the UI uses; `apply` is idempotent. |

The seat model itself — rooms, seats, seat types, modules, overlays, links — is documented **once**, in `agenthub_go/NEXT_GEN.md` under "How the project and its seats work together", with the HTTP and MCP surface in `ai_docs/api-integration/surface-inventory.md`. **It is not repeated here.**

**Seats can also report friction back.** The same channel has three doors onto one writer: the MCP tool `submit_feedback`, the HTTP routes `POST`/`GET /api/v2/openrig/feedback`, and `scripts/seat_feedback.sh` for runtimes without MCP. A report carries the **layer** it belongs to (`runtime`, `openrig`, `cloud`, `seat-context`, `workspace`, `other`), the room and seat, and what happened; the credential scan runs before storage, and the dashboard groups reports by layer so a theme several seats hit reads as one theme rather than as several notes.

## 🤖 **Agent Registry & Seat Model**

> **The Python agent library is retired.** The 32 agent templates, the `agent_templates` / `user_agent_instances` tables that backed them, and the `call_agent` MCP tool were removed. The live surface is the `agents` registry table plus the `manage_agent` MCP tool (register, assign, get, list, update, unassign, unregister, rebalance), which keeps `call_agent` only as an optional data field.
>
> The durable role is now the **seat** (a room + seat key), managed with `manage_seat` (list, get, set_occupant) and resolved with `call_seat`. A seat's occupant is a runtime (`claude-code`, `codex`, `agy`, `omp`) plus a model.

See `ai_docs/api-integration/surface-inventory.md` §2 for the full MCP surface.

---

## 🚀 **Quick Start - Choose Your Path**

### ☁️ **Option 1: Cloud Platform (Recommended)**

<div align="center">

### **🌟 [Start Using agenthub Cloud Now](https://www.4genthub.com/) 🌟**

**Zero Setup • Instant Access • Fully Managed**

</div>

<table>
<tr>
<td width="50%">

#### ✨ **Why Choose Cloud?**
- ⚡ **Instant Access** — No installation required
- 🔧 **Zero Maintenance** — We handle updates & infrastructure
- 🚀 **Always Up-to-Date** — Latest features automatically
- 💪 **Enterprise Performance** — Optimized servers & scaling
- 🔒 **Secure & Reliable** — Professional hosting & backups
- 📱 **Access Anywhere** — Work from any device

</td>
<td width="50%">

#### 🎯 **Perfect For:**
- ✅ Quick evaluation and testing
- ✅ Teams who want zero DevOps overhead
- ✅ Users new to MCP protocol
- ✅ Production deployments without infrastructure hassle
- ✅ Collaborative team environments
- ✅ Anyone who values time over control

</td>
</tr>
</table>

**👉 Visit [https://www.4genthub.com/](https://www.4genthub.com/) to get started in seconds!**

---

### 🏠 **Option 2: Self-Hosted (Advanced Users)**

<div align="center">

**For users who need full control and want to host locally**

</div>

#### 🎯 **One-Line Setup**

```bash
# Clone → Setup → Run (that's it!)
git clone <repository-url> && cd agentic-project && ./docker-system/docker-menu.sh
```

#### 📋 **Prerequisites**
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
4. **Assign a seat** → `call_seat(room="my-room", seat="lead")`
5. **Watch magic happen** → work proceeds automatically

</td>
<td width="40%">

#### 🤖 **What the seat's occupant does** (Behind the Scenes)
1. Planning → Breaks down requirements
2. Architecture → Designs architecture
3. Implementation → Writes the code
4. Testing → Creates tests
5. Documentation → Writes ai_docs

</td>
</tr>
</table>

### 💡 **Power User: MCP Protocol Integration**

Transform any AI tool into a collaborative agent with our MCP protocol:

```python
# 🎭 1. Resolve your seat (the durable role) from the seat model
seat = mcp__agenthub_http__call_seat(room="my-room", seat="coding-agent")

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

**🧠 Context Inheritance**: a context resolved with `GET /api/v2/contexts/{level}/{context_id}/resolve` carries its inherited parent data
**📈 Progress Tracking**: Watch tasks evolve from idea to completion
**🔄 Session Continuity**: Stop and resume work - agents remember everything
**👥 Team Collaboration**: Multiple humans can collaborate with the same agent team

---

## 📚 **Documentation**

| Resource | Description | Link |
|----------|-------------|------|
| 🏗️ **Architecture Guide** | Deep dive into system design | `ai_docs/core-architecture/agenthub-system-architecture.md` |
| 🔧 **Development Guide** | Setup and contribution guide | `ai_docs/development-guides/` |
| 🛠️ **Operations Manual** | Deployment and maintenance | `ai_docs/operations/` |
| 🔍 **Troubleshooting** | Common issues and solutions | `ai_docs/troubleshooting-guides/` |
| 🧭 **API & MCP reference** | The mounted route and tool surface | `ai_docs/api-integration/surface-inventory.md` |
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
Planning: Break down tasks
  ↓
Architecture: Design system
  ↓
Implementation: Write code
  ↓
Testing: Create tests
  ↓
Human: Review and approve
```

</td>
<td width="50%">

#### 🐛 **Bug Resolution**
```
Human: Report issue
  ↓
Debugging: Investigate problem
  ↓
Root cause: Find cause
  ↓
Implementation: Write fix
  ↓
Testing: Verify fix
  ↓
Human: Validate solution
```

</td>
</tr>
</table>

### 🧠 **Context Intelligence**

The context API stores four levels of context records (`/api/v2/contexts/{level}`), each with an inheritance path:

**🌐 Global Context** → Organization-wide patterns and standards
**📋 Project Context** → Project-specific decisions and architecture
**🌿 Branch Context** → Feature-specific implementation details
**🎯 Task Context** → Granular work progress and discoveries

`GET /api/v2/contexts/{level}/{context_id}/resolve` folds the parent chain into one response; `.../delegate` copies data down a level, and `.../insights` and `.../progress` append to a context.

That is the **context API**, not the platform's composition model. How a seat is built — its guidance, skills and MCP servers — comes from company → room → seat overlays resolved per seat (`ai_docs/api-integration/surface-inventory.md` §1.13, §1.16).

---

## 🛠️ **MCP Tools & Capabilities**

<div align="center">

### **10 Published MCP Tools • JSON-RPC + SSE • Endless Possibilities**

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
- AI task actions **refuse legibly** when the AI integration seam is unwired — the caller gets the reason, not a generic error

</td>
<td width="33%">

#### 🤖 **Agent & Seat Orchestration**
- Agent registration & management (`manage_agent`)
- Seat list/get/set_occupant (`manage_seat`)
- Seat resolution (`call_seat`)
- Seat friction reporting (`submit_feedback`)
- Workflow coordination
- Context sharing between agents

</td>
<td width="33%">

#### 🧠 **Context Intelligence**
- Context records at four levels (`manage_context`)
- Inheritance via `resolve`
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
- Token management
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

### ⚡ **Performance — NOT MEASURED**
- **No benchmark of this server exists in this repository**, so the figures that used to print here (`<200ms average` response time, `10-50 concurrent users`, `Context Sync <5ms overhead`) are **removed rather than restated: they had no measurement behind them and none in the tree.** Settle them by measuring, or leave them out.
- **Agent Coordination**: real-time over the socket path — the mounted surface is in [the surface inventory](ai_docs/api-integration/surface-inventory.md)
- **Database**: PostgreSQL

</td>
<td width="50%">

### 📈 **Scaling Roadmap — TARGETS, NOT MEASURED CAPACITY**
- **Every tier below is an aspiration with no measurement behind it and no date metadata in the tree, and the quarters it names have passed** — recorded as a roadmap so that nothing here reads as current capacity.
- **MVP** (when written): 100 RPS
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
| 🎯 **Deploy marker** | `GET /health` reports the running version — **and only the BACKEND's: the frontend ships as a separate artifact, so its half is checked by the bundle filename the dashboard actually serves, and a deploy is complete only when both halves move.** **Measured 2026-10-06 (pass 3): production answers `healthy` with `"version":"0.0.22"` AND `origin/main` still declares `0.0.22`, while THE TREE'S RELEASE LITERAL HAS MOVED TO `0.0.23`** — the value lives in `agenthub_go/fastmcp/config/version.go:21` and is read by `healthVersion = config.ReleaseVersion` (`agenthub_go/fastmcp/server/httpapp/http.go:160`), so **the deployed and the prepared state now DIFFER and the tree sits 44 commits above the deployed tip** (packet 4, `fcd4c268`; the previous deploy was `0.0.21` at packet 3, `0018c644`). **Pass 2's sentence "the first deploy where the two agree" was true when it was written and is false now; it is corrected here rather than quietly dropped, because a row that says two versions agree is itself a claim that drifts.** The newest *released* section of the changelog is **`0.0.5` (2025-09-26)** — a separate numbering scheme — so this row carries the deploy marker and links the release history; the dated reads of both halves live in the packet-4 deploy record rather than here, where a bundle name would go stale. | [CHANGELOG.md](CHANGELOG.md) |

### 🚀 **Latest Releases**

**Recent highlights from our development journey:**

- **HISTORY — `[2025-09-19] - Iteration 107`** - 🏆 *"Septuple Centenarian Perfection"* — **this is a record of the RETIRED PYTHON TREE, not of this server:** `agenthub_main/` is archived and this repository no longer builds or tests it (`55c33107`, "ci: stop building and testing the archived Python server"). **The 541 tests and the 107 iterations are `agenthub_main`'s; the Go server's own tests are the live ones.** Kept, labelled, rather than deleted — **a release note that reads as a current highlight is a retired stack presented as live.**

- **Agent Library Retirement** - Removed the Python agent library (32 templates), the `agent_templates` / `user_agent_instances` tables and the `call_agent` MCP tool
  - Replaced by the seat model (`manage_seat` / `call_seat`) and the `agents` registry via `manage_agent`
  - Reduced complexity with no lost user workflow

### 📈 **Version Migration Guides**

When upgrading between versions, refer to our migration documentation:

- **Breaking Changes** - Documented in each release with migration steps
- **API Updates** - Version-specific changes to MCP protocol integration
- **Agent Changes** - Updates to the agent registry and the seat tool surface (`manage_seat` / `call_seat`)
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

[**GitHub Issues**](https://github.com/agenthub/agenthub/issues) • [**Discussions**](https://github.com/agenthub/agenthub/discussions)

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
- One platform for tasks, context and agent coordination
- Persistent context across all sessions
- Agents remember your preferences
- Visual dashboard shows everything
- Track AI work like team members
- Collaborative AI workflows
- Seat management with per-seat tool scope
- Agent registry for register/assign/update

</td>
</tr>
</table>

### 🎯 **The agenthub Promise**

> **"What if working with AI felt as natural as working with your best teammate?"**

✅ **Context that Never Dies** — Agents remember everything, forever
✅ **Visual AI Collaboration** — See your AI team working in real-time
✅ **Agent Registry & Seats** — Manage agents via `manage_agent` and durable seats via `manage_seat` / `call_seat`
✅ **Human-First Design** — Built for people who love web interfaces
✅ **Per-Seat Tool Scope** — Each seat's tools and permissions match its role
✅ **10 MCP Tools** — A small, stable MCP surface (`POST /mcp` + `GET /mcp` SSE)
✅ **Enterprise Ready** — Scales from solo dev to global teams

---

<div align="center">

## 🌟 **Ready to Experience the Future?**

### Transform how you collaborate with AI — Choose your path:

### ☁️ **Easiest Way: Cloud Platform**
### **[🚀 Start Now at 4genthub.com](https://www.4genthub.com/)**
**No setup required • Instant access • Fully managed**

---

### 🏠 **Advanced: Self-Hosted**
```bash
git clone <repository-url> && cd agentic-project && ./docker-system/docker-menu.sh
```

**Then visit:** http://localhost:3800 **and watch the magic happen** ✨

</div>

---

<div align="center">

**agenthub** • deployed marker **0.0.22** (production `GET /health` and `origin/main`, measured 2026-10-06) • tree release literal **0.0.23** (prepared, not pushed) • **Built with ❤️ for Human-AI Collaboration**

</div>
