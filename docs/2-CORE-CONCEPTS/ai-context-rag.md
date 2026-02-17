# AI Context & RAG - How Podcast Geeker Uses Your Research

Podcast Geeker uses different approaches to make AI models aware of your research depending on the feature. This section explains **Advanced Agentic RAG** (used in Ask) and **full-content context** (used in Chat).

> **What's New**: Podcast Geeker now features **Advanced Agentic RAG** capabilities including hierarchical indexing, intelligent query rewriting, self-correction mechanisms, and optional multi-modal understanding. These enhancements significantly improve retrieval accuracy and answer quality.

---

## The Problem: Making AI Aware of Your Data

### Traditional Approaches (and their problems)

**Option 1: Fine-Tuning**
- Train the model on your data
- Pro: Model becomes specialized
- Con: Expensive, slow, permanent (can't unlearn)

**Option 2: Send Everything to Cloud**
- Upload all your data to ChatGPT/Claude API
- Pro: Works well, fast
- Con: Privacy nightmare, data leaves your control, expensive

**Option 3: Ignore Your Data**
- Just use the base model without your research
- Pro: Private, free
- Con: AI doesn't know anything about your specific topic

### Podcast Geeker's Dual Approach

**For Chat**: Sends the entire selected content to the LLM
- Simple and transparent: You select sources, they're sent in full
- Maximum context: AI sees everything you choose
- You control which sources are included

**For Ask (RAG)**: Retrieval-Augmented Generation
- RAG = Retrieval-Augmented Generation
- The insight: *Search your content, find relevant pieces, send only those*
- Automatic: AI decides what's relevant based on your question

---

## Advanced Agentic RAG: Beyond Traditional Retrieval

Podcast Geeker implements **Agentic RAG** - an advanced approach that goes beyond simple search-and-retrieve. The system acts as an intelligent agent that understands context, refines queries, and ensures high-quality results.

### What Makes It "Agentic"?

Traditional RAG simply searches and returns results. Agentic RAG adds intelligence:

1. **Query Understanding**: Analyzes your question to understand intent
2. **Conversation Memory**: Remembers previous questions for context
3. **Smart Rewriting**: Reformulates unclear queries automatically
4. **Self-Correction**: Detects poor results and retries with better queries
5. **Hierarchical Search**: Balances precision and context through parent/child chunks

### The Four Pillars of Agentic RAG

#### 1. Hierarchical Indexing (Parent/Child Chunks)

**The Problem with Traditional Chunking:**
```
Traditional: Split document into 500-word chunks
Result: Precise search but loses context
```

**Podcast Geeker's Solution:**
```
Parent Chunks: Large semantic sections (2000-10000 chars)
  └─ Child Chunks: Small precise pieces (500 chars)

Search Flow:
1. Search child chunks for precision
2. Retrieve parent chunks for context
3. AI sees both precision and full context
```

**Example:**
```
Document: "AI Safety Research Paper" (50 pages)
↓
Parent Chunks: 20 sections (by headings)
↓
Child Chunks: 150 precise pieces
↓
Your Question: "What's the alignment approach?"
↓
Search: Find relevant child chunks (precise)
↓
Retrieve: Get their parent sections (context)
↓
AI Answer: Uses precise matches + full context
```

**Benefits:**
- Better search precision (child chunks match specific queries)
- Complete context (parent chunks provide full picture)
- No information loss (unlike pure small chunks)

---

#### 2. Query Rewriting & Analysis

**The Problem:**
Users often ask ambiguous or incomplete questions:
- "What does it say about that?" (missing context)
- "Compare the two approaches" (which approaches?)
- "Tell me more" (more about what?)

**Podcast Geeker's Solution:**

**Step 1: Conversation Summarization**
```
System analyzes your recent questions and answers
Builds context summary:
  - Main topics discussed
  - Entities mentioned
  - Unresolved questions
```

**Step 2: Query Analysis**
```python
Analyzes your question:
{
  "is_clear": true/false,          # Can this be answered?
  "questions": ["Q1", "Q2", "Q3"], # Reformulated queries
  "clarification": "..."            # If unclear, what to ask
}
```

**Step 3: Clarification (if needed)**
```
If question is unclear:
  System: "Are you asking about [X] or [Y]?"
  You: Clarify
  System: Proceeds with clear query

If question is clear:
  Proceeds directly to search
```

**Example Flow:**
```
You: "What does the third chapter say?"
↓
System thinks: "Which document? Let me check conversation history"
↓
Context: User was discussing "AI Safety Paper.pdf"
↓
Rewritten: "What does chapter 3 of the AI Safety Paper say about [topic from context]?"
↓
Search proceeds with clear query
```

---

#### 3. Self-Correction Mechanism

**The Problem:**
Sometimes the first search doesn't find good results:
- Query used wrong keywords
- Content uses different terminology
- Search was too specific or too broad

**Traditional RAG Response:**
```
Search → Poor results → Return poor answer → User frustrated
```

**Agentic RAG Response:**
```
Search → Evaluate results → If insufficient → Rewrite query → Search again
```

**How It Works:**

**Step 1: Relevance Evaluation**
```python
After initial search:
  - Check similarity scores
  - Analyze content relevance
  - Threshold: If max score < 0.5, results insufficient
```

**Step 2: Query Refinement**
```
System: "Initial search didn't find good matches.
         Trying alternate phrasing..."
         
Original: "transformer architecture"
Refined: "attention mechanism in neural networks"
```

**Step 3: Retry Search**
```
Execute refined query
Evaluate new results
If still insufficient → return best available + flag uncertainty
```

**Example:**
```
You: "How do models prevent hallucinations?"
↓
First Search: "prevent hallucinations" (poor matches, score 0.3)
↓
Self-Correction: Low relevance detected
↓
Refined: "reduce false generation accuracy verification"
↓
Second Search: Better matches (score 0.8)
↓
Answer: High-quality response with relevant context
```

**Configuration:**
```bash
OPEN_NOTEBOOK_SELF_CORRECTION=true     # Enable feature
OPEN_NOTEBOOK_MIN_RELEVANCE_SCORE=0.5  # Threshold for retry
OPEN_NOTEBOOK_MAX_RETRIES=1            # How many retries
```

---

#### 4. Conversation Memory for Ask Mode

**Traditional Ask Mode:**
Each question is independent; no memory of previous questions.

**Enhanced Ask Mode:**
Maintains conversation context across questions.

**How It Works:**

**Step 1: Session Creation** (Optional)
```typescript
// Frontend provides session_id
const response = await ask({
  question: "What is alignment?",
  session_id: "conversation-123"
});
```

**Step 2: Context Building**
```
System loads conversation history:
  - Previous questions
  - Previous answers
  - Topics discussed
  - Entities mentioned

Generates summary for current query
```

**Step 3: Enhanced Query Understanding**
```
Current question + Conversation summary → Better understanding

Example:
  Q1: "What is alignment in AI?"
  A1: [Detailed answer about alignment]
  Q2: "What are the main challenges?"
  
System interprets Q2 as:
  "What are the main challenges [in AI alignment]?"
  (inferred from conversation context)
```

**Example Conversation:**
```
You: "What does the paper say about transformers?"
System: [Finds and explains transformer section]

You: "How does it compare to CNNs?"
System: [Understands "it" = transformers from context]
        [Searches for CNN comparisons]
        [Provides comparative analysis]

You: "What are the limitations?"
System: [Understands "limitations" = of transformers vs CNNs]
        [Provides focused answer]
```

**Configuration:**
```bash
OPEN_NOTEBOOK_ASK_MEMORY=true  # Enable conversation memory
```

---

## Multi-Modal Enhancement (Optional)

**Traditional RAG Limitation:**
PDFs contain images, tables, equations → Extracted as text-only → Lose semantic information

**RAG-Anything Integration:**
Optional enhancement layer for comprehensive multi-modal understanding.

### What It Processes

1. **Images & Figures**
   - Vision model analyzes images
   - Generates semantic descriptions
   - Identifies charts, diagrams, photos

2. **Tables**
   - Extracts table structure
   - Interprets data relationships
   - Generates natural language summaries

3. **Equations**
   - Parses mathematical notation
   - Converts to LaTeX and text
   - Explains equation semantics

### How It Works

**Enhancement Pipeline:**
```
PDF Upload
  ↓
content-core: Extract text (existing)
  ↓
RAG-Anything: Analyze non-text elements (optional)
  ├─ MinerU: Parse document structure
  ├─ Vision Model: Describe images
  ├─ Table Interpreter: Structure tables
  └─ Equation Parser: Understand math
  ↓
Merge: Enhanced text with semantic descriptions
  ↓
Embed & Store: Standard RAG pipeline
```

**Example Output:**
```markdown
Original PDF Content:
  "Figure 1 shows the architecture."
  [Complex diagram image]

Enhanced Content:
  "Figure 1 shows the architecture.
  
  [Figure: Neural network architecture diagram showing an 
  encoder-decoder structure with attention mechanisms. The 
  encoder has 6 layers processing input tokens through 
  self-attention and feed-forward networks...]"

Result: AI can now discuss the diagram content!
```

### Configuration

```bash
# Enable multi-modal enhancement
OPEN_NOTEBOOK_MULTIMODAL_ENHANCE=true

# Choose parser
OPEN_NOTEBOOK_MULTIMODAL_PARSER=mineru  # or docling

# Requires Vision Model configuration in UI
# Settings → API Keys → Add Vision-capable model
```

**Use Cases:**
- Research papers with complex diagrams
- Financial reports with data tables
- Scientific documents with equations
- Technical manuals with schematics

---

## Configuration Options

All Agentic RAG features are configurable via environment variables:

```bash
# Phase 1: Hierarchical Indexing
OPEN_NOTEBOOK_HIERARCHICAL_INDEX=true          # Enable Parent/Child
OPEN_NOTEBOOK_PARENT_MIN_SIZE=2000             # Parent minimum chars
OPEN_NOTEBOOK_PARENT_MAX_SIZE=10000            # Parent maximum chars
OPEN_NOTEBOOK_CHILD_CHUNK_SIZE=500             # Child chunk size
OPEN_NOTEBOOK_CHILD_CHUNK_OVERLAP=100          # Child overlap

# Phase 2: Query Understanding
OPEN_NOTEBOOK_QUERY_REWRITE=true               # Enable query rewriting
OPEN_NOTEBOOK_MAX_SUB_QUERIES=3                # Max sub-queries

# Phase 3: Self-Correction
OPEN_NOTEBOOK_SELF_CORRECTION=true             # Enable auto-retry
OPEN_NOTEBOOK_MIN_RELEVANCE_SCORE=0.5          # Retry threshold
OPEN_NOTEBOOK_MAX_RETRIES=1                    # Retry limit

# Phase 4: Conversation Memory
OPEN_NOTEBOOK_ASK_MEMORY=true                  # Enable Ask memory

# Phase 5: Multi-modal Enhancement
OPEN_NOTEBOOK_MULTIMODAL_ENHANCE=true          # Enable RAG-Anything
OPEN_NOTEBOOK_MULTIMODAL_PARSER=mineru         # Parser choice
```

**Defaults:**
- All features are **disabled by default** for backward compatibility
- Enable incrementally as needed
- No performance impact when disabled

---

## How RAG Works: Three Stages

### Stage 1: Content Preparation

When you upload a source, Podcast Geeker prepares it for retrieval:

```
1. EXTRACT TEXT
   PDF → text
   URL → webpage text
   Audio → transcribed text
   Video → subtitles + transcription

2. HIERARCHICAL CHUNKING (if enabled)
   A. Create Parent Chunks:
      - Split by semantic boundaries (headings, sections)
      - Size: 2000-10000 characters
      - Maintain document structure
   
   B. Create Child Chunks:
      - Within each parent, split into smaller pieces
      - Size: ~500 characters with 100-char overlap
      - Enable precise search
   
   C. Link Parent-Child relationships
      - Each child knows its parent
      - Enables context retrieval

   Traditional Mode (default):
      - Fixed-size chunks (~1200 chars)
      - No parent-child relationships

3. MULTI-MODAL ENHANCEMENT (optional)
   If enabled + PDF + Vision model configured:
   - Analyze images with vision model
   - Extract table structures
   - Parse equation semantics
   - Merge descriptions into text

4. CREATE EMBEDDINGS
   Each chunk → semantic vector (numbers representing meaning)
   Why? Allows finding chunks by similarity, not just keywords

5. STORE IN DATABASE
   - Child chunks + embeddings → searchable
   - Parent chunks → context repository
   - Metadata: source, page, position
```

**Example:**
```
Source: "AI Safety Research 2026" (50-page PDF)
↓
Extracted: 50 pages of text
↓
Hierarchical Chunking (if enabled):
  - 20 Parent chunks (by sections)
  - 150 Child chunks (within parents)
  - Links: Child → Parent relationships
↓
Multi-modal (if enabled):
  - 5 figures analyzed with vision model
  - 3 tables structured and described
  - 10 equations parsed to LaTeX + text
↓
Embedded: 
  - Child chunks get vectors (1536 numbers for OpenAI)
  - Ready for semantic search
↓
Stored: Ready for intelligent retrieval
```

---

### Stage 2: Query Time (What You Search For)

When you ask a question, the system intelligently finds relevant content:

```
1. YOU ASK A QUESTION
   "What does the paper say about alignment?"

2. CONVERSATION SUMMARIZATION (if Ask memory enabled)
   - Load recent conversation history
   - Extract context: topics, entities, unresolved questions
   - Build summary for query understanding

3. QUERY ANALYSIS & REWRITING (if enabled)
   - Analyze question clarity
   - Reformulate for better search
   - Expand with conversation context
   - Detect if clarification needed
   
   Example transformations:
   "What about the third approach?" 
   → "What does the AI Safety paper say about the third 
      alignment approach mentioned in section 3.2?"

4. CLARIFICATION GATE (if question unclear)
   - System asks: "Are you referring to [X] or [Y]?"
   - You provide clarification
   - System proceeds with clear query

5. HIERARCHICAL SEARCH (if enabled)
   A. Search Child Chunks:
      - Convert question to embedding vector
      - Find top-N most similar child chunks
      - Score: semantic similarity (0-1)
   
   B. Evaluate Relevance:
      - Check if results are sufficient (score > threshold)
      - If insufficient → trigger self-correction
   
   C. Retrieve Parent Context:
      - For relevant child chunks
      - Get their parent chunks
      - Provides full context around matches
   
   Traditional Search (default):
   - Single-level chunk search
   - No parent retrieval

6. SELF-CORRECTION (if enabled and results poor)
   - Rewrite query with alternate phrasing
   - Retry search with new query
   - Compare results quality
   - Use best available

7. RETURN RESULTS
   ✓ Relevant child chunks (precision)
   ✓ Parent chunks (context)
   ✓ Source information (citations)
   ✓ Relevance scores (confidence)
```

**Example Flow:**
```
Q: "What does it say about alignment?"
↓
Conversation Summary: User discussing "AI Safety paper"
↓
Query Rewrite: "What does the AI Safety paper say about 
                alignment approaches and challenges?"
↓
Search Child Chunks:
  - Chunk 47 (alignment section): similarity 0.94
  - Chunk 63 (safety approaches): similarity 0.88
  - Chunk 12 (related work): similarity 0.71
↓
Evaluate: Good results (top score 0.94 > 0.5 threshold)
↓
Retrieve Parents:
  - Parent of Chunk 47: Full "Alignment Methods" section
  - Parent of Chunk 63: Full "Safety Framework" section
↓
Result: Precise matches + full contextual sections
```

**With Self-Correction:**
```
Q: "How do you prevent model errors?"
↓
First Search: "prevent model errors" → poor matches (max score 0.3)
↓
Self-Correction Triggered: Results insufficient
↓
Query Refinement: "reduce neural network hallucination 
                   false generation accuracy verification"
↓
Second Search: Better matches (score 0.8)
↓
Result: High-quality answer with relevant sources
```

---

### Stage 3: Augmentation (How AI Uses It)

Now you have the relevant pieces. The AI uses them:

```
SYSTEM BUILDS A PROMPT:
  "You are an AI research assistant.

   The user has the following research materials:
   [CHUNK 47 CONTENT]
   [CHUNK 63 CONTENT]

   User question: 'What does the paper say about alignment?'

   Answer based on the above materials."

AI RESPONDS:
  "Based on the research materials, the paper approaches
   alignment through [pulls from chunks] and emphasizes
   [pulls from chunks]..."

SYSTEM ADDS CITATIONS:
  "- See research materials page 15 for approach details
   - See research materials page 23 for emphasis on X"
```

---

## Two Search Modes: Exact vs. Semantic

Podcast Geeker provides two different search strategies for different goals.

### 1. Text Search (Keyword Matching)

**How it works:**
- Uses BM25 ranking (the same algorithm Google uses)
- Finds chunks containing your keywords
- Ranks by relevance (how often keywords appear, position, etc.)

**When to use:**
- "I remember the exact phrase 'X' and want to find it"
- "I'm looking for a specific name or number"
- "I need the exact quote"

**Example:**
```
Search: "transformer architecture"
Results:
  1. Chunk with "transformer architecture" 3 times
  2. Chunk with "transformer" and "architecture" separately
  3. Chunk with "transformer-based models"
```

### 2. Vector Search (Semantic Similarity)

**How it works:**
- Converts your question to a vector (number embedding)
- Finds chunks with similar vectors
- No keywords needed—finds conceptually similar content

**When to use:**
- "Find content about X (without saying exact words)"
- "I'm exploring a concept"
- "Find similar ideas even if worded differently"

**Example:**
```
Search: "what's the mechanism for model understanding?"
Results (no "understanding" in any chunk):
  1. Chunk about interpretability and mechanistic analysis
  2. Chunk about feature analysis
  3. Chunk about attention mechanisms

Why? The vectors are semantically similar to your concept.
```

---

## Context Management: Your Control Panel

Here's where Podcast Geeker is different: **You decide what the AI sees.**

### The Three Levels

| Level | What's Shared | Example Cost | Privacy | Use Case |
|-------|---------------|--------------|---------|----------|
| **Full Content** | Complete source text | 10,000 tokens | Low | Detailed analysis, close reading |
| **Summary Only** | AI-generated summary | 2,000 tokens | High | Background material, references |
| **Not in Context** | Nothing | 0 tokens | Max | Confidential, irrelevant, or archived |

### How It Works

**Full Content:**
```
You: "What's the methodology in paper A?"
System:
  - Searches paper A
  - Retrieves full paper content (or large chunks)
  - Sends to AI: "Here's paper A. Answer about methodology."
  - AI analyzes complete content
  - Result: Detailed, precise answer
```

**Summary Only:**
```
You: "I want to chat using paper A and B"
System:
  - For Paper A: Sends AI-generated summary (not full text)
  - For Paper B: Sends full content (detailed analysis)
  - AI sees 2 sources but in different detail levels
  - Result: Uses summaries for context, details for focused content
```

**Not in Context:**
```
You: "I have 10 sources but only want 5 in context"
System:
  - Paper A-E: In context (sent to AI)
  - Paper F-J: Not in context (AI can't see them, doesn't search them)
  - AI never knows these 5 sources exist
  - Result: Tight, focused context
```

### Why This Matters

**Privacy**: You control what leaves your system
```
Scenario: Confidential company docs + public research
Control: Public research in context → Confidential docs excluded
Result: AI never sees confidential content
```

**Cost**: You control token usage
```
Scenario: 100 sources for background + 5 for detailed analysis
Control: Full content for 5 detailed, summaries for 95 background
Result: 80% lower token cost than sending everything
```

**Quality**: You control what the AI focuses on
```
Scenario: 20 sources, question requires deep analysis
Control: Full content for relevant source, exclude others
Result: AI doesn't get distracted; gives better answer
```

---

## The Difference: Chat vs. Ask

**IMPORTANT**: These use completely different approaches!

### Chat: Full-Content Context (NO RAG)

**How it works:**
```
YOU:
  1. Select which sources to include in context
  2. Set context level (full/summary/excluded)
  3. Ask question

SYSTEM:
  - Takes ALL selected sources (respecting context levels)
  - Sends the ENTIRE content to the LLM at once
  - NO search, NO retrieval, NO chunking
  - AI sees everything you selected

AI:
  - Responds based on the full content you provided
  - Can reference any part of selected sources
  - Conversational: context stays for follow-ups
```

**Use this when**:
- You know which sources are relevant
- You want conversational back-and-forth
- You want AI to see the complete context
- You're doing close reading or analysis

**Advantages:**
- Simple and transparent
- AI sees everything (no missed content)
- Conversational flow

**Limitations:**
- Limited by LLM context window
- You must manually select relevant sources
- Sends more tokens (higher cost with many sources)

---

### Ask: RAG - Automatic Retrieval

**How it works:**
```
YOU:
  Ask one complex question
  (Optional: provide session_id for conversation memory)

SYSTEM:
  1. Summarize conversation (if session_id provided)
  2. Analyze and rewrite query (if enabled)
  3. Check clarity (if enabled)
     - Clear → proceed
     - Unclear → ask clarification
  4. Search child chunks using vector similarity
  5. Evaluate relevance (if enabled)
     - Sufficient → proceed
     - Insufficient → rewrite and retry
  6. Retrieve parent chunks for context (if enabled)
  7. Synthesize comprehensive answer
  8. Add citations with context

AI:
  - Sees retrieved chunks + parent context
  - Answers based on best available evidence
  - Maintains conversation context (if enabled)
  - Can reference previous questions
```

**Enhanced Features (when enabled):**
- **Query Understanding**: Rewrites ambiguous questions
- **Conversation Memory**: Remembers previous questions
- **Self-Correction**: Retries with better queries if needed
- **Hierarchical Context**: Balances precision and completeness
- **Multi-modal**: Understands images, tables, equations in PDFs

**Use this when**:
- You have many sources and don't know which are relevant
- You want the AI to search automatically
- You need a comprehensive answer to a complex question
- You want to minimize tokens sent to LLM
- You want ongoing conversation support (with session_id)

**Advantages:**
- Automatic intelligent search
- Works across many sources at once
- Cost-effective (sends only relevant chunks + context)
- Self-improving (corrects poor initial searches)
- Context-aware (remembers conversation)
- Multi-modal understanding (optional)

**Limitations:**
- Can be conversational with session_id (new feature!)
- AI sees retrieved chunks (but with parent context for completeness)
- Search quality depends on query understanding (improved with rewriting)

---

## What This Means: Privacy by Design

Podcast Geeker's RAG approach gives you something you don't get with ChatGPT or Claude directly:

**You control the boundary between:**
- What stays private (on your system)
- What goes to AI (explicitly chosen)
- What the AI can see (context levels)

### The Audit Trail

Because everything is retrieved explicitly, you can ask:
- "Which sources did the AI use for this answer?" → See citations
- "What exactly did the AI see?" → See chunks in context level
- "Is the AI's claim actually in my sources?" → Verify citation

This prevents hallucinations or misrepresentation better than most systems.

---

## How Embeddings Work (Simplified)

The magic of semantic search comes from embeddings. Here's the intuition:

### The Idea
Instead of storing text, store it as a list of numbers (vectors) that represent "meaning."

```
Chunk: "The transformer uses attention mechanisms"
Vector: [0.23, -0.51, 0.88, 0.12, ..., 0.34]
        (1536 numbers for OpenAI)

Another chunk: "Attention allows models to focus on relevant parts"
Vector: [0.24, -0.48, 0.87, 0.15, ..., 0.35]
        (similar numbers = similar meaning!)
```

### Why This Works
Words that are semantically similar produce similar vectors. So:
- "alignment" and "interpretability" have similar vectors
- "transformer" and "attention" have related vectors
- "cat" and "dog" are more similar than "cat" and "radiator"

### How Search Works
```
Your question: "How do models understand their decisions?"
Question vector: [0.25, -0.50, 0.86, 0.14, ..., 0.33]

Compare to all stored vectors. Find the most similar:
- Chunk about interpretability: similarity 0.94
- Chunk about explainability: similarity 0.91
- Chunk about feature attribution: similarity 0.88

Return the top matches.
```

This is why semantic search finds conceptually similar content even when words are different.

---

## Key Design Decisions

### 1. Search, Don't Train
**Why?** Fine-tuning is slow and permanent. Search is flexible and reversible.

### 2. Explicit Retrieval, Not Implicit Knowledge
**Why?** You can verify what the AI saw. You have audit trails. You control what leaves your system.

### 3. Multiple Search Types
**Why?** Different questions need different search (keyword vs. semantic). Giving you both is more powerful.

### 4. Context as a Permission System
**Why?** Not everything you save needs to reach AI. You control granularly.

---

## Summary

Podcast Geeker gives you **two ways** to work with AI:

### Chat (Full-Content)
- Sends entire selected sources to LLM
- Manual control: you pick sources
- Conversational: back-and-forth dialog
- Transparent: you know exactly what AI sees
- Best for: focused analysis, close reading

### Ask (Advanced Agentic RAG)
- Intelligently searches and retrieves relevant content
- Automatic: AI finds what's relevant
- Conversational: supports session memory (optional)
- Self-improving: corrects poor searches automatically
- Context-aware: hierarchical parent/child chunking
- Multi-modal: understands images, tables, equations (optional)
- Efficient: sends only relevant pieces + context
- Best for: broad questions across many sources

**Both approaches:**
1. Keep your data private (doesn't leave your system by default)
2. Give you control (you choose which features to use)
3. Create audit trails (citations show what was used)
4. Support multiple AI providers

**New Agentic RAG Capabilities:**
- 🧠 **Hierarchical Indexing**: Parent/Child chunks for precision + context
- 🔄 **Query Understanding**: Automatic rewriting and clarification
- ✨ **Self-Correction**: Retry with refined queries when needed
- 💭 **Conversation Memory**: Maintain context across questions in Ask mode
- 🖼️ **Multi-modal Enhancement**: Understand images, tables, and equations

**Configuration:**
All advanced features are opt-in via environment variables. Enable what you need:
```bash
OPEN_NOTEBOOK_HIERARCHICAL_INDEX=true    # Better context
OPEN_NOTEBOOK_QUERY_REWRITE=true         # Smarter queries
OPEN_NOTEBOOK_SELF_CORRECTION=true       # Auto-retry
OPEN_NOTEBOOK_ASK_MEMORY=true            # Conversation memory
OPEN_NOTEBOOK_MULTIMODAL_ENHANCE=true    # Multi-modal PDFs
```

---

## Acknowledgments

The Advanced Agentic RAG capabilities in Podcast Geeker are inspired by and adapted from:

- **[agentic-rag-for-dummies](https://github.com/GiovanniPasq/agentic-rag-for-dummies)** (MIT License) - Hierarchical indexing, query rewriting, and self-correction strategies
- **[RAG-Anything](https://github.com/HKUDS/RAG-Anything)** (MIT License) - Multi-modal content understanding for PDFs

We've integrated these approaches into Podcast Geeker's LangGraph + SurrealDB architecture while maintaining full backward compatibility.
