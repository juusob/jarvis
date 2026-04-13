# Setup Instructions

## 1. Create a LiveKit Project

1. Go to [livekit.io](https://livekit.io) and click **Start building**
2. Sign in or create an account
3. Create a new project from the bottom of the dashboard
4. Select **Agent with code**
5. Run the first couple of commands provided by the setup wizard
   > If you want the LiveKit API keys to be automatically filled into your `env.local` file, run the command that generates a template agent

## 2. Set Up the Project Locally

Run the following commands in your terminal:

```bash
uv sync
uv run src/agent.py download-files
```

Then open the project folder in VS Code and copy the following from this repository into your agent file:

- Add `import os` to the imports
- Around line 15, where `from livekit.agents.llm import ...` is — extend it to also import from `azure` and `openai`
- Replace the agent session with the example from this repository

## 3. Configure Environment Variables

Add the following keys to your `env.local` file:

```env
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
```

## 4. Install Azure and OpenAI Plugins

```bash
uv add livekit-plugins-azure
uv add livekit-plugins-openai
```

## 5. Set Up Azure Resources

In the [Azure portal](https://portal.azure.com), go to **Microsoft Foundry** and:

- Deploy a new **LLM model**
- Create a **Speech resource**
- Copy the API keys and endpoints from both resources into your `env.local` file

## 6. Run the Agent in console mode to test if it works

```bash
uv run src/agent.py console
```


## 7. Run the Agent on a server

When you have a frontend setup, you need to have keep your agent running in your server. You can do that by running this command:

```bash
uv run src/agent.py start
```
