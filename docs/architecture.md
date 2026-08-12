# Architecture

## Overview

Book Illustration Studio follows a two-tier architecture:

- Frontend: React + TypeScript client UI
- Backend: FastAPI API server orchestrating Gemini calls and persistence

## Core Design Constraints

- Maximum 2 adult characters (server-enforced)
- Maximum 1 chapter (server-enforced)
- Book uploaded once to Gemini File API and reused by URI
- No duplicate Gemini calls
- No auto-retry of user actions
- Results must persist across refresh, logout, and server restart

## Pipeline Direction

Two interaction chains are planned:

- Text chain for style, character prompts, and chapter prompts
- Image chain for portraits and chapter illustration

Detailed component and API design will be finalized after decisions 2-6.
