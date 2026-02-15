# Contributing to mtg-sealed-content

Thank you for your interest in contributing to **mtg-sealed-content**! This repository is a community-driven effort to catalog all sealed Magic: The Gathering products and map their contents. Every contribution — whether it's adding a missing product, fixing an error, or improving the tooling — helps hundreds of downstream projects and stores that rely on MTGJSON data.

## Ways to Contribute

### Adding or Correcting Sealed Product Data

This is the most common and impactful way to contribute. If you notice a sealed product is missing or has incorrect contents, you can submit a fix by editing the appropriate YAML file in the `data/` directory.

Each set has its own YAML file (e.g., `data/ONE.yaml` for *Phyrexia: All Will Be One*). Products are defined using the content types documented in the [README](README.md): `card`, `pack`, `deck`, `sealed`, `variable`, and `other`.

### Reporting Issues

If you're not comfortable editing YAML directly, you can still help by [opening an issue](https://github.com/mtgjson/mtg-sealed-content/issues) describing the problem. Please include:

- The product name and set
- What you believe the correct contents should be
- A source or reference for the correct information (e.g., official Wizards of the Coast product pages, unboxing videos, etc.)

### Improving Scripts and Tooling

The `scripts/` directory contains the Python tooling that compiles the YAML data into the final JSON outputs. Bug fixes, performance improvements, and new features are welcome.

### Making a Data Contribution

1. **Fork** the repository and create a new branch for your changes.
2. **Find or create** the appropriate YAML file in `data/` for the set you're working on. File names correspond to set codes (uppercase).
3. **Add or edit** the product entry using the correct content types.
4. **Do not** manually add `uuid` fields — these are calculated automatically by the compiler.
5. **Test** your changes by running the compile scripts to ensure valid output:
   ```bash
   python scripts/contents_validator.py
   ```
6. **Commit** your changes with a clear, descriptive message (see below).
7. **Open a pull request** against the `main` branch.

### YAML Formatting Guidelines

- Use **lowercase set codes** in content entries (e.g., `one`, `2ed`, `akh`).
- Product names should match their official names as closely as possible.
- Include `card_count` when the product contains `pack` or `deck` types if available.
- Make sure to set the `foil` flag where needed or it will silently skipped

### Pull Request Process

1. Ensure your YAML is valid and the compile scripts run without errors.
2. Keep pull requests focused, usually one set per PR is ideal.
3. Provide context in the PR description.
4. A maintainer will review your PR. They may request changes or ask for clarification.
5. Once approved, your contribution will be merged into `main` branch and be available in MTGJSON in the next build.

### Reporting Issues

If you're not comfortable editing YAML directly, you can still help by [opening an issue](https://github.com/mtgjson/mtg-sealed-content/issues) describing the problem. Please include:

- The product name and set
- What you believe the correct contents should be
- A source or reference for the correct information (e.g., official Wizards of the Coast product pages, unboxing videos, etc.)

The MTGJSON team and community are active on [Discord](https://mtgjson.com/discord). It's a great place to:

- Ask questions about the data format or contribution process
- Discuss edge cases for unusual products
- Coordinate with other contributors
- Get help if you're stuck


