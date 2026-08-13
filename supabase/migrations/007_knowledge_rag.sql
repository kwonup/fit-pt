-- 007_knowledge_rag.sql
-- 운동 논문·가이드라인처럼 모든 사용자에게 공통으로 제공할 전문지식 RAG 저장소.
-- 사용자 프로필, 운동 기록, 운동 메모는 이 테이블에 저장하지 않고 기존 SQL 조회를 사용한다.
--
-- embedding 규격:
--   provider   : OpenAI
--   model      : text-embedding-3-small
--   dimensions : 1536 (모델 기본 출력 차원)
-- 모델 또는 차원을 변경할 때는 이 마이그레이션의 vector 크기를 변경하고 전체 문서를 재임베딩해야 한다.

create extension if not exists vector with schema extensions;

create table knowledge_documents (
  id             uuid primary key default uuid_generate_v4(),
  title          text        not null check (btrim(title) <> ''),
  source_name    text        not null check (btrim(source_name) <> ''),
  source_url     text,
  document_type  text        not null default 'other'
                             check (document_type in ('paper', 'guideline', 'article', 'note', 'other')),
  language       text        not null default 'unknown',
  published_at   date,
  license_info   text,
  content_hash   text        not null unique,
  metadata       jsonb       not null default '{}'::jsonb
                             check (jsonb_typeof(metadata) = 'object'),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

create table knowledge_chunks (
  id          uuid primary key default uuid_generate_v4(),
  document_id uuid                    not null references knowledge_documents(id) on delete cascade,
  chunk_index integer                 not null check (chunk_index >= 0),
  content     text                    not null check (btrim(content) <> ''),
  embedding   extensions.vector(1536) not null,
  metadata    jsonb                   not null default '{}'::jsonb
                                        check (jsonb_typeof(metadata) = 'object'),
  created_at  timestamptz             not null default now(),
  unique (document_id, chunk_index)
);

create trigger trg_knowledge_documents_updated_at
  before update on knowledge_documents
  for each row execute function update_updated_at();

-- 작은 초기 corpus에서는 인덱스 없는 exact cosine search로 정확도를 우선한다.
-- chunk 수와 지연시간을 측정한 뒤 같은 연산자 클래스(vector_cosine_ops)의 HNSW 도입을 검토한다.
create or replace function match_knowledge_chunks(
  query_embedding extensions.vector(1536),
  match_threshold double precision default 0.0,
  match_count integer default 4,
  filter jsonb default '{}'::jsonb
)
returns table (
  id uuid,
  document_id uuid,
  content text,
  metadata jsonb,
  similarity double precision
)
language sql
stable
security invoker
set search_path = public, extensions
as $$
  select
    kc.id,
    kd.id as document_id,
    kc.content,
    jsonb_strip_nulls(
      kd.metadata
      || kc.metadata
      || jsonb_build_object(
        'document_id', kd.id,
        'title', kd.title,
        'source_name', kd.source_name,
        'source_url', kd.source_url,
        'document_type', kd.document_type,
        'language', kd.language,
        'published_at', kd.published_at,
        'license_info', kd.license_info,
        'chunk_index', kc.chunk_index
      )
    ) as metadata,
    1 - (kc.embedding <=> query_embedding) as similarity
  from knowledge_chunks kc
  join knowledge_documents kd on kd.id = kc.document_id
  where (kd.metadata || kc.metadata) @> coalesce(filter, '{}'::jsonb)
    and 1 - (kc.embedding <=> query_embedding)
        >= greatest(0.0, least(coalesce(match_threshold, 0.0), 1.0))
  order by kc.embedding <=> query_embedding
  limit least(greatest(coalesce(match_count, 4), 1), 20);
$$;

-- 지식 저장소는 FastAPI의 service_role 클라이언트만 사용한다.
-- 프론트엔드의 anon/authenticated 역할에는 테이블 및 RPC 접근을 열지 않는다.
alter table knowledge_documents enable row level security;
alter table knowledge_chunks enable row level security;

revoke all on table knowledge_documents, knowledge_chunks from anon, authenticated;
grant select, insert, update, delete on table knowledge_documents, knowledge_chunks to service_role;

revoke execute on function match_knowledge_chunks(
  extensions.vector,
  double precision,
  integer,
  jsonb
) from public, anon, authenticated;

grant execute on function match_knowledge_chunks(
  extensions.vector,
  double precision,
  integer,
  jsonb
) to service_role;
