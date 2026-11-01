# Public plugin directory: next publication step

Status: planning only. A GitHub release is not publication in the public OpenAI Plugin Directory.

ADT Repair is a skills-only plugin that calls local programs. Its portable manifest declares `extensions.com.openai.requires_local_executor: true`. It has no MCP server or lifecycle hooks. It therefore follows the skills-only desktop-execution submission path; do not add a local MCP server just to package this workflow.

After the GitHub release:

1. Test installation with a pilot team and at least one additional book family. Retain evidence of repair quality, state preservation, accessibility limitations and measured usage.
2. Confirm the submitting OpenAI organization/project, authorized submitter and verified individual/business publishing identity.
3. Prepare final publisher metadata, an icon, useful screenshots, a public privacy explanation and support links. Do not invent legal terms or claim certification. A repository privacy explanation may need a dedicated URL/form depending on the portal's checks.
4. Open https://platform.openai.com/plugins and upload the standalone plugin ZIP with `plugin.json` at the archive root.
5. Review metadata and skill scan findings, revise the source package, upload again and resolve required errors.
6. Complete any applicable reviewer information, then submit for review. Approval is a separate step; after approval the publisher chooses when to make it public.

A skills-only desktop package follows the standard submission process. If the portal rejects the local-executor field, confirm submission access with OpenAI. The separate local-MCP path is limited to approved partners; it is not a prerequisite for this package because v1 has no MCP server.

Keep the source repository and versioned ZIPs as the maintained source. Skill/metadata updates require new package uploads. A later MCP architecture would need separate planning: the current documentation says adding an MCP server to an existing skills-only plugin is not supported.

Official documentation checked on 2026-11-01:

- Packaging and GitHub/local marketplaces: https://developers.openai.com/plugins/build/plugins
- Desktop execution: https://developers.openai.com/plugins/deploy/desktop-only
- Submission and publishing: https://developers.openai.com/plugins/deploy/submission

These requirements can change; re-check them at submission time.
