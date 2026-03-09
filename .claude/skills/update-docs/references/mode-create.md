# MODE: CREATE (Generate From Scratch)

When no documentation exists, generate all files from codebase analysis.

## Analysis Steps

1. **Scan project structure** - Identify all folders, key files
2. **Identify tech stack** - Languages, frameworks, dependencies
3. **Find entry points** - main.py, index.js, etc.
4. **Analyze configuration** - .env files, config folders
5. **Identify patterns** - Architecture, design patterns used
6. **Extract purpose** - From code comments, file names, structure
7. **Check for existing docs/** - Don't overwrite existing files

## Create: README.md Template

```markdown
# [Project Name]

[One-line description based on codebase analysis]

## Overview

[2-3 sentences about what this project does]

## Features

- [Feature 1 based on code analysis]
- [Feature 2]
- [Feature 3]

## Quick Start

### Prerequisites
- [Detected requirements]

### Installation
[Based on package.json, requirements.txt, etc.]

### Running
[Based on detected entry points]

## Project Structure

[Based on actual folder analysis]

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| [Layer] | [Tech] | [Purpose] |

## Documentation

- [CLAUDE.md](CLAUDE.md) - Development context and session notes
- [docs/PRD.md](docs/PRD.md) - Full specifications and architecture

## License

[Detected or "See LICENSE file"]
```

## Create: CLAUDE.md Template

**IMPORTANT:** This template contains ALL required sections for `/resume-work` compatibility.

```markdown
# Claude Code Context

> **Purpose:** Maintains context across AI coding sessions.
> **Update:** Run `/update-docs` at the end of each coding session.
> **Resume:** Run `/resume-work` at the start of each coding session.

**Last Updated:** [DATE AND TIME]

---

## Project Overview

**Project:** [Name]
**Repository:** [repo-name]
**Description:** [One-liner]

**Key Documentation:**
- [List all docs/*.md files found or created with descriptions]

---

## Current Status

| Component | Status | Description |
|-----------|--------|-------------|
| [Component 1] | Complete | [Status note] |
| [Component 2] | In Progress | [Status note] |
| [Component 3] | Not Started | [Status note] |

**Legend:** Complete | In Progress | Not Started

---

## Completed

- [x] [Detected completed features]
- [x] [Another completed item]

---

## In Progress

- [ ] [Current work item]
- [ ] [Another in-progress item]

---

## Next Steps

1. **[Priority 1]** - [Description and relevant files]
2. **[Priority 2]** - [Description and relevant files]
3. **[Priority 3]** - [Description and relevant files]

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| [Detected pattern/choice] | [Inferred or documented reason] |
| [Another decision] | [Reason] |

---

## Architecture Summary

[Brief architecture based on code analysis - 2-4 sentences or small diagram]

---

## Known Issues / Blockers

- [ ] [Any detected TODOs, FIXMEs, or issues]
- [ ] [Blockers preventing progress]

*None currently* - if no issues detected

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| [VAR_NAME] | Yes/No | [Purpose] |

[Extracted from .env.example or code analysis]

---

## Session History

### Session 1 - [DATE]
**What happened:**
- Initial documentation created from codebase analysis

**Files created/modified:**
- CLAUDE.md (created)
- README.md (created)
- docs/PRD.md (created)

**Next session should:**
- Review and verify generated documentation
- Add missing context
- Begin development on [suggested area]
```

## Create: docs/PRD.md Template

```markdown
# Project Requirements Document (PRD)
# [Project Name]

**Version:** 1.0
**Last Updated:** [DATE]
**Generated:** From codebase analysis

---

## 1. Overview

[Detailed description based on code analysis]

---

## 2. Architecture

### 2.1 High-Level Architecture

[Mermaid diagram based on detected structure]

### 2.2 Tech Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| [Layer] | [Tech] | [Version from package files] | [Purpose] |

### 2.3 Project Structure

[Detailed folder structure with explanations]

---

## 3. Components

[Document each major component/service detected]

---

## 4. Data Models

[If database/models detected, document them]

---

## 5. API Endpoints

[If API routes detected, document them]

---

## 6. Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| [VAR] | [Yes/No] | [Purpose] |

---

## 7. Dependencies

[From package.json, requirements.txt, etc.]

---

## 8. Development

### Setup
[Detailed setup instructions]

### Testing
[If tests detected, document how to run]

### Deployment
[If deployment config detected, document it]
```
