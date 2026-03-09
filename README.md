# Optra

Slack, Notion 등 협업 도구에서 업무 히스토리를 자동 수집하고, 구조화된 요약과 인사이트를 제공하는 CLI 도구.

## Install

```bash
pip install optra
```

또는 [pipx](https://pipx.pypa.io/) 사용 (권장):

```bash
pipx install optra
```

원라인 설치:

```bash
curl -sSL https://raw.githubusercontent.com/RyaninKR/optra/main/install.sh | bash
```

## Quick Start

```bash
# 1. 서비스 연결
optra auth slack       # 브라우저에서 Slack 인증
optra auth notion      # 브라우저에서 Notion 인증

# 2. 업무 히스토리 수집
optra collect                    # 전체 수집
optra collect -s slack -d 14     # Slack만, 최근 14일

# 3. 요약 및 인사이트
optra summary                    # 오늘의 요약
optra summary --week 2026-W10   # 주간 요약
optra categorize                 # 자동 카테고리 분류
optra insight --month 2026-03   # 월간 인사이트

# 4. 검색
optra search "배포 관련 논의"
```

## Commands

| Command | Description |
|---------|-------------|
| `optra auth slack` | Slack OAuth 연결 |
| `optra auth notion` | Notion OAuth 연결 |
| `optra auth status` | 연결 상태 확인 |
| `optra auth logout <service>` | 서비스 연결 해제 |
| `optra collect` | 업무 히스토리 수집 |
| `optra summary` | 일간/주간 요약 생성 |
| `optra categorize` | 미분류 항목 자동 분류 |
| `optra insight` | 카테고리/협업자/소스 통계 |
| `optra search <query>` | 키워드 검색 |
| `optra stats` | 수집 통계 |
| `optra recent` | 최근 항목 조회 |

## Supported Sources

| Source | Status | Auth |
|--------|--------|------|
| Slack | v0.1 | OAuth / Bot Token |
| Notion | v0.1 | OAuth / Integration Token |
| MS Teams | Planned | - |

## Data Storage

- DB: `~/.optra/optra.db` (SQLite)
- Credentials: `~/.optra/credentials.json`
- 모든 데이터는 로컬에만 저장됩니다.

## Requirements

- Python 3.11+
- [Anthropic API Key](https://console.anthropic.com/) (요약 기능 사용 시)

## License

MIT
