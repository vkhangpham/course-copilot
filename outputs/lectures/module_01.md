# Module 1 · Foundations of Database Systems

This stub is generated while the TA CodeAct loop is under construction.
Each real run will include citations, examples, and student prompts.

_Current dataset focus: Foundations & Modeling_

## Learning Objectives & Assessments
- Learning objective: Explain the relational model, SQL, and why normalization matters.
- Assessment strategy: short concept quizzes plus a transactional lab on locking and recovery.

## Concept Coverage
We revisit relational algebra and SQL before contrasting concurrency control mechanisms, recovery logs, and distributed systems such as Spanner and resilient NewSQL engines.

## Worked Example
Consider a banking workload: a transaction debits one account and credits another. We trace how two-phase locking prevents lost updates while recovery replays committed entries.

## Review Questions
1. Why does strict two-phase locking guarantee serializability?
2. Which SQL query would expose a partial failure in the example above?

## Suggested Practice
- Exercise · Quiz-Sql-Group (medium): Given Relations Orders(order_id, customer_id, total) and Customers(customer_id, region), write SQL to return each region with average order total for customers placing >=5 orders.
- Exercise · Quiz-Normalization (medium): A table Campaign(channel, campaign_id, region, manager, region_manager_email) exhibits repeated manager info. Show how to reach BCNF and justify the functional dependencies you used.

## Reading Starter Pack
- ARIES: A Transaction Recovery Method Supporting Fine-Granularity Locking and Partial Rollbacks Using Write-Ahead Logging – Physiological logging, steal/no-force
- Amazon Aurora: An On-Demand Relational Database Service – Log-based replication + HTAP

## Background Explainers
### Distributed & Replicated Systems (distributed)
Scale-out topologies, consensus, and geo-distributed SQL.
Citations: bigtable-2006, spanner-2012

## Sources & Citations
- Codd (1970) formalized the relational model and relational algebra [`codd-1970`].
- System R (1976) demonstrated cost-based SQL optimization and transactions [`system-r-1976`].
- Postgres, ARIES, and Spanner extend these ideas to modern distributed databases.

### Spotlight Concept
Foundations & Modeling (foundations): Canonical abstractions (ER diagrams, relations, relational algebra) that separate logical from physical design.

### Timeline Anchor
1970 – Codd publishes the relational model (related concept `relational_model`)
Formalizes data independence and relational algebra.

### Citation Preview
A Relational Model of Data for Large Shared Data Banks (1970) — CACM
