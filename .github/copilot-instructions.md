# GitHub Copilot & VS Code AI Instructions for Tanvelo

## Autonomous Memory Protocol

When working on this repository with the Tanvelo MCP Server connected:

1. **Pre-flight Retrieval**: Before responding to any prompt or generating code, invoke `get_context(query="...")` from Tanvelo to retrieve relevant architectural facts, database configurations, and developer preferences.
2. **Autonomous Fact Storage**: Whenever durable technical decisions, stack choices, or preferences are established in conversation, call `save_memory(content="...")` in the background without waiting for user commands.
