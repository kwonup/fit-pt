# RAG 지식 문서 적재

Fit-PT의 RAG 지식 적재는 사용자 요청을 처리하는 FastAPI 런타임과 분리된 CLI 작업입니다. 승인한 운동 논문·공공 가이드라인을 운영자가 명시적으로 적재하며, 사용자의 프로필·운동 기록·운동 메모는 이 파이프라인에 넣지 않습니다.

## 처리 흐름

```text
로컬 .pdf/.md/.txt
  → LocalKnowledgeLoader
  → LangChain Document
  → RecursiveCharacterTextSplitter
  → OpenAIEmbeddings
  → knowledge_documents + knowledge_chunks
```

- PDF는 페이지별로 읽어 `page` 메타데이터를 보존합니다. 스캔 PDF는 OCR 후 사용해야 합니다.
- Markdown과 텍스트는 UTF-8 파일을 지원합니다.
- Markdown YAML frontmatter는 현재 별도 metadata로 파싱하지 않고 본문에 포함합니다. 검색 metadata의 제목·출처·언어·카테고리는 CLI 옵션을 기준으로 저장합니다.
- 기본 분할 크기는 1,000자, 겹침은 200자입니다. 문단을 우선 보존하면서 경계에서 문맥이 끊기는 문제를 줄이기 위한 MVP 시작값이며 CLI 옵션으로 조정할 수 있습니다.
- 원문 텍스트의 SHA-256 해시가 이미 존재하면 embedding API를 호출하지 않고 건너뜁니다.
- embedding은 64개 chunk 단위로 생성·저장합니다.
- 저장 중 실패하면 먼저 만든 문서를 삭제하며, `ON DELETE CASCADE`가 이미 저장된 chunk도 정리합니다.

## 사전 준비

1. `supabase/migrations/007_knowledge_rag.sql`을 대상 Supabase 프로젝트에 적용합니다.
2. `apps/api/.env`에 `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`를 설정합니다.
3. 백엔드 의존성을 설치합니다.

```powershell
cd apps/api
python -m pip install -r requirements.txt
```

`SUPABASE_SERVICE_ROLE_KEY`는 지식 테이블에 쓰기 위해 필요하므로 브라우저나 로그에 노출하면 안 됩니다.

## Markdown 문서 적재

승인한 운동 지식을 UTF-8 Markdown으로 정리한 경우 다음처럼 적재합니다.

```powershell
cd apps/api
python scripts/ingest_knowledge.py C:\knowledge\hypertrophy-guide-ko.md `
  --title "근비대 운동 근거 정리" `
  --source-name "원문 발행 기관" `
  --source-url "https://example.org/original" `
  --document-type article `
  --language ko `
  --category hypertrophy `
  --license-info "원문 이용 조건 및 요약문 작성 기준 확인"
```

실제 PDF는 출처와 이용 조건을 확인한 뒤 다음처럼 적재합니다.

```powershell
python scripts/ingest_knowledge.py C:\knowledge\guideline.pdf `
  --title "문서 제목" `
  --source-name "발행 기관" `
  --source-url "https://example.org/original" `
  --document-type guideline `
  --language ko `
  --published-at 2026-01-01 `
  --license-info "문서에 표시된 이용 조건" `
  --category resistance-training
```

분할 설정을 실험할 때만 `--chunk-size`와 `--chunk-overlap`을 변경합니다. overlap은 chunk size보다 작아야 합니다.

하나의 원 논문·가이드라인은 하나의 Markdown 파일로 유지하는 것을 권장합니다. ingestion이 파일을 자동으로 chunk로 나누므로 수동으로 작은 파일 여러 개를 만들 필요는 없습니다. 서로 다른 출처나 독립적으로 삭제·업데이트할 주제만 별도 파일로 분리합니다.

## 적재 확인

Supabase SQL Editor에서 다음 읽기 전용 쿼리로 확인합니다.

```sql
select id, title, source_name, document_type, content_hash, created_at
from knowledge_documents
order by created_at desc;

select document_id, count(*) as chunk_count
from knowledge_chunks
group by document_id
order by chunk_count desc;
```

검색 metadata와 chunk 내용을 일부 확인하려면 다음 쿼리를 사용합니다.

```sql
select
  kd.title,
  kc.chunk_index,
  left(kc.content, 300) as content_preview,
  kc.metadata
from knowledge_chunks kc
join knowledge_documents kd on kd.id = kc.document_id
order by kd.created_at desc, kc.chunk_index
limit 20;
```

적재 후 Router, Retriever, 웹 답변까지 검증하는 방법은 [`ai-rag-operations.md`](./ai-rag-operations.md)를 참고합니다.
