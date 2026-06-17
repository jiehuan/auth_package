Here's the full interview guide with expected strong answers:

---

## Technical Deep Dives

### Full Stack & APIs

**Q: Walk me through how you'd design a RESTful vs GraphQL API — when do you choose one over the other?**

> **Strong Answer:** REST is better for simple, resource-based CRUD operations with caching needs (HTTP caching works naturally). GraphQL shines when clients have varying data needs — mobile vs web fetching different fields — avoiding over/under-fetching. I'd choose GraphQL for complex, interconnected data graphs (e.g., social feeds) and REST for simpler microservices or public APIs where caching matters.

**Q: How have you handled authentication/authorization in Node.js/Express?**

> **Strong Answer:** JWT-based auth with access + refresh token rotation. Store refresh tokens in httpOnly cookies (not localStorage) to prevent XSS. Use middleware for role-based access control (RBAC). For microservices, validate tokens at an API gateway level rather than each service. Would mention libraries like `passport.js`, `jsonwebtoken`, or OAuth2 flows.

**Q: Describe BFF architecture — when is it the right pattern?**

> **Strong Answer:** BFF means having a dedicated backend per client type (mobile BFF, web BFF) that aggregates downstream microservices and shapes responses for that specific client. Right pattern when mobile needs lighter payloads than web, or when different clients have very different UX requirements. Avoids bloating a single API with client-specific logic.

---

### Database & Performance

**Q: You claim 50% faster queries — what optimizations did you apply?**

> **Strong Answer:** Should mention: compound indexes on frequently queried fields, covered queries (index contains all needed fields), avoiding `$where` and full collection scans, using `explain()` to analyze query plans, aggregation pipeline optimizations ($match/$project early), connection pooling, and for PostgreSQL — EXPLAIN ANALYZE, partial indexes, proper JOIN strategies.

> **Red Flag:** Vague answer like "I added indexes" with no mention of how they measured before/after.

**Q: How do you design MongoDB schemas when you have relational data needs?**

> **Strong Answer:** Two strategies — embedding vs referencing. Embed when data is always accessed together and has a 1:few relationship (e.g., user + addresses). Reference when data is large, frequently updated independently, or shared across documents (e.g., products referenced by many orders). Avoid unbounded arrays. Use `$lookup` sparingly as it's expensive — denormalize strategically for read-heavy workloads.

**Q: Explain your indexing strategy for a high-traffic application.**

> **Strong Answer:** Analyze query patterns first using slow query logs. Create compound indexes matching query field order (ESR rule — Equality, Sort, Range). Use sparse indexes for optional fields, TTL indexes for expiring data, text indexes for search. Monitor index usage with `$indexStats` and drop unused indexes since they slow writes.

---

### DevOps/Cloud

**Q: Walk me through a CI/CD pipeline you built with Jenkins/Bitbucket end-to-end.**

> **Strong Answer:** Bitbucket push triggers Jenkins webhook → Jenkins pulls code → runs unit/integration tests → builds Docker image → pushes to ECR/DockerHub → deploys to staging (Kubernetes via Helm charts or kubectl) → smoke tests → manual approval gate → deploy to production. Secrets managed via Jenkins credentials store or AWS Secrets Manager. Rollback via previous Docker image tag.

**Q: How do you handle secrets across AWS EC2 + Kubernetes deployments?**

> **Strong Answer:** Never hardcode secrets. Use AWS Secrets Manager or Parameter Store, injected at runtime via IAM roles (instance profiles for EC2, IRSA for Kubernetes). In Kubernetes, use Secrets objects (base64 encoded, ideally sealed with Sealed Secrets or External Secrets Operator syncing from AWS). Rotate secrets automatically and audit access via CloudTrail.

---

### AI/LLM (Probe Carefully)

**Q: Describe a specific LangChain pipeline you built.**

> **Strong Answer:** Should describe: document loading → text splitting strategy (chunk size, overlap based on content type) → embedding model choice (OpenAI, HuggingFace) → vector store (Pinecone, Chroma, FAISS) → retrieval strategy (similarity search, MMR for diversity) → prompt template → LLM call → output parsing. Should mention trade-offs like chunk size affecting retrieval quality.

> **Red Flag:** Can only describe it at a conceptual level without mentioning specific parameters, chunk strategies, or retrieval trade-offs.

**Q: How did you reduce LLM inference latency with quantization?**

> **Strong Answer:** Quantization reduces model weight precision (FP32 → INT8 or INT4) using tools like `bitsandbytes`, `GPTQ`, or `llama.cpp`. This reduces memory footprint and speeds up inference at slight accuracy cost. Should also mention model distillation (training smaller student model from larger teacher), caching repeated prompts, batching requests, and using faster inference runtimes like vLLM or TGI.

> **Red Flag:** Can't name specific tools or confuses quantization with other optimization techniques.

**Q: What does your NLP sentiment analysis implementation look like?**

> **Strong Answer:** Either fine-tuned a transformer (BERT/RoBERTa) on domain-specific labeled data, or used a pre-trained model (HuggingFace `transformers`) with a classification head. Should mention handling class imbalance, evaluation metrics (F1 over accuracy for imbalanced classes), inference pipeline, and how results were served (batch vs real-time API). For social media — handling short text, slang, emojis.

> **Red Flag:** Only mentions using a pre-built API (AWS Comprehend) with no understanding of the underlying model.

---

## Behavioral/Leadership

**Q: You led teams at Buzzsols — how many people, and how did you handle underperformers?**

> **Strong Answer:** Clear answer on team size. For underperformers — identifies root cause first (skill gap vs motivation vs unclear expectations), sets clear measurable goals with a timeline, provides support/pairing, documents conversations. Escalates to HR if no improvement. Shows empathy but decisiveness.

> **Red Flag:** Either never had direct reports (leadership claim is inflated) or handled it purely punitively.

**Q: Tell me about a cross-functional conflict you navigated.**

> **Strong Answer:** Specific story with STAR format (Situation, Task, Action, Result). Should show they listened to the other party's constraints, found shared goals, escalated appropriately when needed, and achieved a concrete outcome. Not vague or theoretical.

---

## Metrics to Challenge

| Claim | Follow-up |
|-------|-----------|
| "80% deployment error reduction" | How was error rate measured before/after? What was the baseline? |
| "50% faster queries" | What tool measured this? p50 or p99 latency? Production or staging? |
| "20% delivery time reduction" (Agile17) | Was this team-wide or just your tickets? How tracked? |
| "6+ years experience" | BSc finished May 2019 — so experience started ~2019, making it ~6 years max. Verify timeline. |

---

## Overall Verdict Framework

| Area | What to assess |
|------|---------------|
| **Depth vs breadth** | Does he know 3 things deeply or 30 things shallowly? |
| **Ownership** | Does he say "I built" or "the team built"? |
| **Failure stories** | Can he articulate what went wrong and what he learned? |
| **LLM/AI credibility** | This is the most inflated area on most resumes right now — probe hardest here |
