# OmniDesk AI — Product Vision & Technical Project Brief

> **Working name:** OmniDesk AI  
> **Product type:** Personal, project-based multi-LLM workspace  
> **Status:** Concept / Planning  
> **Primary goal:** Let a user continue the same project conversation across different AI models without repeatedly explaining the project or losing work context.

---

## 1. Product Vision

OmniDesk AI is a single workspace where a user can create projects and chat with multiple AI providers—such as OpenAI, Google Gemini, and Anthropic Claude—through one consistent interface.

The key idea is **not merely displaying several AI answers side by side**. The essential feature is **shared project context with seamless model switching**.

Example:

1. The user creates a project named `SentinelGate AI`.
2. The user starts a conversation with an OpenAI model.
3. The model helps design the backend, reviews code, and discusses implementation decisions.
4. If the selected model reaches its provider-side usage limit, becomes unavailable, or is no longer the preferred model, the user switches to Claude or Gemini.
5. The newly selected model receives the relevant project instructions, prior conversation, decisions, task progress, and files.
6. The user continues from the current point instead of starting over.

The product should make the experience feel like **one continuous project conversation**, even though different model providers may answer at different times.

## 2. The Problem Being Solved

The user currently works across separate AI products and accounts. This creates friction:

- Conversations are split across different websites and accounts.
- The user has to copy and paste previous answers between AI tools.
- Each AI may lack the history and decisions made with another AI.
- When a model reaches a usage limit, switching tools can interrupt the workflow.
- Project context, implementation status, and previous decisions are difficult to keep synchronized.
- The user must repeatedly explain the same project and its current state.

OmniDesk AI should centralize these items in one project workspace.

## 3. Core Product Principles

1. **One project source of truth:** project instructions, decisions, tasks, files, and conversation history belong to the workspace—not to an individual model.
2. **Provider-independent history:** messages are stored in the application's database.
3. **Seamless model switching:** a user can change the active model at any point and continue with relevant context.
4. **Explicit context management:** the app decides what context to send to a model and makes that behavior understandable.
5. **Secure credentials:** provider API keys are stored securely on the server and never exposed in frontend code.
6. **Cost awareness:** show provider/model usage and estimated costs when reliable usage/pricing data is available.
7. **Honest limits:** do not claim unlimited usage. Provider quotas, rate limits, context windows, and billing still apply.
8. **No consumer-session scraping:** do not automate or reuse browser cookies, passwords, or consumer website sessions to bypass provider limits. Use official APIs and supported authentication methods.

## 4. Target User Workflow

### 4.1 Create a project

The user creates a project with:

- Project name
- Description
- Goals
- Instructions / preferred response style
- Optional files and reference documents
- Optional technology stack
- Optional project status

Example project: `SentinelGate AI — Runtime Security Gateway for Autonomous AI Agents`.

### 4.2 Start a conversation

The user opens a project chat, chooses a provider/model, and sends a message.

The application stores the user message and the assistant response in a provider-independent conversation database.

### 4.3 Switch models without restarting

The user changes the selected model from (for example) GPT to Claude or Gemini.

Before making the next provider request, the backend builds a context package containing the relevant information:

- Project description and instructions
- Key project decisions
- Current goals and active task
- Recent conversation messages
- Relevant earlier messages or summaries
- Relevant file excerpts or retrieved documents
- Current implementation/progress notes

The new model should receive enough context to continue accurately. It must not be told that it has access to information that was not actually supplied.

### 4.4 Continue after a limit or error

If a provider returns a rate-limit, quota, billing, or availability error:

- Show a clear error category to the user.
- Preserve the user's unsent message and all existing history.
- Offer available configured alternative models.
- Let the user switch manually.
- Optionally suggest a fallback, but do not silently switch models without the user's consent unless the user explicitly enables that setting.
- Do not imply that switching providers bypasses all limits; each provider has independent policies and quotas.

### 4.5 Optional multi-model mode

The user may send one prompt to multiple selected models and see responses separately.

The user can then:
- Compare answers.
- Ask one model to critique another model's response.
- Ask a selected model to synthesize the responses into one result.

This is a secondary feature. The first priority is reliable shared context and model switching.

## 5. Required Features

### MVP — Must Have

1. User authentication for the OmniDesk AI application.
2. Project creation, editing, listing, and deletion.
3. Project-specific instructions and persistent context.
4. One unified chat interface.
5. Provider/model selector.
6. Initial provider adapters for:
   - OpenAI API
   - Google Gemini API
   - Anthropic Claude API
7. Provider-independent message storage.
8. Seamless manual model switching within the same conversation.
9. Context builder that packages relevant project and conversation information.
10. Conversation history and message timestamps.
11. Secure server-side API-key configuration.
12. Clear error handling for invalid keys, quota/rate limits, network errors, and provider failures.

### Next Phase

1. Send one prompt to multiple models.
2. Side-by-side answer comparison.
3. Ask one model to review another model's answer.
4. Final synthesis of multiple answers.
5. File upload and project document library.
6. Search/retrieval over project files (RAG) when justified.
7. Context summaries and token-aware history selection.
8. Usage and cost dashboard.
9. Export conversations and project summaries.

### Later / Optional

1. Local model support through a local inference server such as Ollama.
2. Custom model/provider adapters.
3. Tool calling and controlled agent workflows.
4. Git repository integration.
5. Project task board and implementation checklist.
6. Team collaboration, only if there is a real need.

Do not implement every future feature in the MVP.

## 6. Shared Context: The Most Important Technical Requirement

Different AI providers do not automatically share memory or conversation history. OmniDesk AI must implement this in its own backend.

### 6.1 Store canonical data

Keep canonical records for:

- Projects
- Project instructions
- Conversations
- Messages
- Attachments / files
- Project decisions
- Tasks and progress
- Context summaries
- Provider and model configuration
- Usage records (where available)

Do not rely on any provider's chat history as the only copy of project history.

### 6.2 Context package

For each model request, build a context package from the application's database. A sensible order is:

1. System-level application instructions.
2. Project-specific instructions and description.
3. Current project status and active task.
4. Persistent project decisions and constraints.
5. Relevant file excerpts or retrieved information.
6. A compact summary of older conversation history.
7. Recent messages in chronological order.
8. The user's new message.

The exact provider message format will differ, so each provider adapter must convert the canonical context into the provider's required request format.

### 6.3 Context window management

Do not blindly send the entire conversation forever.

Implement a token-aware context strategy:

- Keep recent messages in full.
- Summarize older messages.
- Preserve important decisions, constraints, file references, and unfinished tasks.
- Retrieve only relevant file sections.
- Respect each model's context-window limits.
- If context must be shortened, prioritize project instructions, decisions, active task, and recent messages.
- Store summaries with timestamps/version information so they can be updated and audited.

A summary is a convenience, not a replacement for the original stored messages. The original history should remain available in the database.

### 6.4 Context transparency

The UI should provide a way to inspect what information is being sent to the selected model (at least a simple “Context included” panel). Avoid silently omitting important project facts.

## 7. Suggested Architecture

Use a modular architecture with clear boundaries. Do not over-engineer.

### Frontend

Suggested option:
- Next.js / React
- TypeScript
- Tailwind CSS
- A clean responsive chat workspace

Main screens:
- Login / account setup
- Project dashboard
- Project chat
- Model/provider settings
- Usage page
- Project files and context page

### Backend

Suggested option:
- Python with FastAPI (or Django REST Framework if there is a strong reason to use Django)
- Provider adapter layer
- Conversation/context service
- Authentication and authorization
- File processing service (later phase)

The backend is responsible for provider API calls, context assembly, key security, and persistence.

### Database

Suggested option:
- PostgreSQL

Possible core entities:
- `users`
- `projects`
- `project_instructions`
- `conversations`
- `messages`
- `project_decisions`
- `project_tasks`
- `context_summaries`
- `attachments`
- `provider_configs`
- `usage_records`

Use migrations and clear relationships. Avoid premature abstraction.

### Provider adapter pattern

Create a common internal interface, conceptually:

```python
class ModelProvider:
    async def generate(self, messages, model, settings):
        raise NotImplementedError
```

Implement separate adapters for OpenAI, Gemini, and Claude. The interface is illustrative; adapt it to the chosen SDKs and their current APIs.

Provider adapters should normalize:
- Text responses
- Streaming responses (if supported)
- Usage metadata (if returned)
- Provider request IDs (if returned)
- Errors and rate-limit information

Do not assume every provider supports identical features or returns identical usage data.

### High-level request flow

```text
User sends message
       |
       v
Frontend -> Backend API
       |
       v
Authenticate user and authorize project access
       |
       v
Save user message
       |
       v
Load project instructions, decisions, tasks, files and history
       |
       v
Build token-aware context package
       |
       v
Selected provider adapter
       |
       v
OpenAI / Gemini / Claude API
       |
       v
Normalize response and usage metadata
       |
       v
Save assistant response and provider/model metadata
       |
       v
Return response to frontend
```

## 8. Security and Privacy Requirements

- Never put provider API keys in browser JavaScript or public frontend environment variables.
- Keep secrets in server-side environment variables or a proper secret manager.
- Encrypt stored user-provided provider keys at rest if the product supports per-user keys.
- Never log raw API keys, passwords, session cookies, or authorization headers.
- Validate project ownership on every project/conversation/file endpoint.
- Apply rate limiting and request-size limits.
- Sanitize uploaded files and restrict allowed file types and sizes.
- Use HTTPS in production.
- Provide a way to remove stored provider credentials and user data.
- Do not collect or store consumer website passwords or cookies.
- Follow each provider's API terms, usage policies, and data-handling requirements.

## 9. Cost and Usage Expectations

This application is an orchestration workspace, not a way to convert consumer subscriptions into unlimited API access.

Important distinctions:

- ChatGPT consumer subscriptions and OpenAI API billing are separate.
- Claude consumer subscriptions and Anthropic API access/billing are separate.
- Gemini API availability, free quotas, and paid usage depend on the applicable model, account, region, and current Google terms.
- Provider quotas, rate limits, model availability, and pricing can change.

Therefore:

- Start with one or two providers.
- Use free API tiers only where currently available and eligible.
- Allow the user to disable expensive models.
- Show usage and cost only when supported by reliable provider metadata and current pricing.
- Never invent a cost estimate.
- Add optional spending limits and confirmation before expensive multi-model requests.

## 10. Recommended MVP Technology Plan

A practical starting stack:

| Layer | Suggested technology |
|---|---|
| Frontend | Next.js + TypeScript |
| UI | Tailwind CSS |
| Backend | FastAPI |
| Database | PostgreSQL |
| ORM / migrations | SQLAlchemy + Alembic |
| Authentication | Secure session or token-based auth |
| AI providers | Official OpenAI, Gemini, Anthropic APIs |
| Local development | Docker Compose (optional) |
| Local models | Ollama integration in a later phase |

These are recommendations, not mandatory choices. Before implementation, inspect the existing repository and follow its established stack if a project already exists.

## 11. Development Phases and Acceptance Criteria

### Phase 0 — Repository inspection and planning

- Inspect the current repository before changing files.
- Identify existing framework, dependencies, conventions, and unfinished work.
- Produce a concise implementation plan.
- Do not delete or recreate existing work without approval.

### Phase 1 — Working foundation

Acceptance criteria:
- User can sign in to the application.
- User can create and open a project.
- User can create a conversation inside a project.
- Messages persist after refresh.
- Project instructions are saved and editable.

### Phase 2 — One provider end-to-end

Acceptance criteria:
- One configured provider can answer a message through the backend.
- The API key is never exposed to the frontend.
- User and assistant messages are stored.
- Provider errors are shown clearly.
- A basic test verifies the flow.

### Phase 3 — Multiple providers and model switching

Acceptance criteria:
- At least two providers work through separate adapters.
- User can switch provider/model in the same conversation.
- The new model receives the shared project context and relevant prior messages.
- The new model can correctly continue a task without asking the user to repeat the project background.
- Provider/model metadata is visible for each assistant response.

### Phase 4 — Context management

Acceptance criteria:
- Older history can be summarized.
- Recent messages remain available.
- Important project decisions and active task are preserved.
- Context assembly respects configured token budgets.
- User can inspect the context summary and correct it.

### Phase 5 — Multi-model collaboration

Acceptance criteria:
- User can select multiple configured models for one prompt.
- Responses are stored separately and labeled by provider/model.
- User can request comparison or synthesis.
- Partial provider failure does not erase successful responses.

### Phase 6 — Files, retrieval, and polish

- Add project files.
- Retrieve relevant file excerpts when needed.
- Add usage display, exports, and improved UI.
- Add local models only after the core workflow is reliable.

## 12. UX Requirements

The interface should feel like a single workspace, not three unrelated chat applications.

Important UI elements:
- Project sidebar
- Conversation list
- Main chat timeline
- Provider/model selector near the message composer
- Clear active model indicator
- “Switch model” action
- Optional “Send to multiple models” action
- Context summary / included context indicator
- Provider error and quota status
- Usage information, where available

When switching models, show a small note such as:

> Continuing this conversation with Claude using the shared project context.

Do not suggest that the new model has native access to another provider's private account or chat history. It only receives the context that this application sends.

## 13. Important Product Decisions

1. The primary workflow is **one conversation, shared history, switchable model**.
2. Multi-model parallel responses are useful but secondary.
3. The application owns the canonical conversation and project memory.
4. Official APIs are the supported integration path.
5. User consent is required before sending project content to a provider.
6. The app must clearly identify which provider/model generated each response.
7. The app must preserve messages even when a provider fails.
8. No automatic usage-limit circumvention.
9. No unnecessary complexity in the first release.

## 14. What Claude Code Should Do

When asked to implement this project:

1. Read this README completely.
2. Inspect the existing repository and report its current structure and stack.
3. Do not assume files, endpoints, or features exist without checking.
4. Do not overwrite or delete existing work without explaining why and obtaining approval.
5. Work in small, testable phases.
6. Avoid over-engineering.
7. Prefer simple, maintainable code and clear module boundaries.
8. Use official provider SDKs/APIs and verify current API documentation before implementing provider-specific calls.
9. Never invent API endpoints, model IDs, pricing, free quotas, or provider capabilities.
10. Add tests for context assembly, model switching, provider failures, and data isolation.
11. After each phase, report changed files, commands run, test results, known limitations, and the next step.
12. Do not claim a feature works unless it has been implemented and tested.

---

## 15. One-Sentence Product Definition

**OmniDesk AI is a project-based multi-AI workspace where OpenAI, Gemini, Claude, and other supported models can continue the same work using one shared, user-controlled project history—so the user can switch models without restarting the conversation.**
