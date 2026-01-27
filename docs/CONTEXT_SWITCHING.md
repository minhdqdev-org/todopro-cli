# Context Switching in TodoPro CLI

The TodoPro CLI supports multiple contexts (environments), allowing you to easily switch between different TodoPro deployments like development, staging, and production.

## Overview

Contexts allow you to:
- Maintain separate authentication tokens for each environment
- Switch between dev, staging, and production with a single command
- Add custom environments (e.g., test, qa, local)
- Keep environment configuration organized and secure

## Default Contexts

The CLI comes with three pre-configured contexts:

| Context   | Endpoint                                | Description                    |
|-----------|-----------------------------------------|--------------------------------|
| **dev**   | `http://localhost:8000/api`             | Local development environment  |
| **staging** | `https://staging.todopro.minhdq.dev/api` | Staging environment           |
| **prod**  | `https://todopro.minhdq.dev/api`        | Production environment         |

## Commands

### List All Contexts

View all available contexts and see which one is currently active:

```bash
todopro config get-contexts
```

Output:
```
Available Contexts
┏━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Current ┃ Name    ┃ Endpoint                               ┃ Description                   ┃
┡━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ *       │ prod    │ https://todopro.minhdq.dev/api         │ Production environment        │
│         │ staging │ https://staging.todopro.minhdq.dev/api │ Staging environment           │
│         │ dev     │ http://localhost:8000/api              │ Local development environment │
└─────────┴─────────┴────────────────────────────────────────┴───────────────────────────────┘
```

### Show Current Context

See which context is currently active:

```bash
todopro config current-context
```

Output:
```
Current Context
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property    ┃ Value                         ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Name        │ prod                          │
│ Endpoint    │ https://todopro.minhdq.dev/api│
│ Description │ Production environment        │
└─────────────┴───────────────────────────────┘
```

### Switch Context

Change the active context:

```bash
todopro config use-context dev
```

Output:
```
Success: Switched to context 'dev'
Endpoint: http://localhost:8000/api
Description: Local development environment
```

### Add or Update a Context

Create a new context or update an existing one:

```bash
todopro config set-context test \
  --endpoint="http://test.local:8000/api" \
  --description="Test environment"
```

### Delete a Context

Remove a context (you cannot delete the currently active context):

```bash
todopro config delete-context test
```

Or skip confirmation with `-y`:

```bash
todopro config delete-context test -y
```

## Authentication Per Context

Each context maintains its own authentication credentials. When you log in, the credentials are saved for the current context:

```bash
# Switch to dev context
todopro config use-context dev

# Login - credentials saved for dev context
todopro login

# Switch to prod context
todopro config use-context prod

# Login - credentials saved for prod context (separate from dev)
todopro login
```

### Credential Storage

Credentials are stored securely in:
```
~/.local/share/todopro-cli/{profile}.{context}.credentials.json
```

For example:
- Dev credentials: `default.dev.credentials.json`
- Prod credentials: `default.prod.credentials.json`
- Staging credentials: `default.staging.credentials.json`

File permissions are set to `0600` (readable only by owner) for security.

## Workflow Examples

### Local Development Workflow

```bash
# Start with dev context
todopro config use-context dev

# Login to local backend
todopro login

# Work with local tasks
todopro tasks list
todopro tasks create "Test feature X"

# When ready, switch to staging
todopro config use-context staging
todopro login
```

### Production Operations

```bash
# Switch to production
todopro config use-context prod

# Login with prod credentials
todopro login

# View production tasks
todopro tasks list
todopro today
```

### Multi-Environment Testing

```bash
# Create QA environment
todopro config set-context qa \
  --endpoint="https://qa.todopro.minhdq.dev/api" \
  --description="QA environment"

# Use it
todopro config use-context qa
todopro login
```

## Configuration File

Context configuration is stored in:
```
~/.config/todopro-cli/default.json
```

Example structure:
```json
{
  "api": {
    "endpoint": "https://todopro.minhdq.dev/api",
    "timeout": 30,
    "retry": 3
  },
  "current_context": "prod",
  "contexts": {
    "dev": {
      "name": "dev",
      "endpoint": "http://localhost:8000/api",
      "description": "Local development environment"
    },
    "staging": {
      "name": "staging",
      "endpoint": "https://staging.todopro.minhdq.dev/api",
      "description": "Staging environment"
    },
    "prod": {
      "name": "prod",
      "endpoint": "https://todopro.minhdq.dev/api",
      "description": "Production environment"
    }
  }
}
```

## Best Practices

1. **Separate Credentials**: Never share credentials between environments. Use separate accounts for dev/staging/prod.

2. **Context Naming**: Use descriptive names for custom contexts (e.g., `qa`, `demo`, `client-staging`).

3. **Verify Context**: Always check the current context before making changes:
   ```bash
   todopro config current-context
   ```

4. **Read-Only Production**: Consider using read-only credentials for production context to prevent accidental modifications.

5. **Scripts**: Use explicit context switching in automation scripts:
   ```bash
   #!/bin/bash
   todopro config use-context staging
   todopro tasks list --output=json > staging-tasks.json
   ```

## Troubleshooting

### Context Not Switching

If the API endpoint doesn't seem to change after switching contexts, check the current config:

```bash
todopro config get api.endpoint
todopro config current-context
```

### Authentication Errors After Switching

Each context requires separate authentication. If you get authentication errors:

```bash
todopro config use-context dev
todopro login
```

### Lost Credentials

If credentials are lost or corrupted, simply login again:

```bash
todopro logout
todopro login
```

## Comparison with kubectl

The TodoPro CLI context system is inspired by `kubectl` context management:

| kubectl | todopro | Description |
|---------|---------|-------------|
| `kubectl config get-contexts` | `todopro config get-contexts` | List contexts |
| `kubectl config current-context` | `todopro config current-context` | Show current context |
| `kubectl config use-context` | `todopro config use-context` | Switch context |
| `kubectl config set-context` | `todopro config set-context` | Create/update context |
| `kubectl config delete-context` | `todopro config delete-context` | Delete context |

## See Also

- [TodoPro CLI README](README.md)
- [Configuration Management](README.md#-configuration)
- [Authentication Guide](README.md#quick-start)
