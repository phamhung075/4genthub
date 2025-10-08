# Avoiding MRO (Method Resolution Order) Conflicts - Best Practices Guide

**Document Version:** 1.0
**Last Updated:** 2025-10-08
**Author:** code-reviewer-agent
**Audience:** Backend Developers, Architecture Team

---

## Table of Contents

1. [Introduction](#introduction)
2. [Understanding MRO](#understanding-mro)
3. [Common Patterns That Cause Conflicts](#common-patterns-that-cause-conflicts)
4. [Best Practices](#best-practices)
5. [Safe Multiple Inheritance Patterns](#safe-multiple-inheritance-patterns)
6. [Code Review Checklist](#code-review-checklist)
7. [Debugging MRO Issues](#debugging-mro-issues)
8. [Examples and Anti-Patterns](#examples-and-anti-patterns)

---

## Introduction

### What is MRO?

**Method Resolution Order (MRO)** is the order in which Python searches for methods and attributes in a class hierarchy. When you have multiple inheritance, Python uses the **C3 Linearization algorithm** to determine which parent class's method to call.

### Why Should You Care?

**Incorrect MRO can cause:**
- ✅ `AttributeError` at runtime
- ✅ Methods called with wrong signatures
- ✅ Unexpected behavior
- ✅ Hard-to-debug errors

**Real Example from Our Codebase:**
```python
class ORMAgentRepository(
    BaseTimestampRepository[Agent],
    BaseUserScopedRepository
):
    pass

# This crashes:
repo.update(agent_id, name="new_name")
# AttributeError: 'str' object has no attribute 'touch'
```

---

## Understanding MRO

### How Python Resolves Methods

Python uses **C3 Linearization** to create a linear order from the inheritance graph:

1. **Start with the class itself**
2. **Add parents in left-to-right order**
3. **Recursively add parent's parents**
4. **Ensure no class appears before its parents**

### Checking MRO

```python
# View MRO for any class
print(ORMAgentRepository.__mro__)

# Output:
(<class 'ORMAgentRepository'>,
 <class 'BaseTimestampRepository'>,
 <class 'BaseORMRepository'>,
 <class 'BaseUserScopedRepository'>,
 <class 'object'>)
```

### MRO Rules

1. **Child before parent** - Subclasses are searched before parent classes
2. **Left to right** - Left parents are searched before right parents
3. **No duplicates** - Each class appears only once in MRO
4. **Consistent ordering** - Parent order must be consistent across hierarchy

---

## Common Patterns That Cause Conflicts

### ❌ Anti-Pattern 1: Conflicting Method Signatures

**Problem:**
```python
class BaseA:
    def update(self, id: str, **kwargs):
        """Update by ID."""
        pass

class BaseB:
    def update(self, entity: Entity, **kwargs):
        """Update by entity object."""
        pass

# WRONG - Method signatures conflict
class MyClass(BaseA, BaseB):
    pass

# Which update() is called?
obj.update(some_id, name="test")  # Calls BaseA.update()
obj.update(some_entity, name="test")  # Also calls BaseA.update() - WRONG!
```

**Why It Fails:**
- BaseA's `update()` comes first in MRO
- BaseB's `update()` is **never accessible**
- Calling with entity object crashes (str has no `.touch()` method)

---

### ❌ Anti-Pattern 2: Diamond Inheritance

**Problem:**
```python
class Base:
    def method(self): pass

class Left(Base):
    def method(self): pass

class Right(Base):
    def method(self): pass

# WRONG - Diamond inheritance without careful design
class Bottom(Left, Right):
    pass

# Which method() is called? Left.method() or Right.method()?
```

**Why It's Confusing:**
- Multiple paths to the same base class
- Unclear which method wins
- Changes in parent order break behavior

---

### ❌ Anti-Pattern 3: Implicit Method Shadowing

**Problem:**
```python
class RepositoryBase:
    def save(self, data: dict):
        """Save raw data."""
        pass

class EntityRepository(RepositoryBase):
    def save(self, entity: Entity):
        """Save entity object."""
        pass

# WRONG - save() signatures are incompatible
class MyRepository(EntityRepository, SomeMixin):
    # Which save() is accessible?
    pass
```

---

## Best Practices

### ✅ Rule 1: Prefer Composition Over Inheritance

**Instead of:**
```python
# AVOID
class MyRepository(
    BaseTimestampRepository,
    BaseUserScopedRepository,
    CacheInvalidationMixin
):
    pass
```

**Use:**
```python
# BETTER
class MyRepository(BaseTimestampRepository):
    def __init__(self, session, user_id):
        super().__init__(model_class)
        self._user_scope = UserScopeHelper(session, user_id)
        self._cache = CacheManager()

    def get_by_id(self, id: str):
        result = super().get_by_id(id)
        self._user_scope.validate_ownership(result)
        return self._cache.cache(result)
```

**Benefits:**
- ✅ No MRO conflicts
- ✅ Clear ownership
- ✅ Easy to test
- ✅ Flexible composition

---

### ✅ Rule 2: Use Mixins Carefully

**Mixin Requirements:**
1. **No constructor** (or super().__init__() only)
2. **No instance variables**
3. **No method conflicts** with other mixins
4. **Clear naming** (e.g., `LoggingMixin`, `CacheMixin`)

**Good Mixin Example:**
```python
class CacheInvalidationMixin:
    """Mixin for cache invalidation - no conflicts."""

    def invalidate_cache(self, key: str):
        """Invalidate cache entry."""
        # Safe - unique method name
        cache.delete(key)

    def invalidate_all_caches(self):
        """Invalidate all related caches."""
        # Safe - unique method name
        cache.clear()
```

**Bad Mixin Example:**
```python
class BadMixin:
    def __init__(self):
        # BAD - Mixins shouldn't have constructors
        self.data = {}

    def save(self, entity):
        # BAD - Common method name, will conflict
        pass
```

---

### ✅ Rule 3: Explicit Method Delegation

When you MUST use multiple inheritance with conflicts, **explicitly delegate**:

```python
class MyRepository(
    BaseTimestampRepository[Agent],
    BaseUserScopedRepository
):
    # EXPLICIT OVERRIDE - Makes intent clear
    def update(self, id: str, **kwargs):
        """Update by ID - delegates to BaseORMRepository."""
        return BaseORMRepository.update(self, id, **kwargs)

    def update_entity(self, entity: Agent, **kwargs):
        """Update by entity - delegates to BaseTimestampRepository."""
        return BaseTimestampRepository.update(self, entity, **kwargs)
```

**Benefits:**
- ✅ Both methods are accessible
- ✅ Clear which method does what
- ✅ Self-documenting code

---

### ✅ Rule 4: Single Responsibility Principle

**Each base class should have ONE responsibility:**

```python
# GOOD - Clear responsibilities
class BaseORMRepository:
    """LOW-LEVEL: Database operations only."""
    def _db_create(self, **kwargs): pass
    def _db_update(self, id, **kwargs): pass
    def _db_delete(self, id): pass

class BaseTimestampRepository(BaseORMRepository):
    """HIGH-LEVEL: Entity management with timestamps."""
    def save(self, entity): pass
    def update_entity(self, entity): pass

class BaseUserScopedRepository:
    """CROSS-CUTTING: User isolation only."""
    def with_user(self, user_id): pass
    def validate_ownership(self, entity): pass
```

---

### ✅ Rule 5: Interface Segregation

**Don't inherit from "god classes":**

```python
# BAD - Too many responsibilities
class MegaRepository:
    def create(self): pass
    def update(self): pass
    def delete(self): pass
    def cache(self): pass
    def log(self): pass
    def validate(self): pass
    def notify(self): pass

# GOOD - Focused interfaces
class CreateRepository:
    def create(self, entity): pass

class UpdateRepository:
    def update(self, entity): pass

class CachedRepository(CreateRepository, UpdateRepository):
    # Small, focused interfaces - less conflict risk
    pass
```

---

## Safe Multiple Inheritance Patterns

### Pattern 1: Mixin-Only Multiple Inheritance

```python
class LoggingMixin:
    """Adds logging to any class."""
    def log(self, message: str):
        logger.info(message)

class CachingMixin:
    """Adds caching to any class."""
    def cache_get(self, key: str):
        return cache.get(key)

class MyRepository(BaseRepository, LoggingMixin, CachingMixin):
    """Safe - mixins have no method conflicts."""
    pass
```

**Safe because:**
- ✅ Mixins have unique method names
- ✅ No overlapping signatures
- ✅ Clear separation of concerns

---

### Pattern 2: Protocol-Based Inheritance

```python
from typing import Protocol

class Saveable(Protocol):
    """Protocol for saveable entities."""
    def save(self) -> bool: ...

class Repository:
    """Concrete implementation."""
    def save_entity(self, entity: Saveable) -> bool:
        """Uses protocol instead of inheritance."""
        return entity.save()
```

**Safe because:**
- ✅ No actual inheritance
- ✅ Duck typing instead
- ✅ No MRO conflicts possible

---

### Pattern 3: Strategy Pattern

```python
class UserScopingStrategy:
    """Strategy for user scoping."""
    def filter(self, query, user_id): pass

class TimestampStrategy:
    """Strategy for timestamp management."""
    def update_timestamps(self, entity): pass

class Repository:
    """Uses composition with strategies."""
    def __init__(self):
        self.user_scoping = UserScopingStrategy()
        self.timestamping = TimestampStrategy()

    def save(self, entity):
        """Composes strategies instead of inheriting."""
        self.timestamping.update_timestamps(entity)
        # Save logic here
```

---

## Code Review Checklist

### Before Merging Code

```markdown
## Multiple Inheritance Checks

- [ ] Does this class inherit from more than one concrete class?
- [ ] Have I checked the MRO with `ClassName.__mro__`?
- [ ] Do any parent classes have methods with the same name?
- [ ] Are all method signatures compatible?
- [ ] Have I added tests for method resolution?
- [ ] Could this be composition instead of inheritance?
- [ ] Are all mixins truly mixins (no state, no __init__)?
- [ ] Is the inheritance hierarchy documented?

## Method Conflict Checks

- [ ] Are there any methods with the same name in different parents?
- [ ] Do those methods have compatible signatures?
- [ ] Have I explicitly overridden conflicting methods?
- [ ] Is it clear which method should be called?
- [ ] Have I added docstrings explaining the resolution?

## Testing Requirements

- [ ] Test calling each inherited method directly
- [ ] Test that MRO is what I expect (assert on __mro__)
- [ ] Test with different parameter types
- [ ] Test edge cases (None, empty, invalid data)
```

---

## Debugging MRO Issues

### Step 1: Print the MRO

```python
# Add to your repository __init__ or test
print(f"MRO for {self.__class__.__name__}:")
for i, cls in enumerate(self.__class__.__mro__):
    print(f"  {i}: {cls.__name__}")
```

### Step 2: Check Method Sources

```python
import inspect

# Which class does this method come from?
method = MyRepository.update
print(f"Method defined in: {method.__qualname__}")
print(f"Method signature: {inspect.signature(method)}")
```

### Step 3: Call Specific Parent Method

```python
# If MRO is wrong, explicitly call the right parent
class MyRepository(BaseA, BaseB):
    def update(self, *args, **kwargs):
        # Force calling BaseB's method
        return BaseB.update(self, *args, **kwargs)
```

### Step 4: Visualize Inheritance

```python
# Use tools to visualize
pip install pylint
pylint --generate-rcfile > .pylintrc
# Enable inheritance diagrams
```

---

## Examples and Anti-Patterns

### ❌ Example 1: The Agent Repository Bug

**What Happened:**
```python
class ORMAgentRepository(
    BaseTimestampRepository[Agent],
    BaseUserScopedRepository,
    AgentRepository
):
    pass

# Developer wrote:
repo.update(agent.id, name="new_name")

# MRO resolved to:
BaseTimestampRepository.update(entity=agent.id, name="new_name")
# entity=agent.id is a string, not an Agent object

# Crashed with:
AttributeError: 'str' object has no attribute 'touch'
```

**Root Cause:**
- BaseTimestampRepository has `update(entity, **kwargs)`
- Developer expected `update(id, **kwargs)` from BaseORMRepository
- MRO chose BaseTimestampRepository (comes first)

**Fix:**
```python
class ORMAgentRepository(
    BaseTimestampRepository[Agent],
    BaseUserScopedRepository,
    AgentRepository
):
    # EXPLICIT OVERRIDE
    def update(self, id: str, **kwargs):
        """Update by ID."""
        return BaseORMRepository.update(self, id, **kwargs)

    def update_entity(self, entity: Agent, **kwargs):
        """Update by entity."""
        return BaseTimestampRepository.update(self, entity, **kwargs)
```

---

### ✅ Example 2: Clean Composition

**Instead of Multiple Inheritance:**
```python
class AgentRepository:
    def __init__(self, session, user_id):
        # Composition - no MRO issues
        self._orm = BaseORMRepository(Agent)
        self._timestamps = TimestampManager()
        self._user_scope = UserScopeManager(session, user_id)

    def update(self, id: str, **kwargs):
        """Clear method - no ambiguity."""
        entity = self._orm.get_by_id(id)
        self._user_scope.validate_ownership(entity)

        for key, value in kwargs.items():
            setattr(entity, key, value)

        self._timestamps.update(entity)
        return self._orm.save(entity)
```

**Benefits:**
- ✅ No MRO conflicts
- ✅ Clear data flow
- ✅ Easy to test each component
- ✅ Can swap implementations

---

### ✅ Example 3: Safe Mixin Use

```python
class AuditMixin:
    """Safe mixin - no method conflicts."""

    def log_action(self, action: str, entity_id: str):
        """Unique method name - won't conflict."""
        logger.info(f"{action} on {entity_id}")

class CacheMixin:
    """Safe mixin - no method conflicts."""

    def cache_invalidate(self, key: str):
        """Unique method name - won't conflict."""
        cache.delete(key)

class AgentRepository(
    BaseTimestampRepository,
    AuditMixin,
    CacheMixin
):
    """Safe - mixins have unique methods."""

    def update(self, id: str, **kwargs):
        result = super().update(id, **kwargs)
        self.log_action("update", id)  # From AuditMixin
        self.cache_invalidate(f"agent:{id}")  # From CacheMixin
        return result
```

---

## Quick Reference

### Decision Tree: Should I Use Multiple Inheritance?

```
┌─────────────────────────────────────┐
│ Do I need multiple inheritance?     │
└─────────────┬───────────────────────┘
              │
              ▼
       ┌──────────────┐
       │ Can I use    │
       │ composition? │
       └──────┬───────┘
              │
     ┌────────┴────────┐
     │                 │
    YES               NO
     │                 │
     ▼                 ▼
  USE IT!    ┌─────────────────┐
             │ Are all parents │
             │ just mixins?    │
             └────────┬─────────┘
                      │
             ┌────────┴────────┐
             │                 │
            YES               NO
             │                 │
             ▼                 ▼
        SAFE TO USE    ┌──────────────────┐
                       │ Do methods have  │
                       │ same name?       │
                       └────────┬─────────┘
                                │
                       ┌────────┴────────┐
                       │                 │
                      YES               NO
                       │                 │
                       ▼                 ▼
              ⚠️ DANGEROUS       PROBABLY SAFE
              Override           Test thoroughly!
              explicitly!
```

### Common Error Messages and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `AttributeError: 'str' object has no attribute 'touch'` | Wrong method signature from MRO | Override method explicitly |
| `TypeError: update() takes 2 positional arguments but 3 were given` | Signature mismatch | Check MRO, fix signatures |
| `TypeError: Cannot create a consistent method resolution order (MRO)` | Conflicting parent order | Reorder parents or remove one |

---

## Summary

**Golden Rules:**
1. **Prefer composition over inheritance**
2. **Use mixins only for cross-cutting concerns**
3. **Explicitly override conflicting methods**
4. **Always check MRO before merging**
5. **Test method resolution thoroughly**

**Red Flags:**
- 🚩 More than 2 parents with concrete methods
- 🚩 Methods with same name, different signatures
- 🚩 Diamond inheritance without careful design
- 🚩 Unclear which parent method should be called

**Remember:**
> "Inheritance should mean IS-A, not USES-A"
> "When in doubt, compose it out"

---

**Document Maintained By:** Backend Architecture Team
**Review Frequency:** Quarterly or after MRO incidents
**Feedback:** Submit PR to update this guide
