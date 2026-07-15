---
title: Beginner Guide
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Beginner Guide

This set of documents is intended for contributors participating in project development for the first time. Its goal is to guide you from scratch through the complete development path: preparing the environment, understanding pipelines, adding a feature, reusing common nodes, and reading existing tasks.

It does not cover every field or every detail of the conventions. Instead, it explains the learning sequence and what you should accomplish at each step. For specific practices, go to the corresponding page and follow the [Project Conventions](/en/dev/project-conventions/) during development.

## 1. Development Preparation

First complete repository cloning, dependency installation, resource checks, and documentation site startup. See [Quick Start](/en/dev/quick-start) for the preparation process.

Before writing code, read these conventions:

- [Pipeline Conventions](/en/dev/project-conventions/pipeline)
- [PR Conventions](/en/dev/project-conventions/pull-request)
- [AI Usage Conventions](/en/dev/project-conventions/ai-usage)

## 2. Pipeline Basics

Understand the basic components of a pipeline: nodes, recognition, actions, transitions, and log descriptions. For details, see [Pipeline Basics](/en/dev/beginner-guide/pipeline-basics).

After reading it, you should be able to understand why a node executes, where it goes after execution, and why clicks must be based on visual recognition.

## 3. Add a Feature

When adding a feature, first break the requirement down into "task entry, page entry, state confirmation, business action, and final return." For details, see [Adding a Feature](/en/dev/beginner-guide/new-feature).

That page explains which files a new task usually needs to modify and how to divide the feature into reviewable pipeline nodes.

## 4. Use Common Nodes

The project already provides a set of common UI, state, and action nodes. Before adding a feature, first determine whether they can be reused. For details, see [Common Nodes and Universal Transitions](/en/dev/beginner-guide/common-nodes).

That page explains how to use `AnySceneEnter_MainMenu`, `Status_In_MainMenu`, `SceneDo_*`, and `UI_*` nodes.

## 5. Read the StartGame Example

Finally, read the [StartGame Development Workflow](/en/dev/beginner-guide/start-game). `StartGame` covers launching the application, waiting for loading, handling updates, clicking start, handling login prompts, and confirming the main screen, making it a suitable first complete pipeline example.
