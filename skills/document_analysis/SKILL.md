---
name: document_analysis
description: Analyze documents in the user's workspace and extract relevant information for downstream reasoning and reporting.
---

# Document Analysis Skill

## Purpose

Analyze documents available in the user's workspace and produce reliable, structured findings that can be used by downstream agent steps.

## When to Use

Use this skill when the user's request requires:
- understanding one or more workspace documents
- extracting facts or key information
- comparing information across documents
- identifying important sections, findings, or conclusions
- preparing source-grounded information for another workflow

## Instructions

1. Inspect the available workspace files before deciding which documents are relevant.
2. Read only the files necessary to fulfill the user's request.
3. Base findings on the contents of the source documents.
4. Distinguish explicitly between information found in the documents and conclusions inferred from them.
5. Do not invent facts that are not supported by the source material.
6. When multiple documents are used, keep track of which source supports each important finding.
7. Identify uncertainty, missing information, or conflicting information when present.
8. Prefer concise, structured findings that can be passed to downstream agent steps.
9. Do not modify source files while performing analysis.
10. Respect the user's workspace boundary and access only files belonging to the authenticated user.

## Expected Output

Produce structured findings containing, where applicable:

- relevant source files
- key facts
- important observations
- comparisons or relationships
- uncertainties or conflicts
- conclusions supported by the source material

## Safety Constraints

- Never access files outside the authenticated user's workspace.
- Never use path traversal to access another user's workspace.
- Never overwrite or modify source documents during analysis.
- Never fabricate information when the source material is insufficient.
