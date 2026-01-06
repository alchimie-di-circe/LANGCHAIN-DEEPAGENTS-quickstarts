# DevContainer Setup for deepagents-quickstarts

This guide describes how to configure a production-ready DevContainer for secure local development with 1Password + direnv integration.

## First-Time Setup

```bash
# Step 1: Authenticate 1Password CLI
op account add

# Step 2: Verify vault access
op vault list

# Step 3: Configure your 1Password vault name
# Create a file named .env in the root of the repository with the following content,
# replacing "Your Vault Name" with your actual 1Password vault name.
# This file is ignored by git.
echo 'export OP_VAULT="Your Vault Name"' > .env

# Step 4: Populate your vault with the required API keys
# - Anthropic: https://console.anthropic.com/account/keys
# - OpenAI: https://platform.openai.com/account/api-keys
# - Tavily: https://app.tavily.com/home
# - LangSmith: https://smith.langchain.com/settings

# Step 5: Open in VS Code
code .
# Select "Reopen in Container" when prompted.

# Step 6: Allow direnv
# Once the container is running, direnv will prompt for permission.
direnv allow
```

## What This Setup Provides

1. **1Password Integration**: Securely manages API keys via 1Password CLI
2. **direnv Support**: Automatically loads environment variables when entering the directory
3. **VS Code DevContainer**: Full development environment with Python, Node.js, and tools
4. **LangSmith Configuration**: Pre-configured for tracing and project management

## Troubleshooting

### OP_VAULT not set
If you see an error about `OP_VAULT` not being set:
1. Make sure you've created the `.env` file in the root directory
2. Verify the vault name matches your actual 1Password vault
3. Run `direnv allow` after creating/updating the `.env` file

### 1Password CLI not authenticated
If direnv fails with an authentication error:
1. Run `op account add` to authenticate
2. Run `direnv allow` again

### direnv not installed
If direnv is not installed in the container:
1. The container will provide instructions in the terminal
2. Install it manually via the 1Password CLI or set environment variables directly in your shell

## Additional Resources

- [1Password CLI Documentation](https://developer.1password.com/docs/cli)
- [direnv Documentation](https://direnv.net)
- [VS Code DevContainers](https://code.visualstudio.com/docs/remote/containers)
