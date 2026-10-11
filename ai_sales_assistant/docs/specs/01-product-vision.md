# 01. Product Vision

## Problem

Sales teams spend a lot of time writing similar communications for each customer: first-contact emails, proposals, follow-ups and quick messages. Quality and tone vary between people, and personalisation is often sacrificed for speed.

## Vision

**AI Sales Assistant** is an AI-powered web application that helps sales teams produce professional, consistent and personalised commercial communications in seconds, starting from a few structured details about the customer.

## Target users

- Sales representatives and account managers
- Small and medium-sized sales teams
- Consultants who prepare commercial material for clients

## Value proposition

| Need | How the product addresses it |
| ---- | ---------------------------- |
| Speed | One request produces a ready-to-edit draft |
| Consistency | Shared rules for structure, tone and language |
| Personalisation | Each draft uses the customer's company, industry, product and needs |
| Trust | Facts and figures are never invented; missing details are written around, not left as placeholders |
| Traceability | Every generation is stored with its input and the model that produced it |

## Content types

- Commercial email
- Sales proposal
- Follow-up email
- WhatsApp message
- Customer summary (internal, for the sales team)

## Scope of Version 1

An AI content-generation **REST API** with SQLite persistence and Swagger documentation. The Bootstrap user interface, authentication, customer management, exports, RAG and integrations are planned for later versions (see [Roadmap](10-roadmap.md)).

## Long-term goal

Evolve into a complete enterprise commercial assistant integrated with CRM (Odoo), with knowledge retrieval (RAG), MCP and AI agents.
