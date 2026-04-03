# BBSEngine Documentation

Welcome to the BBSEngine documentation handbook. This is the central repository for all technical documentation, specifications, and guides related to the BBSEngine project.

## Quick Navigation

### Getting Started
- [README](README.md) - Project overview and setup

### Documentation
- [Specifications](specs/index.md) - Technical specifications and architecture
- [Database Documentation](database.md) - Database schema and design
- [Module Documentation](module.md) - Module system and architecture
- [Utility Functions](util.md) - Common utilities and helpers

### Guides
- [Listbox Documentation](listbox.md) - Listbox component reference
- [Notify System](README_NOTIFY.md) - Notification system documentation
- [JSON Handling Guide](JSON_HANDLING_GUIDE.md) - JSON serialization and handling

### Architecture & Design
- [CSRF Protection](csrf/README.md) - CSRF security implementation
- [Module System](bbsengine-modules.md) - Module loading and management
- [Architecture Overview](specs/architecture.md) - System architecture

## Documentation Structure

```
handbook/
├── specs/                    # Technical specifications
│   ├── index.md             # Specs overview
│   ├── architecture.md       # Architecture docs
│   ├── console/             # Console subsystem docs
│   ├── database.md          # Database specs
│   └── ...
├── csrf/                    # CSRF implementation docs
├── migrations/              # Database migration docs
├── database.md              # Database reference
├── module.md                # Module system reference
├── util.md                  # Utility functions reference
└── README_NOTIFY.md         # Notify subsystem
```

## Development

### Building Documentation
To regenerate HTML from markdown files:

```bash
cd handbook
python convert_markdown.py .
```

### Contributing
When adding new documentation:
1. Create markdown files in appropriate subdirectories
2. Use clear, descriptive headings
3. Include code examples where relevant
4. Update this index with links to new docs

## Key Topics

### Notification System
- [Notify Overview](README_NOTIFY.md)
- [Input Integration](NOTIFY_INPUT_INTEGRATION.md)
- [Testing Guide](NOTIFY_TESTING.md)
- [Demo Examples](NOTIFY_DEMOS.md)

### Database
- [Database Design](database.md)
- [Upgrade Procedures](../py/src/bbsengine6/sql/upgrades.md)

### Security
- [CSRF Protection](csrf/README.md)
- [CSRF Technical Docs](csrf/CSRF_TECHNICAL_DOCUMENTATION.md)
- [CSRF Audit Report](csrf/ZOID6_CSRF_AUDIT_REPORT.md)

## Viewing Documentation

Documentation is best viewed through the web interface at:
- `https://bbsengine.org/handbook/`

Or you can read the markdown files directly on GitHub:
- Check out the repository at the main bbsengine.org project

## Contact & Support

For questions about documentation or to suggest improvements:
- Check existing documentation and specs
- Review the architecture guides
- Consult the module documentation
