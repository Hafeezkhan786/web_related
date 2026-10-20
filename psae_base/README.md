# PSAE Base Module

## Purpose

This module is specifically designed for **upgrade and migration purposes only**. It serves as a base dependency for PSAE internal modules during version upgrades.

## Usage

This module should **only** be used in upgrade-specific scenarios:

- Database migrations between Odoo versions
- Upgrade scripts and hooks
- Data transformation during upgrades
- Pre/post-migration operations

## Important Notes

- This is **not** intended for regular production use
- Only install when performing upgrades or migrations
- Contains no business logic or user-facing features
- Exists solely to support the upgrade process

## Technical Information

- **Version**: 19.0.1.0.0
- **License**: OEEL-1
- **Author**: Odoo PS
- **Dependencies**: None
