---
name: report_generation
description: Generate structured reports and deliverables from validated information and workspace sources.
---

# Report Generation Skill

## Purpose

Generate clear, structured reports and other deliverables using validated information gathered during the workspace analysis workflow.

## When to Use

Use this skill when the user's request requires:
- creating a report from analyzed documents
- transforming findings into a structured deliverable
- summarizing validated information into a professional document
- organizing analysis results into sections, tables, or recommendations
- producing a final artifact for delivery to the user

## Instructions

1. Review the validated findings and relevant source references before generating the report.
2. Use only information supported by the available source material and analysis results.
3. Preserve important facts, qualifications, uncertainties, and conflicting information.
4. Organize the report according to the user's requested format and purpose.
5. Use clear headings and logical sections.
6. Keep conclusions distinguishable from source-supported facts.
7. Do not fabricate missing information.
8. When recommendations or interpretations are made, clearly distinguish them from factual findings.
9. Generate the deliverable in the workspace's appropriate writable area.
10. Do not modify original source documents.
11. Validate the generated content before marking the deliverable as ready.
12. Respect the authenticated user's workspace boundary.

## Recommended Report Structure

When appropriate, use:

1. Title
2. Executive Summary
3. Source Documents
4. Key Findings
5. Detailed Analysis
6. Important Observations
7. Uncertainties or Conflicts
8. Conclusions
9. Recommendations
10. References

Only include sections that are relevant to the user's request.

## Quality Requirements

A generated report should be:

- accurate
- source-grounded
- logically structured
- readable
- concise where appropriate
- explicit about uncertainty
- consistent with the user's requested format

Before delivery, verify:

- required sections are present
- important findings are represented
- unsupported claims have not been introduced
- source references are preserved where applicable
- the output is written to an allowed workspace location

## Safety Constraints

- Never access files outside the authenticated user's workspace.
- Never use path traversal to access another user's workspace.
- Never overwrite original source documents.
- Never write generated deliverables into the user's input directory.
- Never fabricate facts or citations.
