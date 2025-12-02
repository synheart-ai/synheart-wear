# Contributing to Synheart Wear

Thank you for your interest in contributing to Synheart Wear! This document provides guidelines for contributing to the Synheart Wear ecosystem.

## 📁 Repository Structure

Synheart Wear is organized as a **multi-repository project**. This repository (`synheart-wear`) serves as the **documentation hub** containing specifications, schemas, and guidelines.

### Platform-Specific Contributions

For code contributions, please contribute to the appropriate platform-specific repository:

| Platform | Repository | Purpose |
|----------|-----------|---------|
| **Flutter/Dart** | [synheart-wear-dart](https://github.com/synheart-ai/synheart-wear-dart) | Cross-platform Flutter SDK |
| **Android (Kotlin)** | [synheart-wear-kotlin](https://github.com/synheart-ai/synheart-wear-kotlin) | Native Android SDK |
| **iOS (Swift)** | [synheart-wear-swift](https://github.com/synheart-ai/synheart-wear-swift) | Native iOS SDK |
| **CLI** | [synheart-wear-cli](https://github.com/synheart-ai/synheart-wear-cli) | Python CLI tool |


## 🤝 Ways to Contribute

### 1. Adding Device Support

To add support for a new wearable device, choose the platform SDK and follow its contributing guide:

- **Flutter/Dart**: [Contributing Guide](https://github.com/synheart-ai/synheart-wear-dart/blob/main/CONTRIBUTING.md)
- **Android/Kotlin**: [Contributing Guide](https://github.com/synheart-ai/synheart-wear-kotlin/blob/main/CONTRIBUTING.md)
- **iOS/Swift**: [Contributing Guide](https://github.com/synheart-ai/synheart-wear-swift/blob/main/CONTRIBUTING.md)

Each platform has specific guidelines for implementing device adapters that conform to the unified data schema.

### 2. Improving Documentation (This Repository)

Documentation improvements are welcome here! You can contribute by:

- Fixing typos or clarifying explanations
- Adding examples or tutorials
- Updating outdated information
- Improving API documentation
- Translating documentation

**Steps:**
1. Fork this repository
2. Create a feature branch (`git checkout -b docs/improve-readme`)
3. Make your changes
4. Submit a pull request with a clear description

### 3. Reporting Issues

Found a bug? Please report it in the appropriate repository:

- **General/Documentation issues**: [This repository](https://github.com/synheart-ai/synheart-wear/issues)
- **Flutter/Dart SDK issues**: [synheart-wear-dart issues](https://github.com/synheart-ai/synheart-wear-dart/issues)
- **Android SDK issues**: [synheart-wear-kotlin issues](https://github.com/synheart-ai/synheart-wear-kotlin/issues)
- **iOS SDK issues**: [synheart-wear-swift issues](https://github.com/synheart-ai/synheart-wear-swift/issues)
- **CLI issues**: [synheart-wear-cli issues](https://github.com/synheart-ai/synheart-wear-cli/issues)


When reporting issues, please include:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Platform and version information
- Code snippets if applicable

### 4. Proposing New Features

For new features that affect multiple platforms or the overall architecture:

1. Open a [GitHub Discussion](https://github.com/synheart-ai/synheart-wear/discussions) in this repository
2. Describe the feature and its benefits
3. Discuss implementation approaches
4. Get community feedback before starting implementation

## 📊 Unified Data Schema

All device adapters must output data in the **Synheart Data Schema v1.0** format:

```json
{
  "timestamp": "2025-10-20T18:30:00Z",
  "device_id": "device_identifier",
  "source": "adapter_name",
  "metrics": {
    "hr": 72,
    "hrv_rmssd": 45,
    "hrv_sdnn": 62,
    "steps": 1045,
    "calories": 120.4,
    "distance": 2.5
  },
  "meta": {
    "battery": 0.82,
    "firmware_version": "1.0",
    "synced": true
  },
  "rr_ms": [800, 850, 820]
}
```

**See [schema/metrics.schema.json](schema/metrics.schema.json) for the complete specification.**

### Metric Keys

Standard metric keys (all numeric values):

| Key | Description | Unit |
|-----|-------------|------|
| `hr` | Heart rate | BPM |
| `hrv_rmssd` | HRV RMSSD | milliseconds |
| `hrv_sdnn` | HRV SDNN | milliseconds |
| `steps` | Step count | count |
| `calories` | Calories burned | kcal |
| `distance` | Distance traveled | km |
| `stress` | Stress level | 0.0-1.0 |
| `recovery_score` | Recovery score | 0-100 |

## 🪙 Incentives & Recognition

We offer incentives for valuable contributions:

| Contribution Type | Example | Reward |
|-------------------|---------|--------|
| **New Device Adapter** | Garmin, Polar, Muse S | $100 + Public credit |
| **Data Validation** | Signal quality benchmarking | Access to internal datasets |
| **Maintenance** | Bug fixes, upgrades | Badge + Leaderboard points |
| **Open Dataset** | Anonymized HR/HRV data | Contributor recognition |

**To be eligible:**
- Implementation must pass all tests
- Code must follow platform style guides
- Documentation must be included
- Pull request must be approved by maintainers

See our **[Connectors Program](docs/CONNECTORS.md)** for more details.

## 📝 Documentation Guidelines

When contributing documentation:

### Writing Style
- Use clear, concise language
- Write in present tense
- Use active voice
- Include code examples where appropriate
- Keep line length under 120 characters

### Structure
- Use proper markdown headers
- Include table of contents for long documents
- Add code blocks with appropriate language tags
- Use tables for structured comparisons
- Include diagrams for complex concepts

### Examples
Code examples should:
- Be complete and runnable
- Include necessary imports
- Follow platform conventions
- Include comments for clarity
- Show both success and error cases

## 🔍 Review Process

### For Documentation PRs (This Repository)

1. **Automated Checks**: Markdown linting, link validation
2. **Maintainer Review**: Review for accuracy and clarity
3. **Approval**: Merge after approval (usually within 1-3 days)

### For Code PRs (Platform Repositories)

See the specific contributing guide for each platform repository.

## 🧪 Testing Requirements

Documentation changes should:
- [ ] Have no broken links
- [ ] Include updated examples that work
- [ ] Be reviewed for technical accuracy
- [ ] Follow the documentation style guide

Code changes must:
- [ ] Pass all existing tests
- [ ] Include new tests for new features
- [ ] Follow platform code style guidelines
- [ ] Include documentation updates

## 💬 Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect different opinions and experiences
- Report inappropriate behavior to maintainers

### Communication

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community discussions
- **Pull Requests**: Code and documentation contributions

## 🎯 Good First Issues

Looking for a place to start? Look for issues labeled:
- `good first issue` - Great for newcomers
- `documentation` - Documentation improvements
- `help wanted` - Community help needed

## 📚 Resources

- **Main Documentation**: [README.md](README.md)
- **Data Schema**: [schema/metrics.schema.json](schema/metrics.schema.json)
- **RFC Document**: [docs/RFC.md](docs/RFC.md)
- **Connector Interface**: [docs/CONNECTOR_INTERFACE.md](docs/CONNECTOR_INTERFACE.md)
- **Connectors Program**: [docs/CONNECTORS.md](docs/CONNECTORS.md)

## 📄 License

By contributing to Synheart Wear, you agree that your contributions will be licensed under the MIT License.

---

## Quick Links

### Platform Contributing Guides
- [Flutter/Dart SDK](https://github.com/synheart-ai/synheart-wear-dart/blob/main/CONTRIBUTING.md)
- [Android/Kotlin SDK](https://github.com/synheart-ai/synheart-wear-kotlin/blob/main/CONTRIBUTING.md)
- [iOS/Swift SDK](https://github.com/synheart-ai/synheart-wear-swift/blob/main/CONTRIBUTING.md)

### Community
- [GitHub Discussions](https://github.com/synheart-ai/synheart-wear/discussions)
- [Issues](https://github.com/synheart-ai/synheart-wear/issues)
- [Synheart AI](https://synheart.ai)

---

Thank you for contributing to Synheart Wear! 🎉

**Made with ❤️ by the Synheart AI Team**

*Technology with a heartbeat.*
