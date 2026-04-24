# ShadowIQ Business, Process, and Product Blueprint

## Positioning

ShadowIQ is a managed project delivery platform for research, analytics, and technical work.

It is not a freelancer bidding marketplace.

Clients do not hire unknown individuals directly. They submit a project to ShadowIQ, ShadowIQ reviews the request, and accepted work is assigned internally to a trusted analyst with the right skills. Delivery is supervised through milestones, controlled communication, and structured payment handling.

Core brand promise:

- Confidential intake
- Trusted analyst assignment
- Milestone-based delivery
- Admin-supervised communication
- Protected progress sharing
- Final delivery after payment conditions are met

Suggested positioning line:

ShadowIQ helps clients get serious technical work done through a trusted, managed workflow without needing to know or recruit analysts personally.

## Business Model

### What ShadowIQ sells

ShadowIQ sells managed execution, not access to a marketplace.

Typical work may include:

- Research support
- Statistical analysis
- Data cleaning and reporting
- Software and IT support
- Technical documentation
- Custom internal tools
- Broader tech-enabled delivery projects

### Why clients choose ShadowIQ

Clients choose ShadowIQ because:

- work is screened before acceptance
- the analyst is chosen by skill fit, not by bidding
- payment is structured around milestones
- communication is centralized and traceable
- progress can be shared without releasing the final asset too early
- accepted work is handled with a high-confidence service promise

## Core Process

### 1. Project submission

The client submits a project brief, timeline, requirements, and any attachments.

At intake, ShadowIQ should communicate that submitted projects are reviewed for:

- scope fit
- legality and ethics
- feasibility
- delivery timeline
- pricing suitability

### 2. Review and acceptance

ShadowIQ reviews the project internally.

Possible outcomes:

- Accepted
- Rejected
- Returned for clarification
- Sent into negotiation

If accepted:

- the project is approved for execution
- an analyst is assigned internally
- milestones are defined
- payment options are prepared

If rejected:

- the client is informed clearly
- any eligible refund is processed according to policy

### 3. Analyst assignment

Accepted work is assigned to a trusted analyst selected by ShadowIQ.

This is a major strategic differentiator. The platform should repeatedly communicate:

- clients are not choosing from random freelancers
- analysts are vetted internally
- assignment is based on skill and trust
- ShadowIQ remains accountable for delivery quality

### 4. Milestone setup

Each accepted project should be broken into milestones with:

- title
- description
- amount
- due date
- delivery expectations
- review criteria

Milestones create structure for:

- project tracking
- partial funding
- staged release of work
- payment reconciliation
- dispute handling

### 5. Payment handling

Clients can fund:

- all milestones at once
- selected milestones in stages

Current payment model:

- Paystack supported
- PayPal supported
- PayPal escrow-like hold flow used until admin marks milestone complete for release

Recommended user-facing explanation:

Funds are secured against agreed milestones and are only released according to the project’s completion and approval workflow.

### 6. Project communication

Each project has a dedicated communication channel.

Communication lanes currently implied by your model:

- Client to admin
- Admin to analyst
- Possibly system-generated milestone and payment updates

This makes admin the control layer between client and analyst, which supports confidentiality, consistency, and quality control.

### 7. Progress sharing

Admin can share project progress with the client during execution.

Important messaging note:

Do not promise that users cannot screenshot content. That cannot be guaranteed once content is displayed on a user device.

Safer product language:

- progress previews are view-only
- direct download of protected progress files is restricted until payment conditions are met
- full deliverables are released only when the required milestone or project payment status is complete

### 8. Final delivery

When project conditions are satisfied, the final deliverable can be sent through project chat and downloaded.

This final release should be tied to:

- milestone approval status
- payment completion state
- admin release action

## Website User Flow

### Public flow

1. Visitor lands on homepage
2. Visitor understands ShadowIQ is a managed delivery service, not a bidding marketplace
3. Visitor reviews service categories, trust signals, and process
4. Visitor submits a project or logs in to access an existing one

### Client flow

1. Client submits project
2. Client receives confirmation and status visibility
3. Admin reviews project
4. Client receives acceptance, rejection, or request for clarification
5. If accepted, client sees milestones and payment options
6. Client funds one or more milestones
7. Client monitors project progress through protected updates
8. Client uses project chat for questions and decisions
9. Client receives final deliverables when release conditions are met
10. Client can track receipts, milestone history, and project status

### Admin flow

1. Review submitted project
2. Accept, reject, or negotiate
3. Assign analyst
4. Create milestones
5. Oversee payment status
6. Mediate communication
7. Share progress updates
8. Approve milestone completion
9. Release deliverables or trigger refund/dispute actions

### Analyst flow

1. Receive assigned project
2. Review milestone expectations
3. Communicate with admin
4. Submit progress artifacts and deliverables
5. Mark work ready for review
6. Revise if needed

## Missing Features and Edge Cases

## Policy and workflow gaps

- Clarification state before acceptance is not explicit.
- Dispute workflow needs exact rules, ownership, and timelines.
- Partial refund logic needs to be defined per milestone and per project.
- Cancellation policy needs separate handling for pre-start, mid-project, and near-completion cancellation.
- Revision limits are not defined.
- What counts as milestone completion needs clear evidence requirements.
- There should be a formal rejected-project reason model for internal tracking and client messaging.

## Payment and release gaps

- Paystack and PayPal may not behave identically; the platform needs one consistent user-facing payment policy.
- Multi-milestone payments need safeguards for partial success and partial failure.
- Currency handling, exchange assumptions, and gateway fees need explicit treatment.
- Release rules should prevent a final file from bypassing unpaid milestone restrictions.
- Admin release actions should be audited.
- Failed callbacks, duplicate callbacks, and retry-safe verification logic need to be handled carefully.
- Refund initiation, approval, and settlement states should be visible in the system.

## Communication and trust gaps

- If client-to-analyst direct messaging is blocked by design, the UI should say that clearly.
- Read receipts, delivery confirmations, and attachment audit logs would strengthen accountability.
- A system message layer should record milestone creation, funding, completion, approval, refund, and release events in chat or activity history.

## Progress protection gaps

- “No screenshots” is not technically enforceable in a browser environment.
- Protected previews should use lower-risk delivery methods such as view-only rendering, watermarking, blurred segments, and disabled direct download where practical.
- Preview expiration rules may be useful for sensitive files.

## Operations and scaling gaps

- Admin may become a bottleneck if every client and analyst interaction must pass through one team layer.
- Analyst workload balancing and availability matching are not yet visible in the model.
- SLA targets for response time, review time, and milestone turnaround are not defined.
- Escalation paths for urgent projects or stuck reviews are not defined.

## Compliance and legal gaps

- Terms should distinguish legitimate assistance from prohibited misuse.
- Data rights, client ownership of uploaded materials, and deliverable ownership need explicit wording.
- Refund policy should be reflected consistently across payment, terms, and project UI.
- Privacy language should match the actual data you store and hash.

## Recommended Messaging Principles

- Say “managed by ShadowIQ,” not “find a freelancer.”
- Say “trusted analyst assignment,” not “bid and hire.”
- Say “view-only progress updates,” not “impossible to screenshot.”
- Say “accepted projects are handled under structured delivery and quality oversight,” not “guaranteed” without conditions.

## Revised Landing Copy

### Hero headline

Managed research and technical project delivery you can trust.

### Hero supporting text

Submit your project once. ShadowIQ reviews the work, assigns a trusted analyst internally, structures delivery in milestones, and manages communication and payments from start to finish.

### Trust strip

- No freelancer bidding
- Trusted analyst assignment
- Milestone-based payments

### Why ShadowIQ

- Managed, not marketplace-based
- Confidential intake and controlled communication
- Structured milestones and supervised delivery
- Research, analytics, and coding support in one workflow
- Protected progress sharing before final release
- Clear review, payment, and refund handling

### How it works

1. Submit your brief
2. ShadowIQ reviews and accepts the project
3. A trusted analyst is assigned
4. Milestones are created and funded
5. Progress is shared through protected updates
6. Final deliverables are released when payment conditions are met

### CTA

Start with a confidential project review.

## Product Direction Summary

The strongest version of ShadowIQ is a high-trust managed execution platform for clients who want results without the uncertainty of hiring strangers individually.

That means the product should consistently reinforce these truths:

- ShadowIQ owns the workflow
- analysts are vetted and assigned internally
- communication is structured
- milestones control funding and release
- progress can be reviewed safely
- final delivery follows clear payment and approval rules
