# Context Engineering Tools & Testing Strategy

**Date**: 2025-10-27
**Critical Question**: What tools and tests do we need to demonstrate context engineering gains across phases?

---

## 🎯 Project Core Objective

> Demonstrate **progressive gains of context engineering techniques** in LLM applications through 7 phases

**Key Metrics to Improve:**
- **Effectiveness**: Accuracy, relevance, hallucination rate, context utilization
- **Efficiency**: Latency, token usage, cost, cache hit rate
- **Scalability**: Throughput, memory usage

---

## 📊 Context Engineering Progression

### Phase 0: Baseline (COMPLETE) ✅
- Simple echo system
- ROUGE-1: 0.3149, Relevance: 0.5698, Hallucination: 0.0422
- **No context engineering**

### Phase 1: MVP Agent (CURRENT)
- ADK agent with tool calling
- **Context engineering starts here**: Agent can use tools to get better context
- Expected improvements: Better accuracy (real LLM vs echo)

### Phase 2: Basic RAG
- Vector database retrieval
- **Context engineering**: Inject relevant documents into prompts
- Expected improvements: Accuracy on document-based queries

### Phase 3: Advanced Retrieval
- Hybrid search, reranking, query enhancement
- **Context engineering**: Better context selection
- Expected improvements: Relevance score, reduced hallucination

### Phase 4: Memory & State
- Conversation history, semantic caching
- **Context engineering**: Use past context to inform current responses
- Expected improvements: Coherence, efficiency (caching)

### Phase 5: Context Compression
- Prompt compression, filtering, smart context assembly
- **Context engineering**: Optimize context usage within token limits
- Expected improvements: Token usage, latency, cost

### Phase 6: Advanced Techniques
- Graph RAG, adaptive chunking, query routing
- **Context engineering**: Sophisticated context selection and assembly
- Expected improvements: All metrics optimized

### Phase 7: Full Integration
- All techniques working together
- **Context engineering**: Fully optimized context pipeline
- Expected improvements: Production-ready performance

---

## 🔍 Critical Analysis: Do We Need Skipped Tools?

### File System Tool
**For Context Engineering? NO ❌**

**Reasoning:**
- Context engineering is about **what context you give the LLM**, not file I/O
- RAG Phase (Phase 2) will handle document ingestion programmatically
- File operations don't demonstrate context engineering gains
- Security risk outweighs benefit

**Alternative:**
- Phase 2: Document ingestion API (controlled, safe)
- Phase 2: RAG retrieval tool (agent retrieves context from vector DB)

### Code Execution Tool
**For Context Engineering? NO ❌**

**Reasoning:**
- Calculator tool already demonstrates tool use
- Context engineering focuses on **information context**, not code execution
- Very high security risk
- Not needed for any phase's metrics

**Alternative:**
- Calculator tool is sufficient for demonstrating tool calling

### Web Search Tool
**For Context Engineering? YES, BUT NOT NOW ✅**

**Reasoning:**
- Useful for Phase 3+ (external context retrieval)
- Demonstrates retrieving context from external sources
- Not critical for Phase 1 evaluation
- Can implement as placeholder now, real integration in Phase 3

---

## ✅ WHAT TOOLS DO WE ACTUALLY NEED?

### Phase 1 Requirements (MVP Agent)

**Goal**: Prove ADK + Ollama + tool calling works, establish baseline with LLM

**Current Tools (SUFFICIENT):**

1. **Calculator** ✅
   - Demonstrates tool calling
   - Tests agent's ability to recognize when to use tools
   - Relevant test queries: "What is 15 * 7?", "Calculate 2^8"

2. **Text Analysis** ✅
   - Demonstrates context processing
   - Tests multi-return-value handling
   - Relevant test queries: "Analyze this text: ...", "How many words in..."

3. **Count Words** ✅
   - Simple, fast tool for quick operations
   - Tests tool selection (when to use simple vs complex tool)
   - Relevant test queries: "Count words in: ..."

4. **Time/Timezone** ✅
   - Demonstrates external knowledge retrieval
   - Tests error handling (invalid timezones)
   - Relevant test queries: "What time is it in Tokyo?", "Current time in America/New_York"

**Verdict**: ✅ **SUFFICIENT FOR PHASE 1** - These 4 tools demonstrate:
- Tool calling mechanism works
- Agent can choose appropriate tools
- Multi-step reasoning (decide if tool is needed)
- Error handling
- Different tool types (computation, analysis, lookup)

### Phase 2 Requirements (RAG)

**Goal**: Demonstrate context injection improves answers

**Critical NEW Tool:**

5. **RAG Retrieval Tool** ⚠️ REQUIRED FOR PHASE 2
   ```python
   def retrieve_documents(query: str, top_k: int = 5) -> Dict:
       """
       Retrieve relevant documents from vector database.

       THIS IS THE KEY CONTEXT ENGINEERING TOOL!

       Args:
           query: Search query
           top_k: Number of documents to retrieve

       Returns:
           dict: Retrieved documents with relevance scores
       """
       # Search vector DB
       # Return relevant documents
       # Agent injects these into its context
   ```

**Why Critical:**
- **This is pure context engineering**: Retrieving and injecting relevant context
- Directly impacts accuracy, relevance scores
- Tests: Compare answers WITH vs WITHOUT retrieved context
- Metrics: Context utilization, answer accuracy improvement

### Phase 3+ Requirements (Advanced Context Engineering)

**Additional Tools Needed:**

6. **Web Search Tool** (Phase 3)
   - Real-time external context retrieval
   - Tests: Queries needing current information
   - Metrics: Accuracy on time-sensitive queries

7. **Multi-Query Retrieval** (Phase 3)
   - Query expansion for better context retrieval
   - Tests: Complex queries needing multiple perspectives
   - Metrics: Relevance score improvement

8. **Context Filtering Tool** (Phase 5)
   - Remove irrelevant context before injection
   - Tests: Large context sets, measure token reduction
   - Metrics: Token usage, latency, maintained accuracy

---

## 🧪 COMPREHENSIVE TESTING STRATEGY

### Phase 1 Testing (CURRENT PHASE)

**Test Categories:**

#### 1. Tool Calling Tests
```python
test_cases = [
    # Calculator tool
    {
        "query": "What is 157 multiplied by 83?",
        "expected_tool": "calculate",
        "expected_pattern": "13031",
        "measures": "Tool selection, accuracy"
    },

    # Text analysis tool
    {
        "query": "Analyze this sentence: The quick brown fox jumps over the lazy dog",
        "expected_tool": "analyze_text",
        "expected_pattern": "9 words",
        "measures": "Multi-value tool results"
    },

    # Time tool
    {
        "query": "What's the current time in Asia/Tokyo?",
        "expected_tool": "get_current_time",
        "expected_pattern": "JST",
        "measures": "External knowledge, timezone handling"
    },

    # No tool needed
    {
        "query": "What is Python?",
        "expected_tool": None,
        "measures": "Agent knows when NOT to use tools"
    }
]
```

#### 2. Baseline Comparison (CRITICAL)
```python
# Run SAME 15 test cases as Phase 0
baseline_dataset = load("data/test_sets/baseline_qa.json")

# Compare metrics:
phase0_metrics = {
    "rouge1_f1": 0.3149,
    "rouge2_f1": 0.1598,
    "rougeL_f1": 0.2509,
    "relevance": 0.5698,
    "hallucination_rate": 0.0422
}

phase1_metrics = run_evaluation(agent, baseline_dataset)

# Expected improvements:
# - ROUGE scores: 0.31 → 0.45-0.60 (real LLM understanding)
# - Relevance: 0.57 → 0.70-0.85 (better answers)
# - Hallucination: 0.04 → 0.10-0.20 (may increase slightly)
```

#### 3. Tool-Enhanced Queries
```python
# New test cases that BENEFIT from tools
tool_enhanced_tests = [
    {
        "id": "tool_001",
        "query": "If I have 15 apples and give away 7, then buy 23 more, how many do I have?",
        "requires_tool": "calculate",
        "ground_truth": "31 apples",
        "tests": "Multi-step calculation via tool"
    },
    {
        "id": "tool_002",
        "query": "Write a paragraph, then tell me how many words it contains",
        "requires_tool": "count_words",
        "tests": "Tool use with generated content"
    },
    {
        "id": "tool_003",
        "query": "What time zone is Tokyo in and what time is it there?",
        "requires_tool": "get_current_time",
        "tests": "Knowledge + tool combination"
    }
]
```

### Phase 2 Testing (RAG - CONTEXT ENGINEERING STARTS HERE)

**Critical Tests:**

#### 1. Context Injection Impact
```python
rag_comparison_tests = [
    {
        "query": "What is Phase 3 about in this project?",
        "without_context": {
            "expected": "Generic/wrong answer",
            "measures": "Baseline without RAG"
        },
        "with_context": {
            "retrieved_docs": ["BACKLOG.md Phase 3 section"],
            "expected": "Advanced retrieval techniques...",
            "measures": "Answer accuracy WITH context"
        },
        "metric": "ROUGE score improvement, context utilization"
    }
]
```

#### 2. Document-Based Q&A
```python
# Use existing rag_qa.json test cases
rag_tests = load("data/test_sets/rag_qa.json")  # 3 test cases

for test in rag_tests:
    # Test WITHOUT retrieval (baseline)
    answer_no_rag = agent.query(test.query)

    # Test WITH retrieval (RAG)
    retrieved_docs = vector_db.search(test.query, top_k=5)
    answer_with_rag = agent.query_with_context(test.query, retrieved_docs)

    # Measure improvement
    improvement = compare_metrics(answer_no_rag, answer_with_rag)

# Expected: Significant accuracy improvement with context
```

#### 3. Context Utilization Metric (NEW)
```python
def measure_context_utilization(query, retrieved_docs, answer):
    """
    Measure how much of the retrieved context was actually used.

    This is a KEY context engineering metric!
    """
    # Extract key facts from retrieved docs
    facts = extract_facts(retrieved_docs)

    # Check which facts appear in answer
    utilized_facts = count_utilized_facts(answer, facts)

    utilization_rate = utilized_facts / total_facts

    return {
        "context_utilization": utilization_rate,
        "relevant_facts_used": utilized_facts,
        "total_facts_available": total_facts
    }
```

### Phase 3-7 Testing (Advanced Context Engineering)

**Progressive Tests:**

#### Phase 3: Advanced Retrieval
- Test: Hybrid search vs pure vector search
- Measure: Retrieval precision, relevance score
- Test: Reranking impact on answer quality
- Measure: ROUGE improvement, reduced hallucination

#### Phase 4: Memory & State
- Test: Multi-turn conversations
- Measure: Coherence, context awareness
- Test: Semantic caching
- Measure: Cache hit rate, latency reduction

#### Phase 5: Context Compression
- Test: Large context → compressed context
- Measure: Token reduction while maintaining accuracy
- Test: Selective context inclusion
- Measure: Efficiency gains, cost reduction

#### Phase 6: Advanced Techniques
- Test: Graph RAG vs standard RAG
- Measure: Complex query handling
- Test: Query routing
- Measure: Response quality per query type

---

## 📋 RECOMMENDED TOOL IMPLEMENTATION PLAN

### Phase 1 (CURRENT) - READY TO TEST ✅

**Tools:**
- ✅ Calculator
- ✅ Text Analysis
- ✅ Count Words
- ✅ Time/Timezone

**Tests:**
1. Run manual test script ✅
2. Run baseline_qa.json evaluation ⚠️ NEXT
3. Create tool-enhanced test cases ⚠️ NEXT
4. Compare with Phase 0 metrics ⚠️ NEXT

**Skip:**
- ❌ File system tool (not needed)
- ❌ Code execution (not needed)
- ❌ Web search (defer to Phase 3)

### Phase 2 (NEXT PHASE) - CRITICAL NEW TOOL

**New Tool Required:**
- ⚠️ **RAG Retrieval Tool** (THE key context engineering tool)
  ```python
  def retrieve_context(query: str) -> Dict:
      """Agent retrieves documents from vector DB."""
  ```

**Why Critical:**
- This tool IS context engineering
- Directly demonstrates "injecting relevant context improves answers"
- All future phases build on this

**Tests:**
- Before/after RAG comparison
- Context utilization metrics
- Document-based Q&A accuracy

### Phase 3+ Tools (FUTURE)

**As Needed:**
- Web search (external context)
- Multi-query expansion (better retrieval)
- Reranking (better context selection)
- Context filters (optimize token usage)

---

## 🎯 FINAL VERDICT

### Current Tools: ✅ SUFFICIENT FOR PHASE 1

**Reasoning:**
- 4 diverse tools demonstrate tool calling works
- Cover computation, analysis, and lookup
- Sufficient to measure Phase 1 baseline with LLM
- File system & code execution NOT needed for context engineering

### What We Need Next:

**Phase 1 (Now):**
1. ✅ Test current tools
2. ⚠️ Run evaluation on baseline_qa.json
3. ⚠️ Create tool-enhanced test cases
4. ⚠️ Measure improvements vs Phase 0

**Phase 2 (Critical):**
1. ⚠️ Implement RAG retrieval tool (THE context engineering tool)
2. ⚠️ Vector database setup
3. ⚠️ Document ingestion
4. ⚠️ Test WITH vs WITHOUT context injection

### Key Insight:

**Context engineering is demonstrated by:**
1. ✅ Phase 1: Agent CAN use tools (foundation)
2. ⚠️ Phase 2: Agent retrieves RELEVANT CONTEXT and uses it (core demonstration)
3. ⚠️ Phase 3+: Progressively BETTER context selection and optimization

**The skipped tools (file system, code execution) don't help demonstrate context engineering gains.**

---

## 📊 Success Metrics Summary

### Phase 1 Success Criteria:
- ✅ Tool calling works
- ✅ Agent chooses appropriate tools
- ⚠️ ROUGE scores > Phase 0 (0.31 → 0.45+)
- ⚠️ Relevance score > Phase 0 (0.57 → 0.70+)
- ⚠️ Latency acceptable (<5000ms per query)

### Phase 2 Success Criteria (Context Engineering Proof):
- ⚠️ Answers WITH context >> answers WITHOUT context
- ⚠️ Context utilization rate measured
- ⚠️ Document-based Q&A accuracy significantly improved
- ⚠️ Relevance score > Phase 1

### Phases 3-7: Progressive Improvements
- Each phase optimizes a different aspect of context engineering
- Cumulative improvements in all metrics

---

## 🚀 IMMEDIATE NEXT STEPS

1. **Test Phase 1 Agent** (30 min)
   ```bash
   python3 scripts/test_agent_manual.py
   ```

2. **Run Phase 1 Evaluation** (1 hour)
   - Update evaluation script to use ADK agent
   - Run on baseline_qa.json
   - Compare metrics with Phase 0

3. **Create Tool-Enhanced Tests** (30 min)
   - Add test cases that benefit from tools
   - Measure tool utilization

4. **Document Phase 1 Results** (30 min)
   - Create phase1_results.json
   - Write phase summary
   - Prepare for Phase 2

**Total Time: ~2.5 hours to complete Phase 1 evaluation**

Then proceed to Phase 2 with RAG retrieval tool.

---

*Analysis Date: 2025-10-27*
*Conclusion: Current 4 tools are SUFFICIENT for Phase 1. RAG retrieval tool is CRITICAL for Phase 2.*
