# Database Systems

**Duration:** 10 weeks

## Learning Objectives
- Explain the relational model, relational algebra, and SQL basics.
- Design normalized schemas with functional dependencies and normal forms.
- Analyze transaction processing, concurrency control, and recovery strategies.

## Dataset Snapshot
- Concepts: 30
- Papers: 22
- Timeline events: 10
- Quiz items: 10
- Domains: Foundations & Modeling, Execution & Storage, Transactions, Concurrency, and Resilience

## Concept Highlights
- **Foundations & Modeling** (foundations): Canonical abstractions (ER diagrams, relations, relational algebra) that separate logical from physical design.
- **Execution & Storage** (execution): Physical layout, indexing, and query processing internals.
- **Transactions & Concurrency** (concurrency): Guarantees that keep shared data correct when multiple writers/readers interact.

## Timeline Signals
- 1970: Codd publishes the relational model · related concept `relational_model`
  - Formalizes data independence and relational algebra.
- 1970: Codd publishes the relational model · related concept `relational_algebra`
  - Formalizes data independence and relational algebra.
- 1976: System R validates SQL · related concept `sql_language`
  - Demonstrates cost-based optimization + relational performance.

## Citation Spotlight
- A Relational Model of Data for Large Shared Data Banks (1970) — CACM

## Syllabus Snapshot
- Week 1: Relational Thinking & Data Modeling
  - Introduce relational abstractions, relational algebra, and SQL basics.
- Week 2: Schema Quality & Functional Dependencies
  - Use FDs, normal forms, and trade-offs between normalization and denormalization.
- Week 3: Storage Engines, Indexes, and Cost Models
  - Connect physical layout choices to indexing and cost-based optimization.

## Suggested Readings
- ARIES: A Transaction Recovery Method Supporting Fine-Granularity Locking and Partial Rollbacks Using Write-Ahead Logging: Physiological logging, steal/no-force (mohan, (1992), ARIES: A Transaction Recovery Method Supporting Fine-Granularity Locking and Partial Rollbacks Using Write-Ahead Logging, ACM TODS)
- Amazon Aurora: An On-Demand Relational Database Service: Log-based replication + HTAP (verbitski, (2017), Amazon Aurora: An On-Demand Relational Database Service, SIGMOD)
- Highly Available Transactions: Virtues and Limitations: Discusses weak consistency taxonomies (bailis, (2013), Highly Available Transactions: Virtues and Limitations, VLDB)

## Practice Ideas
- Exercise · Quiz-Sql-Group (medium): Given Relations Orders(order_id, customer_id, total) and Customers(customer_id, region), write SQL to return each region with average order total for customers placing >=5 orders.
- Exercise · Quiz-Normalization (medium): A table Campaign(channel, campaign_id, region, manager, region_manager_email) exhibits repeated manager info. Show how to reach BCNF and justify the functional dependencies you used.
- Exercise · Quiz-Locking (hard): Explain how strict two-phase locking prevents dirty reads yet can deadlock. Provide a concrete deadlock example and mitigation.

## Explanation Highlights
- **Distributed & Replicated Systems (distributed)** — Scale-out topologies, consensus, and geo-distributed SQL.
- **Hybrid Transactional/Analytical Processing (HTAP) (htap)** — Systems blending OLTP + analytics via log-based replication and materialized views.
- **CAP Theorem (cap_theorem)** — Under partitions, systems trade availability against consistency.


> Placeholder plan – replace once Teacher RLM is wired.
