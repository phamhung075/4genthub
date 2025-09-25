# Clean Code Enforcement in Agent Library

## Overview
All code-working agents in the agenthub system now strictly enforce Clean Code, DRY (Don't Repeat Yourself), and SOLID principles. This ensures high-quality, maintainable code across all agent-generated outputs.

## Updated Agents

### Primary Code Agents
1. **coding-agent** - Implements all code with clean principles
2. **debugger-agent** - Fixes bugs while improving code quality
3. **code-reviewer-agent** - Enforces standards during reviews
4. **test-orchestrator-agent** - Ensures clean test code
5. **prototyping-agent** - Creates clean, evolvable prototypes
6. **devops-agent** - Applies clean code to infrastructure

## Core Principles

### Clean Code
- **Meaningful Names**: Self-documenting, intention-revealing names
- **Small Functions**: 20-30 lines maximum, single purpose
- **No Side Effects**: Pure functions when possible
- **Proper Error Handling**: Exceptions over return codes
- **Self-Documenting**: Code explains itself without comments

### DRY Principle
- **No Duplication**: Every piece of knowledge has single representation
- **Extract Common Code**: Reusable functions and modules
- **Use Constants**: Named constants instead of magic numbers
- **Central Configuration**: Single source of truth
- **Template Patterns**: Reuse similar structures
- **Factory Pattern Detection**: Automatically detect and refactor duplicate object creation
- **Auto-Generate Factories**: Create factory classes for reusable object instantiation

### SOLID Principles

#### Single Responsibility
- Classes have one reason to change
- Functions do one thing well
- High cohesion within modules

#### Open/Closed
- Open for extension, closed for modification
- Use abstractions and interfaces
- Strategy pattern for varying behavior

#### Liskov Substitution
- Derived classes properly substitute base classes
- No violation of parent contracts
- Consistent behavior in inheritance

#### Interface Segregation
- Small, focused interfaces
- Clients not forced to depend on unused methods
- Role-based interface design

#### Dependency Inversion
- Depend on abstractions, not concretions
- Dependency injection
- Inversion of control

## Enforcement Rules

### Automatic Rejection Criteria
- **Code Duplication**: Any copy-paste code
- **Giant Functions**: Over 50 lines
- **God Classes**: Over 300 lines
- **Deep Nesting**: Over 3 levels
- **Magic Numbers**: Hardcoded values
- **Poor Naming**: Ambiguous or misleading names

### Quality Metrics
- **Cyclomatic Complexity**: Maximum 10
- **Function Length**: Maximum 30 lines
- **Class Length**: Maximum 300 lines
- **File Length**: Maximum 500 lines
- **Test Coverage**: Minimum 80%
- **Test Speed**: Unit tests < 100ms

## Agent-Specific Implementations

### Coding Agent
- Enforces all principles during implementation
- Creates modular, testable code
- Follows existing patterns and conventions
- Automatically refactors violations

### Debugger Agent
- Fixes bugs AND improves code structure
- Eliminates duplication that causes bugs
- Applies SOLID to prevent future issues
- Simplifies complex, bug-prone code

### Code Reviewer Agent
- Strict enforcement of all principles
- Provides detailed feedback with examples
- Suggests design patterns for improvements
- Educates on why principles matter

### Test Orchestrator Agent
- Test code follows same standards as production
- DRY principle in test utilities and fixtures
- Single concept per test
- Clear, self-documenting test names

### Prototyping Agent
- Clean code even in prototypes
- Structured for easy evolution to production
- Modular design from the start
- Avoids technical debt accumulation

### DevOps Agent
- Infrastructure as clean code
- DRY in configurations and scripts
- Modular, reusable components
- Proper error handling in automation

## File Structure

```
agenthub_main/agent-library/
├── shared/
│   └── clean_code_principles.yaml       # Shared principles definition
├── config/
│   └── clean_code_master_config.yaml    # Master configuration
└── agents/
    ├── coding-agent/rules/
    │   ├── implementation_methodology.yaml  # Updated with clean code
    │   └── clean_code_enforcement.yaml     # Specific enforcement rules
    ├── debugger-agent/rules/
    │   └── clean_code_enforcement.yaml
    ├── code-reviewer-agent/rules/
    │   └── clean_code_enforcement.yaml
    ├── test-orchestrator-agent/rules/
    │   └── clean_code_enforcement.yaml
    ├── prototyping-agent/rules/
    │   └── clean_code_enforcement.yaml
    └── devops-agent/rules/
        └── clean_code_enforcement.yaml
```

## Usage

### For Developers
When working with any code-generating agent:
1. Agent automatically applies clean code principles
2. Code is reviewed for violations before delivery
3. Refactoring suggestions provided proactively
4. Education on principles included in feedback

### For Orchestrators
When delegating to code agents:
1. Specify quality requirements in task
2. Code agents enforce principles automatically
3. Review agents validate compliance
4. Quality gates prevent bad code

## Benefits

### Immediate Benefits
- **Zero Duplication**: No copy-paste code
- **Clear Code**: Self-explanatory naming and structure
- **Proper Design**: SOLID principles followed
- **Testable Code**: Easy to test and verify

### Long-term Benefits
- **Reduced Bugs**: Clean code has fewer defects
- **Faster Development**: Clean code speeds future changes
- **Easier Maintenance**: Code is easy to understand and modify
- **Team Satisfaction**: Developers enjoy working with clean code

## Validation and Monitoring

### Quality Gates
- Linting passes
- Complexity metrics within thresholds
- Test coverage meets minimums
- No principle violations

### Continuous Improvement
- Track violation patterns
- Update standards based on learnings
- Regular review of principles
- Agent feedback incorporation

## Factory Pattern Detection and Refactoring

### Automatic Detection Triggers
The system automatically detects code that should be refactored into factory patterns:

1. **Repeated Object Creation** (3+ instances)
   - Same class instantiated multiple times with different parameters
   - Automatically suggests Simple Factory pattern

2. **Complex Initialization** (4+ setup steps)
   - Object creation followed by multiple configuration calls
   - Suggests Factory with encapsulated setup

3. **Conditional Instantiation** (3+ branches)
   - If-else or switch statements determining object types
   - Recommends Factory Method or Abstract Factory

4. **Parameter Explosion** (5+ parameters)
   - Constructors with too many parameters
   - Suggests Builder Pattern

### Factory Pattern Types

#### Simple Factory
```python
# Before (DRY violation)
user1 = User("Alice", "admin", True, True)
user2 = User("Bob", "user", True, False)
user3 = User("Charlie", "user", False, False)

# After (Factory pattern)
class UserFactory:
    @staticmethod
    def create_admin(name):
        return User(name, "admin", True, True)

    @staticmethod
    def create_user(name, active=True):
        return User(name, "user", active, False)
```

#### Builder Pattern
```python
# Before (Too many parameters)
request = HttpRequest(url, "POST", headers, body, 30, 3, True, True, proxy)

# After (Builder pattern)
request = (HttpRequestBuilder(url)
    .with_method("POST")
    .with_headers(headers)
    .with_body(body)
    .with_timeout(30)
    .build())
```

### Enforcement in Agents

- **Coding Agent**: Detects patterns while coding, auto-generates factories
- **Code Reviewer**: Flags duplicate creation as DRY violation
- **Test Agent**: Creates test data factories and builders
- **Debugger Agent**: Refactors duplicate code during bug fixes

## Examples

### Bad Code (Rejected)
```python
def proc(d):
    r = []
    for i in d:
        if i > 0 and i < 100:
            r.append(i * 2)
    return r
```

### Good Code (Approved)
```python
class MeasurementProcessor:
    MIN_VALID = 0
    MAX_VALID = 100
    SCALE_FACTOR = 2

    def process_valid_measurements(self, measurements: List[int]) -> List[int]:
        """Process measurements within valid range."""
        return [
            self._scale_measurement(measurement)
            for measurement in measurements
            if self._is_valid_measurement(measurement)
        ]

    def _is_valid_measurement(self, measurement: int) -> bool:
        return self.MIN_VALID < measurement < self.MAX_VALID

    def _scale_measurement(self, measurement: int) -> int:
        return measurement * self.SCALE_FACTOR
```

## Conclusion

Clean Code, DRY, and SOLID principles are now fundamental to all code-working agents in the agenthub system. This ensures consistent, high-quality code output that is maintainable, scalable, and professional.