CREATE TABLE IF NOT EXISTS bounty_scan_history (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 scanned_at timestamptz NOT NULL DEFAULT now(),
 source text NOT NULL,
 candidate_count integer NOT NULL,
 report jsonb NOT NULL
)