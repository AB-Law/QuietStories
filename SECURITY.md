# Security Policy

## Supported Versions

Use this section to tell people about which versions of your project are currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| 0.x     | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it privately to maintain user safety while a fix is developed.

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please send your report to [security@quietstories.dev] with the following information:

- A description of the vulnerability
- Steps to reproduce the issue
- Affected versions
- Potential impact
- Any suggested fixes (if you have them)

You can expect:
- An acknowledgment of your report within 48 hours
- A more detailed response within 7 days indicating the next steps in handling your report
- Regular updates on the progress of fixing the vulnerability
- Credit for discovering the vulnerability (unless you prefer to remain anonymous)

## Security Best Practices

When running QuietStories in production:

1. **Environment Variables**: Never commit sensitive data like API keys or database credentials to version control
2. **HTTPS Only**: Always use HTTPS in production environments
3. **API Keys**: Store API keys securely and rotate them regularly
4. **Database Security**: Use strong passwords and consider encrypting sensitive data at rest
5. **Dependencies**: Keep all dependencies updated to avoid known vulnerabilities
6. **Access Control**: Implement proper authentication and authorization for your API endpoints

## Additional Resources

- [OWASP Top Ten](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://docs.python.org/3/library/security.html)
- [Node.js Security Best Practices](https://nodejs.org/en/docs/guides/security/)
