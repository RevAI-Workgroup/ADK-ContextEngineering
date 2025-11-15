# Phase 3 RAG - Manual Testing Checklist

## Pre-requisites

1. Install dependencies:
```bash
pip install chromadb sentence-transformers tiktoken
```

2. Start the backend:
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

3. Start the frontend:
```bash
cd frontend && npm run dev
```

## API Endpoint Tests

### 1. Vector Store Stats
```bash
curl http://localhost:8000/api/vector-store/stats
```
**Expected**: Returns stats with total_documents=0 initially

### 2. List Documents
```bash
curl http://localhost:8000/api/documents
```
**Expected**: Returns empty array initially

### 3. Upload Document
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@data/knowledge_base/python_basics.md"
```
**Expected**: Returns success with chunks_created count

### 4. Vector Store Stats (after upload)
```bash
curl http://localhost:8000/api/vector-store/stats
```
**Expected**: Returns stats with total_documents > 0

### 5. Search Vector Store
```bash
curl "http://localhost:8000/api/vector-store/search?query=What%20is%20Python&top_k=3"
```
**Expected**: Returns relevant document chunks with similarity scores

### 6. Bulk Ingest
```bash
curl -X POST http://localhost:8000/api/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{"directory": "data/knowledge_base", "recursive": true}'
```
**Expected**: Returns documents_processed and total_chunks

### 7. List Documents (after ingest)
```bash
curl http://localhost:8000/api/documents
```
**Expected**: Returns all uploaded documents

### 8. Delete Document
```bash
curl -X DELETE http://localhost:8000/api/documents/python_basics.md
```
**Expected**: Returns success message

### 9. Clear Vector Store
```bash
curl -X POST http://localhost:8000/api/vector-store/clear
```
**Expected**: Returns success, stats should show 0 documents

## Frontend Tests

### Vector Store Page (http://localhost:5173/vector-store)

1. **Initial Load**
   - [ ] Page loads without errors
   - [ ] Statistics cards show 0 documents
   - [ ] No documents in list
   - [ ] No console errors

2. **Upload Document**
   - [ ] Click "Upload Document" button
   - [ ] Select a .txt or .md file
   - [ ] Success message appears
   - [ ] Document appears in list
   - [ ] Stats update (document count increases)

3. **Search Documents**
   - [ ] Enter query in search box
   - [ ] Click "Search" button
   - [ ] Results appear with similarity scores
   - [ ] Results are relevant to query

4. **Delete Document**
   - [ ] Click trash icon next to a document
   - [ ] Confirm deletion
   - [ ] Document removes from list
   - [ ] Success message appears

5. **Clear All**
   - [ ] Click "Clear All" button
   - [ ] Confirm action
   - [ ] All documents cleared
   - [ ] Stats show 0 documents

### Chat Page (http://localhost:5173/chat)

1. **Upload Button Visible**
   - [ ] Paperclip icon visible next to send button
   - [ ] Button is enabled when not processing

2. **Upload Document via Chat**
   - [ ] Click paperclip icon
   - [ ] Select .txt or .md file
   - [ ] Success message appears in chat
   - [ ] Message confirms upload

3. **RAG Toggle**
   - [ ] Open configuration panel
   - [ ] RAG toggle is visible
   - [ ] Enable RAG
   - [ ] Configure settings (chunk_size, top_k, threshold)

4. **Query with RAG Disabled**
   - [ ] Disable RAG in config
   - [ ] Ask: "What is Python?"
   - [ ] Agent responds without retrieved context
   - [ ] No RAG metrics in response

5. **Query with RAG Enabled**
   - [ ] Enable RAG in config
   - [ ] Ask: "What is Python?"
   - [ ] Agent response includes retrieved context
   - [ ] RAG metrics visible (retrieved_docs, similarity)
   - [ ] Response is more detailed/accurate

6. **Compare Runs**
   - [ ] Go to Metrics page
   - [ ] Select both runs (RAG enabled vs disabled)
   - [ ] Comparison shows differences
   - [ ] RAG metrics visible for RAG-enabled run

## Error Cases

### Backend

1. **Upload invalid file type**
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@test.pdf"
```
**Expected**: 400 error, "Unsupported file type"

2. **Search empty store**
```bash
# After clearing store
curl "http://localhost:8000/api/vector-store/search?query=test"
```
**Expected**: Returns empty results array

### Frontend

1. **Upload invalid file**
   - [ ] Try to upload .pdf file
   - [ ] Error message appears
   - [ ] No upload occurs

2. **Clear empty store**
   - [ ] Clear store when already empty
   - [ ] No errors occur
   - [ ] Message confirms clearing

## Performance Tests

1. **Large Document Upload**
   - [ ] Upload 1MB+ document
   - [ ] Chunking completes successfully
   - [ ] Document searchable

2. **Many Documents**
   - [ ] Upload 10+ documents
   - [ ] Stats update correctly
   - [ ] Search still fast (<1s)

3. **RAG Latency**
   - [ ] Note query time without RAG
   - [ ] Note query time with RAG
   - [ ] RAG adds 200-500ms (acceptable)

## Success Criteria

- ✅ All API endpoints return expected responses
- ✅ No console errors in frontend
- ✅ Vector Store page functions correctly
- ✅ Chat upload button works
- ✅ RAG toggle enables/disables retrieval
- ✅ Retrieved documents improve response quality
- ✅ Metrics track RAG-specific data
- ✅ Error handling works properly

## Known Issues

None currently - all issues fixed:
- ✅ Fixed documents.length undefined error
- ✅ Fixed import syntax error (api.ts)
- ✅ Added upload button to chat UI
