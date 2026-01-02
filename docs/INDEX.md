# Documentation Index

Quick reference guide to all documentation in this repository.

## Getting Started

- **New to this project?** Start with `/README.md` (main repository README)
- **Want to run tests quickly?** See `QUICK_START.md`
- **Need command reference?** See `QUICK_REFERENCE.md`

## Documentation Files

### Quick Guides
| File | Purpose | When to Use |
|------|---------|-------------|
| `QUICK_START.md` | Step-by-step setup and first benchmark | First time running tests |
| `QUICK_REFERENCE.md` | Command lookup and quick tips | Need to remember a command |
| `ADAPTIVE_TESTING.md` | Adaptive plateau detection methodology | Understanding test strategies |

### Architecture Documentation
| File | Purpose | When to Use |
|------|---------|-------------|
| `architecture/IMPLEMENTATION_SUMMARY.md` | System architecture overview | Understanding how services work |
| `architecture/SPU_CAMPAIGN_IMPLEMENTATION_COMPARISON.md` | SPU campaign design comparison | Understanding flash sale implementation |
| `architecture/VARIANT_Y_ENHANCEMENT_PLAN.md` | Variant Y optimization plan | Planning performance improvements |

## Version History

See `/versions/` directory for:
- `CONVENTIONS.md` - Sacred policies and conventions (MUST READ)
- `DEPLOYMENT.md` - Deployment procedures
- Dated version files (e.g., `20260102_adaptive_plateau_detection.md`)

## Performance Results

See `/benchmark_results/campaigns/` for:
- Campaign-specific results and analysis
- Raw CSV data for each test
- Performance comparison reports

## Scripts and Tools

- **Scripts:** See `/scripts/README.md` for verification, benchmarking, and reproduction scripts
- **Tools:** See `/tools/README.md` for analysis and reporting utilities

## Key Concepts

### Business Logic
- **SPU (Standard Product Unit):** Product type where campaigns are designed
- **SKU (Stock Keeping Unit):** Specific variant with inventory
- **Flash Sale Campaign:** SPU-level with total_sale_limit, start_time, end_time
- **Dual Validation:** SPU campaign limit AND SKU stock must both pass

### Testing Strategies
- **Fixed Sweep:** Predefined concurrency levels (c=10, 25, 50, 100...)
- **Adaptive Plateau:** Automatic optimal concurrency detection

### Sacred Principles
- **S**elf-verifying
- **A**utomated
- **C**onsistent
- **R**eproducible
- **E**xplicit
- **D**eterministic

## Quick Navigation

```
/home/syracuse/flashsale/
├── README.md                  # ← START HERE
├── docs/                      # ← YOU ARE HERE
│   ├── INDEX.md               # ← This file
│   ├── QUICK_START.md
│   ├── QUICK_REFERENCE.md
│   ├── ADAPTIVE_TESTING.md
│   └── architecture/
│       ├── IMPLEMENTATION_SUMMARY.md
│       ├── SPU_CAMPAIGN_IMPLEMENTATION_COMPARISON.md
│       └── VARIANT_Y_ENHANCEMENT_PLAN.md
├── scripts/
│   ├── verification/          # Health checks
│   ├── benchmarking/          # Performance tests
│   └── reproduction/          # Reproduce specific variants
├── tools/                     # Analysis utilities
├── lib/                       # Reusable test libraries
├── benchmark_results/
│   └── campaigns/             # Test results by campaign
└── versions/                  # Version history and conventions
```

## Common Tasks

| I want to... | Go to... |
|--------------|----------|
| Understand the business requirements | `/README.md` section 1 |
| Run my first benchmark | `QUICK_START.md` |
| Verify services are working | `/scripts/verification/SACRED_VERIFICATION.sh` |
| See performance results | `/benchmark_results/campaigns/[latest]/` |
| Understand test strategies | `ADAPTIVE_TESTING.md` |
| Learn sacred conventions | `/versions/CONVENTIONS.md` |
| Reproduce a variant | `/scripts/reproduction/` |
| Generate performance reports | `/tools/generate_summary_reports.sh` |

---

**Last Updated:** 2026-01-02
**Maintained By:** Syracuse
