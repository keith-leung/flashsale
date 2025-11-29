# Development Conventions

## Documentation Style

### Version Documents
- Record only factual results and what was done
- NO "Next Steps" sections
- NO "Room for Improvement" sections
- NO "Phase 1/2/3" planning
- NO future optimization suggestions
- NO "Next: TBD" in version control sections

Version documents are historical records, not project plans.

### Code Comments
- Document what the code does
- Explain non-obvious logic
- NO suggestions for future improvements in comments

## Communication Style

### What NOT to Do
- Don't act as project manager
- Don't suggest next steps unless explicitly asked
- Don't create future roadmaps
- Don't push for additional work
- Don't use over-the-top validation or praise

Work like an employee who completes the current task and stops.

### What TO Do
- Fix bugs when found
- Complete the requested task
- Report what was done
- Answer questions directly

## Code Quality

### Error Handling
- Handle None values properly (e.g., `value or 0` for SQL aggregates)
- Test edge cases (empty datasets, zero records)
- Clean up resources properly (event loops, connections)

### Multi-Worker Considerations
- Use PID-based unique IDs for distributed systems
- Test with multiple workers before deployment
- Avoid hardcoded instance IDs in multi-worker environments

## Cross-Service Compatibility

### JSON Property Naming
- All services must use **snake_case** for JSON properties in API requests/responses
- Python: Uses snake_case natively (FastAPI/Pydantic)
- Java: Configure `spring.jackson.property-naming-strategy: SNAKE_CASE`
- C#: Configure custom `SnakeCaseNamingPolicy` for System.Text.Json
- This ensures load balancer compatibility across all services

### Database Column Naming
- All services must use **snake_case** for database column names
- Python: Uses snake_case natively (SQLAlchemy)
- Java: Configure Hibernate `CamelCaseToUnderscoresNamingStrategy`
- C#: Use `EFCore.NamingConventions` with `.UseSnakeCaseNamingConvention()`

### UUID Storage Format
- Store UUIDs as **CHAR(36)** with hyphens (e.g., `1afdec20-b755-426e-bb72-e2a146447d82`)
- NOT BINARY(16) format
- Java: Configure `hibernate.type.preferred_uuid_jdbc_type: CHAR` and add `columnDefinition = "CHAR(36)"`
- C#: Default Guid mapping to CHAR(36) works correctly
- Python: Store as string with `CHAR(36)` column definition
