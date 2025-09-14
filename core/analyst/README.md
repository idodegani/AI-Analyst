# AI Analyst Module - Agentic Data Analysis System

## Overview

This module implements an AI-powered data analyst system that enables natural language querying of property management data. The system employs an agentic workflow using LangGraph for sophisticated state management and multi-step reasoning, ensuring secure, accurate, and contextual responses to analytical questions about reservations and reviews data.

## Architecture Design

The architecture follows Domain-Driven Design principles with clear separation of concerns across multiple layers:

### Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   API Layer (Django)                     │
│                 External Interface                       │
├─────────────────────────────────────────────────────────┤
│                  AIAnalystDjango                         │
│              Main Orchestrator (analyst.py)              │
├─────────────────────────────────────────────────────────┤
│     Workflow Engine               │    Configuration     │
│   LangGraph State Machine         │    Management        │
│     (workflow.py)                 │    (config.py)       │
├───────────────────────┬───────────┴──────────────────────┤
│   Business Services   │          External Providers      │
│   - QueryService      │          - DuckDBProvider        │
│   - ResponseService   │          - OpenAIProvider        │
│   (services.py)       │          (providers.py)          │
├───────────────────────┴──────────────────────────────────┤
│   Domain Models       │          Security Layer          │
│   Data Structures     │          SQL Validation          │
│   (models.py)         │          (validators.py)         │
└───────────────────────┴──────────────────────────────────┘
```

### Component Responsibilities

#### Core Domain Layer

**models.py** - Defines the core business entities and data structures
- Implements Pydantic models for robust data validation
- Ensures type safety across the entire application
- Provides domain-specific validation rules (e.g., SQL security checks)
- Maintains conversation state and context tracking

**config.py** - Centralized configuration management
- Eliminates hardcoded values throughout the codebase
- Provides environment-specific settings
- Enables easy testing with different configurations
- Supports feature toggles and behavioral modifications

#### Infrastructure Layer

**providers.py** - Abstractions for external dependencies
- Implements the Dependency Inversion Principle
- Allows swapping implementations without changing business logic
- Provides interfaces for database operations and LLM interactions
- Enables mock implementations for testing

**validators.py** - Security-first validation layer
- Implements comprehensive SQL injection prevention
- Enforces read-only operations at multiple levels
- Provides pattern-based threat detection
- Returns detailed error messages for debugging

#### Application Services Layer

**services.py** - Core business logic implementation
- Orchestrates interactions between different components
- Implements complex business rules and workflows
- Handles error enhancement and context extraction
- Maintains separation between technical and business concerns

**workflow.py** - Agentic workflow orchestration
- Implements state machine pattern using LangGraph
- Manages complex multi-step processes
- Provides retry logic and error recovery
- Enables observable and debuggable execution flow

**prompts.py** - LLM interaction templates
- Centralizes prompt engineering logic
- Ensures consistent LLM interactions
- Implements few-shot learning examples
- Handles context injection for follow-up questions

## Agentic Workflow Implementation

The system implements a sophisticated agentic workflow that mimics human analytical reasoning:

### State Machine Design

```
User Question
     │
     ▼
┌─────────────┐
│ Generate SQL│ ◄─────────────┐
└─────┬───────┘               │
      │                       │
      ▼                       │ Retry with
┌─────────────┐               │ Context
│  Validate   │               │
│  Security   │               │
└─────┬───────┘               │
      │                       │
      ├─► Pass                │
      │                       │
      ▼                       │
┌─────────────┐               │
│   Execute   │               │
│    Query    │               │
└─────┬───────┘               │
      │                       │
      ├─► Success             │
      │                       │
      ▼                       │
┌─────────────┐         ┌─────┴───────┐
│   Format    │         │   Handle    │
│  Response   │ ◄───────┤    Error    │
└─────┬───────┘         └─────────────┘
      │
      ▼
Natural Language
    Answer
```

### Workflow Characteristics

1. **Context Preservation**: The system maintains conversation history and context, enabling follow-up questions and contextual understanding.

2. **Intelligent Retry Logic**: When queries fail, the system analyzes the error and attempts to reformulate the SQL with additional context.

3. **Multi-Stage Validation**: Security checks occur at multiple points - during SQL generation, before execution, and at runtime.

4. **Adaptive Response Generation**: The LLM formats responses based on the query type, data structure, and user context.

## Security Architecture

The security implementation follows defense-in-depth principles:

### Multi-Layer Protection

1. **Input Validation** (models.py)
   - Pydantic validators sanitize SQL at the model level
   - Removes potentially dangerous patterns before processing
   - Enforces whitelist of allowed SQL operations

2. **Security Validation** (validators.py)
   - Secondary validation layer with specialized security focus
   - Pattern-based detection of injection attempts
   - Comprehensive logging of security events

3. **Runtime Protection** (workflow.py)
   - Final security check before query execution
   - Validates query starts with allowed operations
   - Prevents bypass attempts through workflow manipulation

4. **Error Handling** (services.py)
   - Sanitizes error messages to prevent information leakage
   - Provides helpful hints without exposing system internals
   - Maintains security while improving user experience

## Code Quality Principles

### SOLID Principles Implementation

**Single Responsibility Principle**
- Each class has one reason to change
- Clear separation between SQL generation, execution, and formatting
- Distinct modules for different aspects of the system

**Open/Closed Principle**
- New providers can be added without modifying existing code
- Extensible through interfaces rather than modifications
- Configuration-driven behavior changes

**Liskov Substitution Principle**
- All provider implementations are interchangeable
- Abstract base classes define clear contracts
- Consistent behavior across different implementations

**Interface Segregation Principle**
- Focused interfaces for specific capabilities
- No forced implementation of unnecessary methods
- Clean abstractions for database and LLM operations

**Dependency Inversion Principle**
- High-level modules depend on abstractions
- Concrete implementations injected at runtime
- Testable through mock implementations

### Design Patterns

**Singleton Pattern** (analyst.py)
- Ensures single instance of the analyst
- Manages resource-intensive connections efficiently
- Maintains consistent state across requests

**Factory Pattern** (get_analyst function)
- Provides clean interface for instance creation
- Hides complexity of initialization
- Enables future enhancement without API changes

**State Machine Pattern** (workflow.py)
- Clear representation of workflow states
- Predictable state transitions
- Observable execution flow

**Strategy Pattern** (providers.py)
- Interchangeable algorithms for data access and LLM interaction
- Runtime selection of implementations
- Easy testing with mock strategies

## Meeting Assignment Requirements

### Natural Language Interface
The system successfully translates natural language questions into SQL queries, handling complex temporal expressions (Q1, H1, etc.) and contextual follow-ups.

### Data Analysis Capabilities
Supports all required analytical operations including aggregations, filtering, joining, and complex date-based queries across reservations and reviews data.

### Security First
Comprehensive security implementation prevents SQL injection and ensures data integrity through multiple validation layers.

### Scalable Architecture
The modular design allows easy extension for new data sources, different LLMs, or additional analytical capabilities without disrupting existing functionality.

### Production Ready
Includes proper error handling, logging, configuration management, and session handling for real-world deployment scenarios.

## Usage and Integration

The module integrates seamlessly with Django through a simple interface:

```python
from core.analyst import get_analyst

# Initialize the analyst (singleton pattern ensures efficiency)
analyst = get_analyst()

# Process analytical questions
response = await analyst.ask(
    question="What is the average guest count for Q1 2025?",
    session_id="user-session-123"
)

# Access structured response
print(response.text_answer)  # Human-readable answer
print(response.sql_query)    # Generated SQL for transparency
print(response.status)       # Success/Error status
```

The system maintains backward compatibility while providing a clean, extensible architecture for future enhancements.
