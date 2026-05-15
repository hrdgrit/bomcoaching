-- ═══════════════════════════════════════════════════════
--  봄 코칭심리연구소 - Supabase 초기 설정
--  Supabase 대시보드 > SQL Editor 에서 순서대로 실행하세요.
-- ═══════════════════════════════════════════════════════

-- ─── 1. reviews 테이블 ───
CREATE TABLE reviews (
  id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  name          TEXT        NOT NULL,
  coaching_type TEXT        NOT NULL,
  content       TEXT        NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  approved      BOOLEAN     DEFAULT FALSE
);

-- ─── 2. admin_settings 테이블 ───
CREATE TABLE admin_settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- 관리자 비밀번호 설정 (반드시 변경하세요!)
INSERT INTO admin_settings (key, value)
VALUES ('admin_password', 'CHANGE_ME_PASSWORD');

-- ─── 3. Row Level Security ───
ALTER TABLE reviews       ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_settings ENABLE ROW LEVEL SECURITY;

-- 승인된 후기만 공개 조회 허용
CREATE POLICY "Public read approved reviews"
  ON reviews FOR SELECT
  USING (approved = true);

-- 누구나 후기 제출 허용
CREATE POLICY "Public submit reviews"
  ON reviews FOR INSERT
  WITH CHECK (true);

-- admin_settings 는 공개 정책 없음 (SECURITY DEFINER 함수에서만 접근)

-- ─── 4. 관리자 함수 ───
-- SECURITY DEFINER: 호출자 권한이 아닌 함수 정의자 권한으로 실행 (RLS 우회)

-- 대기 중인 후기 목록 조회
CREATE OR REPLACE FUNCTION get_pending_reviews(p_password text)
RETURNS SETOF reviews
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM admin_settings
    WHERE key = 'admin_password' AND value = p_password
  ) THEN
    RAISE EXCEPTION 'Invalid password';
  END IF;
  RETURN QUERY
    SELECT * FROM reviews
    WHERE approved = false
    ORDER BY created_at DESC;
END;
$$;

-- 후기 승인
CREATE OR REPLACE FUNCTION approve_review(p_id uuid, p_password text)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM admin_settings
    WHERE key = 'admin_password' AND value = p_password
  ) THEN
    RAISE EXCEPTION 'Invalid password';
  END IF;
  UPDATE reviews SET approved = true WHERE id = p_id;
END;
$$;

-- 후기 삭제
CREATE OR REPLACE FUNCTION delete_review(p_id uuid, p_password text)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM admin_settings
    WHERE key = 'admin_password' AND value = p_password
  ) THEN
    RAISE EXCEPTION 'Invalid password';
  END IF;
  DELETE FROM reviews WHERE id = p_id;
END;
$$;
