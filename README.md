# OCR Starter (Netlify + Supabase)

## 1) Prérequis
- Compte Netlify
- Compte Supabase avec un projet (Free/Hobby)
- Clé API ocr.space (gratuite)

### Supabase
- Crée un **bucket public** `documents` (Storage).
- Colle ce SQL dans Supabase → SQL Editor :

```
create table if not exists categories (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  created_at timestamptz default now()
);

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  filename text not null,
  mime_type text not null,
  size_bytes int8 not null,
  storage_path text not null,
  public_url text,
  status text not null default 'uploaded',
  created_at timestamptz default now()
);

create table if not exists document_categories (
  doc_id uuid references documents(id) on delete cascade,
  cat_id uuid references categories(id) on delete cascade,
  primary key (doc_id, cat_id)
);

create table if not exists ocr_texts (
  doc_id uuid primary key references documents(id) on delete cascade,
  lang text,
  content text,
  created_at timestamptz default now()
);

create extension if not exists pg_trgm;
create index if not exists idx_ocr_texts_trgm on ocr_texts using gin (content gin_trgm_ops);
```

### Variables d'environnement (Netlify → Site settings → Environment)
- `SUPABASE_URL` = https://xxxx.supabase.co
- `SUPABASE_SERVICE_ROLE_KEY` = (clé service role de Supabase)
- `OCR_SPACE_API_KEY` = (clé sur ocr.space)

## 2) Dev local
```bash
npm i
npm run dev
```

## 3) Déploiement Netlify
- Pousse sur GitHub, connecte le repo à Netlify.
- Netlify détecte Vite → build.
- Fonctions accessibles via `/api/*`.

## 4) Utilisation
- Page home → uploader PDF/Images → OCR → recherche + catégories.
```

