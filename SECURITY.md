# Security Policy

We take the security of Zen MCP Server seriously. Thank you for helping make the project safe for everyone.

## Supported Versions

We currently support security fixes on the latest release branch. If you require extended support, please open an issue to discuss.

## Reporting a Vulnerability

If you believe you have found a security vulnerability, please do not open a public issue.

Instead, please report it privately:
- Email the maintainers: jajireen1@gmail.com
- Alternatively, open a GitHub Security Advisory (if available) to privately disclose the issue

Please include:
- A detailed description of the vulnerability
- Steps to reproduce
- Affected versions/commit hash
- Any suggested mitigations

We will acknowledge receipt within 72 hours and work with you to assess severity and a remediation timeline. If confirmed, we will publish a patch release and credit reporters (unless you prefer anonymity).

## Scope

This project is an MCP (Model Context Protocol) server that integrates with third-party AI providers. Vulnerabilities in third-party services or model providers are out of scope; however, issues in our integrations, request/response handling, or configuration that could impact security are in scope.

Examples of in-scope issues:
- Remote code execution, injection, or sandbox escapes via tool inputs
- Sensitive data leakage through logs or error messages
- Insecure default configurations
- Authentication/authorization bypass (if any feature requires it)

## Responsible Disclosure

We ask that you:
- Give us a reasonable time to resolve the issue before public disclosure
- Avoid exploiting the vulnerability beyond what is necessary to prove its existence
- Avoid privacy violations, data destruction, or service disruption

