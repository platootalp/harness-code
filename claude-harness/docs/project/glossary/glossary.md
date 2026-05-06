# Glossary

This document defines project-specific terms, acronyms, and abbreviations used throughout the codebase and documentation.

---

## General Terms

| Term | Definition |
|------|------------|
| `[Term]` | `[Clear, concise definition — 1-3 sentences. Avoid jargon where possible; define any technical terms used in the definition.]` |

---

## Acronyms & Abbreviations

| Acronym | Full Form | Definition |
|---------|-----------|------------|
| API | Application Programming Interface | A set of protocols and tools for building software applications and enabling communication between different systems |
| CRUD | Create, Read, Update, Delete | The four basic operations of persistent storage |
| CI/CD | Continuous Integration / Continuous Deployment | Automated processes for building, testing, and deploying code changes |
| ORM | Object-Relational Mapping | A technique for converting between database tables and programming language objects |
| REST | Representational State Transfer | An architectural style for designing networked applications |
| JSON | JavaScript Object Notation | A lightweight data interchange format |
| TLS | Transport Layer Security | A cryptographic protocol for secure communications over a network |
| JWT | JSON Web Token | A compact, URL-safe token format for securely transmitting information between parties |
| SSO | Single Sign-On | An authentication method that allows users to log in once and access multiple systems |
| SLA | Service Level Agreement | A commitment between a service provider and client defining expected service standards |
| OIDC | OpenID Connect | An identity layer built on top of OAuth 2.0 for authentication |
| SAML | Security Assertion Markup Language | An XML-based standard for exchanging authentication and authorization data |
| IdP | Identity Provider | A system that creates, maintains, and manages identity information |
| RBAC | Role-Based Access Control | An access control mechanism that assigns permissions based on roles |
| ABAC | Attribute-Based Access Control | An access control mechanism that evaluates attributes rather than roles |
| IaC | Infrastructure as Code | Managing and provisioning infrastructure through machine-readable definition files |
| EKS | Amazon Elastic Kubernetes Service | A managed Kubernetes service on AWS |
| ECS | Amazon Elastic Container Service | A managed container orchestration service on AWS |
| SNS | Amazon Simple Notification Service | A managed pub/sub messaging service on AWS |
| SQS | Amazon Simple Queue Service | A managed message queuing service on AWS |
| RDS | Amazon Relational Database Service | A managed relational database service on AWS |
| ElastiCache | Amazon ElastiCache | A managed Redis/Memcached service on AWS |
| ASG | Auto Scaling Group | A group of EC2 instances with automatic scaling policies |
| ALB | Application Load Balancer | An AWS load balancer operating at the application layer |
| NLB | Network Load Balancer | An AWS load balancer operating at the transport layer |
| WAF | Web Application Firewall | A firewall that protects web applications from common attacks |
| DDoS | Distributed Denial of Service | An attack that overwhelms a service with traffic from multiple sources |
| CSP | Content Security Policy | An HTTP header that helps prevent XSS and data injection attacks |
| CORS | Cross-Origin Resource Sharing | A mechanism that allows resources to be requested from domains outside the origin domain |
| HMAC | Hash-Based Message Authentication Code | A cryptographic hash function used for message authentication |
| idempotent | Idempotent | An operation that produces the same result regardless of how many times it is applied |

---

## Project-Specific Terms

<!-- TODO: Define all project-specific terminology. -->

| Term | Definition |
|------|------------|
| `[Term]` | `[Definition — what does this term mean in the context of this project specifically?]` |

### Example Project-Specific Terms

| Term | Definition |
|------|------------|
| `workspace` | A shared environment where team members collaborate on projects. Contains its own users, resources, and billing. |
| `resource` | Any managed entity in the system — a database, storage bucket, function, etc. Identified by a unique resource ID prefixed with `res_`. |
| `integration` | A connection between this platform and an external service (e.g., GitHub, Slack, AWS). |
| `deployment` | A specific version of application code deployed to an environment. Identified by a unique deployment ID prefixed with `dep_`. |
| `environment` | A deployment target (development, staging, production). Each environment has isolated resources and configuration. |
| `webhook` | An HTTP callback that notifies your system when events occur in the platform. |
| `event` | A record of something that happened in the system (e.g., `user.created`, `deployment.succeeded`). |
| `pipeline` | A CI/CD pipeline that automates building, testing, and deploying code. |
| `secret` | A sensitive value (password, API key, token) stored securely and injected into the runtime environment. |
| `quota` | A limit on resource usage (e.g., maximum workspaces per account, requests per minute). |
| `audit log` | A chronological record of all actions taken in the system, including who did what and when. |

---

## Architecture Terms

| Term | Definition |
|------|------------|
| `service` | An individual deployable unit that performs a specific function. May contain one or more modules. |
| `module` | A logical grouping of related code within a service (e.g., an `auth` module, `billing` module). |
| `microservice` | An architectural approach where the application is composed of small, independently deployable services. |
| `monolith` | A traditional architecture where all functionality is in a single deployable unit. |
| `sidecar` | A helper process that runs alongside a main container to provide additional functionality (e.g., logging, metrics). |
| `gateway` | A single entry point for all client requests, handling routing, authentication, and rate limiting. |
| `bff` | Backend for Frontend — an API layer tailored to a specific client's needs. |
| `event-driven` | An architecture where services communicate by emitting and consuming events. |
| `CQRS` | Command Query Responsibility Segregation — separating read and write operations into different models. |
| `event sourcing` | Storing state changes as a sequence of events rather than just current state. |
| `saga` | A pattern for managing distributed transactions across multiple services. |
| `circuit breaker` | A design pattern that prevents cascading failures by failing fast when a downstream service is unhealthy. |
| `bulkhead` | An isolation pattern that prevents failures in one part of the system from affecting others. |
| `dead letter queue` | A queue for messages that could not be processed successfully, for later inspection/retry. |

---

## Operational Terms

| Term | Definition |
|------|------------|
| `p95 latency` | The 95th percentile response time — 95% of requests are faster than this. |
| `p99 latency` | The 99th percentile response time — 99% of requests are faster than this. |
| `availability` | The percentage of time a service is operational and accessible. |
| `MTTR` | Mean Time To Recovery — the average time to restore service after an incident. |
| `MTBF` | Mean Time Between Failures — the average time between service disruptions. |
| `SLO` | Service Level Objective — a target level of service performance agreed upon with stakeholders. |
| `SLI` | Service Level Indicator — a metric used to measure whether the SLO is being met. |
| `runbook` | A document that describes the steps to perform a routine operational task or respond to an incident. |
| `postmortem` | A document reviewing a significant incident — what happened, why, impact, and action items. |
| `change advisory board` | A group that reviews and approves changes to production systems. |
| `blue-green deployment` | A deployment strategy using two identical environments, switching traffic between them. |
| `canary deployment` | A strategy where a new version is deployed to a small subset of users before full rollout. |
| `feature flag` | A toggle that enables or disables a feature without deploying new code. |
| `dark launch` | Releasing a feature to a subset of users without publicizing it to test performance. |
| `horizontal scaling` | Adding more machines/instances to handle load. |
| `vertical scaling` | Adding more resources (CPU, RAM) to existing machines. |
| `sharding` | Partitioning data across multiple database instances. |
| `replication` | Copying data across multiple database instances for redundancy and read scaling. |

---

## Security Terms

| Term | Definition |
|------|------------|
| `OWASP` | Open Web Application Security Project — a community focused on improving software security. |
| `XSS` | Cross-Site Scripting — an attack where malicious scripts are injected into web pages. |
| `CSRF` | Cross-Site Request Forgery — an attack that tricks a user into performing unintended actions. |
| `SQL injection` | An attack that inserts malicious SQL code into queries. |
| `mitigation` | Actions taken to reduce the severity or impact of a vulnerability or attack. |
| `threat model` | A systematic analysis of potential threats and vulnerabilities in a system. |
| `attack surface` | The sum of all possible entry points for an attacker. |
| `zero trust` | A security model that requires strict verification for every access request, regardless of source. |
| `least privilege` | The principle of granting only the minimum permissions necessary. |
| `defense in depth` | Using multiple layers of security controls. |
| `secret scanning` | Automated detection of secrets accidentally committed to source code. |
| `SBOM` | Software Bill of Materials — a list of components and dependencies in a software product. |

---

## External Services & Tools

| Term | Definition |
|------|------------|
| Datadog | A monitoring and observability platform providing logs, metrics, and traces. |
| PagerDuty | An incident management platform for alerting on-call engineers. |
| LaunchDarkly | A feature flag management platform. |
| Sentry | An error tracking and performance monitoring platform. |
| Doppler | A secrets management platform (alternative to AWS Secrets Manager). |
| 1Password | A password manager with team sharing capabilities. |
| Figma | A collaborative design tool. |
| Notion | A documentation and wiki platform. |
| Linear | A project management and issue tracking tool. |
| GitHub Actions | A CI/CD platform integrated with GitHub repositories. |
| Terraform | An infrastructure as code tool for provisioning cloud resources. |
| Helm | A package manager for Kubernetes. |
| Istio | A service mesh providing traffic management, security, and observability. |
| Envoy | A proxy and communication bus for service mesh architectures. |
| Prometheus | A metrics collection and alerting system. |
| Grafana | A visualization platform for metrics and logs. |
| Jaeger | A distributed tracing system. |
| ArgoCD | A GitOps continuous delivery tool for Kubernetes. |
